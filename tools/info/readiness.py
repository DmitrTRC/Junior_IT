from __future__ import annotations
from pathlib import Path

import yaml

from info.common import Line, homework_task, hw_id_from_ref, module_dir, scenario_target

ANATOMY = (
    ("scenario", "teacher/scenario.md"),
    ("live-code", "shared/live-code.md"),
    ("slides", "shared/slides.html"),
    ("cheatsheet", "student/cheatsheet.html"),
    ("glossary", "student/glossary.md"),
)


def module_homework(directory: Path) -> str | None:
    manifest = directory / "module.yml"
    if not manifest.is_file():
        return None
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    ref = data.get("homework") if isinstance(data, dict) else None
    return hw_id_from_ref(ref) if ref else None


def lines(module_ids: list[str], repo_root, validate_fn) -> list[Line]:
    """validate_fn(module_dir: Path, repo_root: Path) -> list[str] — ошибки module_schema.validate_module."""
    if not module_ids:
        return [Line("нет плейлиста", style="dim")]
    root = Path(repo_root)
    out: list[Line] = []
    for module_id in module_ids:
        directory = module_dir(module_id, root)
        if not directory.is_dir():
            out.append(Line(f"{module_id} · модуля нет", style="err"))
            continue
        marks = [(label, (directory / rel).is_file()) for label, rel in ANATOMY]
        errors = validate_fn(directory, root)
        parts = " ".join(f"{label} {'✓' if present else '✗'}" for label, present in marks)
        validate = "validate ✓" if not errors else f"validate ✗ {errors[0]}"
        style = "err" if errors else ("ok" if all(present for _, present in marks) else "warn")
        out.append(Line(f"{module_id} · {parts} · {validate}", open=scenario_target(module_id, root), style=style))
        hw_id = module_homework(directory)
        if hw_id:
            task = homework_task(hw_id)
            task_path = root / task
            present = task_path.is_file()
            renders = present and _renders(task_path, hw_id)
            style = "ok" if present and renders else "warn"
            out.append(Line(f"  домашка {hw_id}: task.md {'✓' if present else '✗'} · страница {'✓' if renders else '✗'}",
                            open=task, style=style))
    return out


def _renders(task_path: Path, hw_id: str) -> bool:
    try:
        from build_homework_pages import render_task
        render_task(task_path.read_text(encoding="utf-8"), hw_id, [])
        return True
    except Exception:
        return False
