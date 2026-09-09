#!/usr/bin/env python3
"""Проверка библиотеки модулей: python3 tools/validate_modules.py [корень репо]"""

import sys
from pathlib import Path

from module_schema import validate_module


def iter_module_dirs(repo_root):
    """Все папки модулей вида tracks/<track>/<module>/ с манифестом."""
    tracks_dir = Path(repo_root) / "tracks"
    if not tracks_dir.is_dir():
        return []
    return sorted(p.parent for p in tracks_dir.glob("*/*/module.yml"))


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    repo_root = Path(args[0]) if args else Path(__file__).resolve().parent.parent

    failed = 0
    for module_dir in iter_module_dirs(repo_root):
        errors = validate_module(module_dir, repo_root)
        name = module_dir.relative_to(repo_root)
        if errors:
            failed += 1
            print(f"FAIL {name}")
            for error in errors:
                print(f"     {error}")
        else:
            print(f"ok   {name}")

    print(f"\nмодулей с ошибками: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
