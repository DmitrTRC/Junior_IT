import subprocess
from datetime import date, timedelta
from importlib import resources

from zoom_pipeline.anonymize import anonymize
from zoom_pipeline.config import (CLAUDE_TIMEOUT, NOTIFY_TIMEOUT,
                                  RSYNC_TIMEOUT, WHISPER_TIMEOUT)


def default_runner(cmd, *, timeout, stdin_text=None):
    return subprocess.run(cmd, input=stdin_text, capture_output=True,
                          text=True, timeout=timeout)


def _meeting_date(meeting):
    return meeting.start_time[:10]


def _meeting_dir(cfg, meeting):
    return cfg.recordings_dir / _meeting_date(meeting)


def _download(cfg, api, meeting):
    target = _meeting_dir(cfg, meeting)
    seen_names = {}
    for f in meeting.files:
        if f.file_type not in {"MP4", "M4A", "TRANSCRIPT"}:
            continue
        base_name = meeting.uuid.replace('/', '_')
        ext = f.extension or f.file_type.lower()
        name_key = f"{base_name}.{ext}"
        if name_key in seen_names:
            seen_names[name_key] += 1
            name = f"{base_name}-{seen_names[name_key]}.{ext}"
        else:
            seen_names[name_key] = 1
            name = name_key
        api.download(f.download_url, target / name)
    return target


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

def _find_file(meeting_dir, *suffixes):
    for suffix in suffixes:
        found = sorted(meeting_dir.glob(f"*.{suffix}"))
        if found:
            return found[0]
    return None


def _transcribe(cfg, meeting, runner, log):
    meeting_dir = _meeting_dir(cfg, meeting)
    transcript = meeting_dir / "transcript.txt"
    audio = _find_file(meeting_dir, "m4a", "mp4")
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
    vtt = _find_file(meeting_dir, "vtt", "transcript")
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
        date=_meeting_date(meeting), topic=meeting.topic,
        share_url=meeting.share_url, passcode=meeting.passcode,
        session_yaml=_session_yaml(cfg, meeting),
        transcript=anonymize(
            transcript_path.read_text(encoding="utf-8"), cfg.student_stems),
    )
    result = runner(cfg.claude_cmd, timeout=CLAUDE_TIMEOUT, stdin_text=prompt)
    if result.returncode != 0 or not result.stdout.strip():
        log(f"анализ: claude -p упал ({result.returncode})")
        return None
    cfg.drafts_dir.mkdir(parents=True, exist_ok=True)
    draft = cfg.drafts_dir / f"lesson-{_meeting_date(meeting)}-analysis.md"
    draft.write_text(result.stdout, encoding="utf-8")
    return draft


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


def run_tick(cfg, api, state, runner, today, log):
    since = (today - timedelta(days=7)).isoformat()
    try:
        meetings = api.list_recordings(since)
    except Exception as exc:
        log(f"опрос записей не удался: {exc}")
        return
    for meeting in meetings:
        try:
            _process(cfg, api, state, runner, meeting, log)
        except Exception as exc:
            log(f"встреча {meeting.uuid}: {exc}")
    _retention(cfg, api, state, today, log)


def _process(cfg, api, state, runner, meeting, log):
    phase = state.phase(meeting.uuid)
    day, topic = _meeting_date(meeting), meeting.topic
    if phase == "new":
        _download(cfg, api, meeting)
        state.advance(meeting.uuid, "downloaded", date=day, topic=topic)
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
        state.advance(meeting.uuid, "transcribed", date=day, topic=topic)
        phase = "transcribed"
    if phase == "transcribed":
        transcript = _meeting_dir(cfg, meeting) / "transcript.txt"
        draft = _analyze(cfg, meeting, transcript, runner, log)
        if draft is None:
            return
        state.advance(meeting.uuid, "analyzed", date=day, topic=topic)
        _notify(draft, runner)
