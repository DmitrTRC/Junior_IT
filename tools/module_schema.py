"""Схема и проверки module.yml."""

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
