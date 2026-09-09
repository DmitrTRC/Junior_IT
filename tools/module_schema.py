"""Схема и проверки module.yml."""

import re

import yaml

TRACKS = ("book", "python", "pascal", "devops", "cs", "web")

TRACK_TOKEN = {
    "book": "book",
    "python": "py",
    "pascal": "pas",
    "devops": "ops",
    "cs": "cs",
    "web": "web",
}

LEVELS = ("core", "deep", "optional")
REQUIRED_FIELDS = ("id", "title", "track", "level", "minutes")
ROLE_DIRS = ("shared", "student", "teacher")

TEXTBOOK_RE = re.compile(r"^[78]:\d+\.\d+$")


def check_fields(data):
    """Проверяет содержимое module.yml. Возвращает список ошибок."""
    if not isinstance(data, dict):
        return ["module.yml должен быть словарём"]

    errors = []

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"нет обязательного поля {field}")

    track = data.get("track")
    if track is not None and track not in TRACKS:
        errors.append(f"неизвестный трек {track!r}, ожидается один из {list(TRACKS)}")

    level = data.get("level")
    if level is not None and level not in LEVELS:
        errors.append(f"неизвестный level {level!r}, ожидается один из {list(LEVELS)}")

    minutes = data.get("minutes")
    if minutes is not None and (not isinstance(minutes, int) or minutes <= 0):
        errors.append(f"minutes должно быть положительным целым, получено {minutes!r}")

    for ref in data.get("textbook") or []:
        if not TEXTBOOK_RE.match(str(ref)):
            errors.append(
                f"ссылка на учебник {ref!r} должна быть вида '7:1.3' или '8:5.4'"
            )

    for term in data.get("terms") or []:
        if not isinstance(term, dict) or not term.get("ru") or not term.get("en"):
            errors.append(f"термин {term!r} должен иметь непустые ru и en")

    return errors


def check_layout(module_dir):
    """Проверяет, что у модуля есть все три папки ролей."""
    return [
        f"нет папки {role}/"
        for role in ROLE_DIRS
        if not (module_dir / role).is_dir()
    ]


def check_links(data, module_dir, repo_root):
    """Проверяет, что id совпадает с путём, а ссылки ведут в существующее."""
    errors = []

    expected_id = f"{module_dir.parent.name}/{module_dir.name}"
    if data.get("id") != expected_id:
        errors.append(f"id {data.get('id')!r} не совпадает с путём {expected_id!r}")

    for dep in data.get("requires") or []:
        if not (repo_root / "tracks" / dep).is_dir():
            errors.append(f"requires: модуль {dep!r} не найден")

    for field in ("quiz", "homework"):
        target = data.get(field)
        if target and not (repo_root / target).exists():
            errors.append(f"{field}: путь {target!r} не найден")

    return errors


def validate_module(module_dir, repo_root):
    """Полная проверка модуля: манифест, поля, папки ролей, ссылки."""
    manifest = module_dir / "module.yml"
    if not manifest.is_file():
        return ["нет module.yml"]

    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"module.yml не читается: {exc}"]

    return (
        check_fields(data)
        + check_layout(module_dir)
        + check_links(data, module_dir, repo_root)
    )
