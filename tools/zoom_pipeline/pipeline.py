import argparse
import sys
from datetime import date
from pathlib import Path

from zoom_pipeline.config import ConfigError, load_config
from zoom_pipeline.phases import analyze_recording, default_runner, run_tick
from zoom_pipeline.state import State, StateError
from zoom_pipeline.zoom_api import Meeting, ZoomApi

CONFIG_DIR = Path.home() / '.junior_it'


def _local_meeting(state, uuid):
    meta = state.meta(uuid)
    if not meta['date'] or state.phase(uuid) == 'new':
        raise StateError('unknown_recording')
    start = meta.get('start_time')
    if not start:
        # Old state has no time; this mode must not request metadata from Zoom.
        start = meta['date'] + 'T00:00:00Z'
    return Meeting(uuid=uuid, topic=meta['topic'], start_time=start,
                   share_url=meta.get('share_url', ''), passcode=meta.get('passcode', ''),
                   files=[])


def main(argv=None):
    parser = argparse.ArgumentParser(description='Zoom-пайплайн Junior_IT')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--once', action='store_true', help='один тик (по умолчанию)')
    modes.add_argument('--dry-run', action='store_true', help='список записей из Zoom')
    modes.add_argument('--resume-analysis', metavar='UUID', help='новый цикл анализа записи, без сети')
    modes.add_argument('--resume-engine', action='store_true', help='снять блокировку движка, без сети')
    modes.add_argument('--analyze-only', metavar='UUID', help='только локальный транскрипт, без Zoom и retention')
    args = parser.parse_args(argv)
    offline = bool(args.resume_analysis or args.resume_engine or args.analyze_only)

    def log(message):
        print(message, file=sys.stderr)

    try:
        cfg = load_config(CONFIG_DIR / 'zoom-pipeline.toml',
                          CONFIG_DIR / 'zoom.env', require_zoom=not offline)
        # Acquire the lock before loading state, so a second process cannot use a stale snapshot.
        with State.locked_path(cfg.state_path):
            state = State.load(cfg.state_path)
            if not args.dry_run:
                state.recover_interrupted()
            if args.resume_analysis:
                state.resume_analysis(args.resume_analysis)
                return 0
            if args.resume_engine:
                state.resume_engine()
                return 0
            if args.analyze_only:
                meeting = _local_meeting(state, args.analyze_only)
                if state.phase(meeting.uuid) == 'analyzed':
                    log('анализ уже готов; повторный вызов не требуется')
                    return 0
                success = analyze_recording(cfg, state, default_runner, meeting, log)
                return 0 if success else 1
            api = ZoomApi(cfg.zoom_account_id, cfg.zoom_client_id, cfg.zoom_client_secret)
            if args.dry_run:
                meetings = api.list_recordings(date.today().replace(day=1).isoformat())
                for meeting in meetings:
                    print(f'{meeting.start_time[:10]} · {meeting.topic} · фаза: {state.phase(meeting.uuid)}')
                return 0
            run_tick(cfg, api, state, default_runner, date.today(), log)
            return 0
    except (ConfigError, StateError, OSError, ValueError) as exc:
        # Avoid echoing config values, corrupted state or remote response bodies.
        log(f'пайплайн остановлен: {type(exc).__name__}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
