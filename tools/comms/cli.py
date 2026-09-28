"""comms — ручные операции: код регистрации, репо ученика, статус. Автоматика — tick.py."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tools/ — чтобы работал python3 tools/comms/cli.py

from comms.identity import Identity, IdentityError  # noqa: E402
from comms.outbox import Outbox  # noqa: E402
from journal import store as journal_store  # noqa: E402
from journal.model import JournalError  # noqa: E402

DEFAULT_LOCAL = Path.home() / ".junior_it" / "comms"


def run(argv, students_root=None, local_dir: Path | None = None) -> int:
    ap = argparse.ArgumentParser(prog="comms")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("code", help="код регистрации в Telegram для ученика или родителя")
    p.add_argument("student")
    p.add_argument("--parent", action="store_true")
    p = sub.add_parser("github", help="репозиторий домашек ученика owner/name")
    p.add_argument("student")
    p.add_argument("repo")
    sub.add_parser("status", help="очереди и состояние")
    args = ap.parse_args(argv)
    root = journal_store.students_root(students_root)
    local = Path(local_dir or DEFAULT_LOCAL)
    try:
        ident = Identity(root / "comms.yml")
    except IdentityError as exc:
        print(f"comms: {exc}", file=sys.stderr)
        return 3
    if args.cmd in ("code", "github"):
        try:
            known = {s.id for s in journal_store.load_roster(students_root)}
        except JournalError as exc:
            print(f"comms: {exc}", file=sys.stderr)
            return 3
        if args.student not in known:
            print(f"comms: ученика {args.student} нет в ростере", file=sys.stderr)
            return 2
    if args.cmd == "code":
        person = ident.ensure(args.student, "parent" if args.parent else "student")
        code = ident.new_code(person)
        Outbox(local / "outbox-staging").control_add_code(code, person.comms_id)
        print(f"{args.student} ({person.role}): /start {code}")
        return 0
    if args.cmd == "github":
        ident.set_github(args.student, args.repo)
        print(f"{args.student}: {args.repo}")
        return 0
    status_path = local / "status.json"
    if status_path.is_file():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        sizes = status.get("sizes") or {}
        print(f"почтальон: {'онлайн' if status.get('online') else 'офлайн'} · исходящих {sizes.get('outbox', 0)}, "
              f"входящих {sizes.get('inbox', 0)}, не доставлено {sizes.get('failed', 0)}")
    else:
        print("почтальон: status.json ещё не забирали")
    print(f"людей в comms.yml: {len(ident.people)}, без telegram: "
          f"{sum(1 for p in ident.people if p.telegram_id is None)}")
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
