from datetime import date

import pytest
import yaml

TODAY = date(2026, 9, 25)
DAY = date(2026, 9, 20)


def _dump(path, data):
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


@pytest.fixture
def journal_root(tmp_path):
    """students/ с вымышленной группой alice/bob/carol и одним занятием."""
    root = tmp_path / "students"
    (root / "journal").mkdir(parents=True)
    _dump(root / "roster.yml", {"students": [
        {"id": "alice", "name": "Алиса", "status": "active", "platform": "mac", "joined": "2026-09-09"},
        {"id": "bob", "name": "Боб", "status": "active", "platform": "win"},
        {"id": "carol", "name": "Кэрол", "status": "left"},
    ]})
    _dump(root / "journal" / "2026-09-20.yml", {
        "date": DAY,
        "attendance": {"alice": "present", "bob": "late"},
        "homework": {"python-01-first-run": {
            "alice": {"status": "issued", "at": DAY},
            "bob": {"status": "submitted", "at": date(2026, 9, 21)}}},
        "points": [{"who": "alice", "amount": 2, "reason": "присутствие", "by": "teacher"},
                   {"who": "bob", "amount": 1, "reason": "опоздание", "by": "teacher"}],
        "notes": {},
    })
    return root


@pytest.fixture
def course_root(tmp_path):
    """Корень репо с двумя планами занятий в playground/."""
    root = tmp_path / "repo"
    d = root / "playground" / "2026-09-20"
    d.mkdir(parents=True)
    _dump(d / "session.yml", {"date": DAY, "time": "20:00", "theme": "Первый Python",
                              "homework": {"due": date(2026, 9, 23), "items": ["homework/python-01-first-run"]}})
    d = root / "playground" / "2026-09-13"
    d.mkdir(parents=True)
    _dump(d / "session.yml", {"date": date(2026, 9, 13), "theme": "Терминал"})
    return root
