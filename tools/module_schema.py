"""Схема и проверки module.yml."""

import re

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
