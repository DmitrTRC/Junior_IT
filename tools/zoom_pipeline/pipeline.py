import argparse
import sys
from datetime import date
from pathlib import Path

from zoom_pipeline.config import load_config
from zoom_pipeline.phases import default_runner, run_tick
from zoom_pipeline.state import State
from zoom_pipeline.zoom_api import ZoomApi

CONFIG_DIR = Path.home() / ".junior_it"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zoom-пайплайн Junior_IT")
    parser.add_argument("--once", action="store_true",
                        help="один тик (поведение по умолчанию)")
    parser.add_argument("--dry-run", action="store_true",
                        help="показать план действий, ничего не делая")
    args = parser.parse_args(argv)

    cfg = load_config(CONFIG_DIR / "zoom-pipeline.toml",
                      CONFIG_DIR / "zoom.env")
    api = ZoomApi(cfg.zoom_account_id, cfg.zoom_client_id,
                  cfg.zoom_client_secret)
    state = State.load(cfg.state_path)

    def log(message):
        print(message, file=sys.stderr)

    if args.dry_run:
        since_meetings = api.list_recordings(
            (date.today()).replace(day=1).isoformat())
        for m in since_meetings:
            print(f"{m.start_time[:10]} · {m.topic} · фаза: {state.phase(m.uuid)}")
        return 0

    run_tick(cfg, api, state, default_runner, date.today(), log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
