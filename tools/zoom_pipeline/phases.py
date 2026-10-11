import subprocess
import os
import signal
import tempfile
from datetime import date, datetime, timedelta, timezone
from importlib import resources

from zoom_pipeline.anonymize import anonymize
from zoom_pipeline.analysis import AnalysisError, analyze
from zoom_pipeline.config import (NOTIFY_TIMEOUT,
                                  RSYNC_TIMEOUT, WHISPER_TIMEOUT)


def default_runner(cmd, *, timeout, stdin_text=None, env=None):
    # CLI launchers can spawn a native child; stop the whole group on timeout.
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, env=env,
                          start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(stdin_text, timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise
        return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)


def _meeting_date(meeting):
    return meeting.start_time[:10]


def _meeting_time_hhmm(meeting):
    """Извлечь HHMM из start_time (ISO 8601), например 17:00 -> 1700."""
    return meeting.start_time[11:16].replace(":", "")


def _safe_uuid(meeting):
    """Безопасное имя uuid для использования в путях."""
    return meeting.uuid.replace("/", "_")


def _meeting_dir(cfg, meeting):
    return cfg.recordings_dir / _meeting_date(meeting)


def _transcript_path(cfg, meeting):
    """Путь к транскрипту для конкретной встречи."""
    return _meeting_dir(cfg, meeting) / f"{_safe_uuid(meeting)}-transcript.txt"


def _download(cfg, api, meeting):
    """Возвращает число скачанных файлов; 0 = запись ещё готовится в Zoom."""
    target = _meeting_dir(cfg, meeting)
    seen_names = {}
    base_name = _safe_uuid(meeting)
    downloaded = 0
    for f in meeting.files:
        if f.file_type not in {"MP4", "M4A", "TRANSCRIPT"}:
            continue
        ext = f.extension or f.file_type.lower()
        name_key = f"{base_name}.{ext}"
        if name_key in seen_names:
            seen_names[name_key] += 1
            name = f"{base_name}-{seen_names[name_key]}.{ext}"
        else:
            seen_names[name_key] = 1
            name = name_key
        api.download(f.download_url, target / name)
        downloaded += 1
    return downloaded


def _backup(cfg, meeting, runner, log):
    if not cfg.backup_dir.is_dir():
        log(f"бэкап: шара не смонтирована ({cfg.backup_dir}), отложено")
        return False
    src = str(_meeting_dir(cfg, meeting))
    result = runner(["rsync", "-a", src, str(cfg.backup_dir) + "/"],
                    timeout=RSYNC_TIMEOUT)
    if result.returncode != 0:
        log(f"бэкап: rsync упал ({result.returncode}): {result.stderr.strip()}")
        return False
    return True

def _find_file(meeting_dir, prefix, *suffixes):
    """Найти файл с заданным префиксом и одним из расширений."""
    for suffix in suffixes:
        found = sorted(meeting_dir.glob(f"{prefix}*.{suffix}"))
        if found:
            return found[0]
    return None


def _transcribe(cfg, meeting, runner, log):
    meeting_dir = _meeting_dir(cfg, meeting)
    transcript = _transcript_path(cfg, meeting)
    prefix = _safe_uuid(meeting)

    audio = _find_file(meeting_dir, prefix, "m4a", "mp4")
    if audio is not None:
        result = runner([*cfg.whisper_cmd, "--output-dir", str(meeting_dir),
                         str(audio)], timeout=WHISPER_TIMEOUT)
        produced = audio.with_suffix(".txt")
        if result.returncode == 0 and produced.is_file():
            produced.replace(transcript)
            return transcript
        if result.returncode != 0:
            log(f"whisper упал ({result.returncode}), пробую облачный vtt")
        else:
            log("whisper отработал, но выходной файл не появился, пробую облачный vtt")

    vtt = _find_file(meeting_dir, prefix, "vtt")
    if vtt is not None:
        transcript.write_text(
            "[транскрипт из облака Zoom — точность ниже]\n" +
            vtt.read_text(encoding="utf-8"), encoding="utf-8")
        return transcript
    log("транскрибировать нечем: нет ни аудио с рабочим whisper, ни vtt")
    return None


def _session_yaml(cfg, meeting):
    path = cfg.playground_dir / _meeting_date(meeting) / "session.yml"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "(session.yml на эту дату не найден)"


def _analyze(cfg, meeting, transcript_path, runner, log):
    template = (resources.files("zoom_pipeline") / "analysis_prompt.md") \
        .read_text(encoding="utf-8")
    prompt = template.format(
        date=_meeting_date(meeting), topic=anonymize(meeting.topic, cfg.student_stems),
        share_url="[RECORDING_URL]", passcode="[RECORDING_PASSCODE]",
        session_yaml=anonymize(_session_yaml(cfg, meeting), cfg.student_stems),
        transcript=anonymize(
            transcript_path.read_text(encoding="utf-8"), cfg.student_stems),
    )
    result = analyze(cfg, prompt, runner)
    before, marker, message = result.partition("## Сообщение в MAX")
    message = message.replace("[RECORDING_URL]", meeting.share_url or "ссылка недоступна")
    message = message.replace("[RECORDING_PASSCODE]", meeting.passcode or "код недоступен")
    result = before + marker + message
    cfg.drafts_dir.mkdir(parents=True, exist_ok=True)
    hhmm = _meeting_time_hhmm(meeting)
    draft = cfg.drafts_dir / f"lesson-{_meeting_date(meeting)}-{hhmm}-analysis.md"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=cfg.drafts_dir, delete=False) as handle:
            temporary = handle.name
            handle.write(result + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, draft)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return draft


def analyze_recording(cfg, state, runner, meeting, log, *, now=None):
    fixed_clock = now is not None
    now = now or datetime.now(timezone.utc)
    if state.phase(meeting.uuid) != "transcribed" or not state.analysis_allowed(meeting.uuid, now):
        return False
    state.begin_analysis(meeting.uuid, now)
    try:
        draft = _analyze(cfg, meeting, _transcript_path(cfg, meeting), runner, log)
    except AnalysisError as exc:
        failure_time = now if fixed_clock else datetime.now(timezone.utc)
        state.fail_analysis(meeting.uuid, exc.code, failure_time,
                            retryable=exc.retryable, global_block=exc.global_block,
                            retry_at=exc.retry_at)
        log(f"анализ: {exc.code}")
        return False
    except OSError:
        state.fail_analysis(meeting.uuid, "local_io", now)
        log("анализ: local_io")
        return False
    state.complete_analysis(meeting.uuid)
    try:
        _notify(draft, runner)
    except (OSError, subprocess.SubprocessError):
        log("анализ готов; уведомление недоступно")
    return True


def _notify(draft, runner):
    runner(["osascript", "-e",
            f'display notification "{draft.name}" with title "Zoom-пайплайн: анализ готов"'],
           timeout=NOTIFY_TIMEOUT)


def _retention(cfg, api, state, today, log):
    for uuid in list(state.uuids_in_phase("analyzed")):
        meta = state.meta(uuid)
        if not meta["date"]:
            continue
        recorded = date.fromisoformat(meta["date"])
        if today - recorded >= timedelta(days=cfg.retention_days):
            try:
                api.delete_recording(uuid)
            except Exception as exc:
                log(f"retention: не удалилось {uuid}: {exc}")
                continue
            state.advance(uuid, "cloud_deleted")
            log(f"retention: запись {meta['date']} удалена из облака")


def run_tick(cfg, api, state, runner, today, log, *, now=None):
    since = (today - timedelta(days=7)).isoformat()
    try:
        meetings = api.list_recordings(since)
    except Exception as exc:
        log(f"опрос записей не удался: {exc}")
        return
    for meeting in meetings:
        try:
            _process(cfg, api, state, runner, meeting, log, now=now)
        except Exception as exc:
            log(f"встреча {meeting.uuid}: {exc}")
    _retention(cfg, api, state, today, log)


def _process(cfg, api, state, runner, meeting, log, *, now=None):
    phase = state.phase(meeting.uuid)
    day, topic = _meeting_date(meeting), meeting.topic
    if phase == "new":
        if _download(cfg, api, meeting) == 0:
            log(f"встреча {meeting.uuid}: файлы записи ещё готовятся в Zoom, жду следующего тика")
            return
        state.advance(meeting.uuid, "downloaded", date=day, topic=topic,
                      share_url=meeting.share_url, passcode=meeting.passcode,
                      start_time=meeting.start_time)
        phase = "downloaded"
    if phase == "downloaded":
        if not _backup(cfg, meeting, runner, log):
            return
        state.advance(meeting.uuid, "backed_up", date=day, topic=topic)
        phase = "backed_up"
    if phase == "backed_up":
        transcript = _transcribe(cfg, meeting, runner, log)
        if transcript is None:
            return
        # Best-effort backup транскрипта, результат игнорируем
        _backup(cfg, meeting, runner, log)
        state.advance(meeting.uuid, "transcribed", date=day, topic=topic)
        phase = "transcribed"
    if phase == "transcribed":
        analyze_recording(cfg, state, runner, meeting, log, now=now)
