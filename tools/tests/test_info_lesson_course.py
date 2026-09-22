from datetime import date

from info import course, lesson
from info.common import PAGES_URL

TODAY = date(2026, 9, 22)
PLAN = {
    "date": date(2026, 9, 24), "time": "20:00", "theme": "Ветвление",
    "playlist": [{"module": "python/m-02-branching", "minutes": 35}, {"module": "book/m-01-information-and-data"}],
    "buffer": 10,
    "homework": {"due": date(2026, 9, 27), "items": ["homework/python-02-branching"]},
}


def test_lesson_lines_future_plan(tmp_path):
    (tmp_path / "tracks" / "python" / "m-02-branching" / "teacher").mkdir(parents=True)
    (tmp_path / "tracks" / "python" / "m-02-branching" / "teacher" / "scenario.md").write_text("x", encoding="utf-8")
    out = lesson.lines(PLAN, False, TODAY, tmp_path)
    assert [l.text for l in out] == [
        "чт 24.09 20:00 · через 2 дн.", "Ветвление",
        "python/m-02-branching · 35 мин", "book/m-01-information-and-data",
        "домашка до 27.09: python-02-branching", "буфер 10 мин"]
    assert out[0].open == "playground/2026-09-24/session.yml" and out[0].style is None
    assert out[2].open == "tracks/python/m-02-branching/teacher/scenario.md"
    assert out[3].open == "tracks/book/m-01-information-and-data/module.yml"
    assert out[4].open == "homework/python-02-branching/task.md"
    assert out[5].style == "dim"


def test_lesson_lines_today_and_stale(tmp_path):
    today_plan = {**PLAN, "date": TODAY}
    assert lesson.lines(today_plan, False, TODAY, tmp_path)[0].style == "ok"
    assert lesson.lines(today_plan, False, TODAY, tmp_path)[0].text.startswith("вт 22.09 20:00 · сегодня")
    stale = lesson.lines({**PLAN, "date": date(2026, 9, 20)}, True, TODAY, tmp_path)
    assert stale[0].style == "warn" and "план на следующее не создан" in stale[0].text
    assert "2 дн. назад" in stale[0].text


def test_lesson_lines_without_plan_or_homework(tmp_path):
    out = lesson.lines(None, False, TODAY, tmp_path)
    assert len(out) == 1 and out[0].style == "warn" and "планов нет" in out[0].text
    bare = lesson.lines({"date": date(2026, 9, 24)}, False, TODAY, tmp_path)
    assert [l.text for l in bare] == ["чт 24.09 · через 2 дн."]


MODULES = [
    {"id": "python/m-01", "track": "python", "level": "core"},
    {"id": "python/m-02", "track": "python", "level": "core"},
    {"id": "devops/m-01", "track": "devops", "level": "core"},
    {"id": "web/reading", "track": "web", "level": "optional"},
]
SESSIONS = [
    {"date": date(2026, 9, 13), "playlist": [{"module": "devops/m-01"}]},
    {"date": date(2026, 9, 20), "playlist": [{"module": "python/m-01"}], "completed": ["python/m-01"]},
    {"date": date(2026, 9, 24), "playlist": [{"module": "python/m-02"}]},
]


def test_course_lines():
    out = course.lines(MODULES, SESSIONS, TODAY)
    assert [l.text for l in out] == ["занятий проведено: 2", "модулей: 2/3", "devops 1/1 · python 1/2"]
    assert all(l.style == "dim" and l.open == PAGES_URL for l in out)


def test_course_lines_empty():
    assert [l.text for l in course.lines([], [], TODAY)] == ["занятий проведено: 0", "модулей: 0/0", "модулей нет"]
