from datetime import date

from comms import course


def test_plans_and_homework(course_root):
    day, plan = course.latest_plan_with_homework(course_root, date(2026, 9, 25))
    assert day == date(2026, 9, 20) and course.homework_ids(plan) == ["python-01-first-run"]
    assert course.due(plan) == date(2026, 9, 23)
    assert course.plan_for(course_root, date(2026, 9, 13))["theme"] == "Терминал"
    assert course.latest_plan_with_homework(course_root, date(2026, 9, 1)) is None
    assert [s["date"] for s in course.sessions(course_root)] == [date(2026, 9, 13), date(2026, 9, 20)]


def test_task_text_attachments_and_url(tmp_path):
    hw = tmp_path / "homework" / "x-01"
    hw.mkdir(parents=True)
    (hw / "task.md").write_text("# Д\n\nтекст", encoding="utf-8")
    (hw / "broken.py").write_text("print('x)", encoding="utf-8")
    assert course.task_text(tmp_path, "x-01") == "# Д\n\nтекст" and course.task_text(tmp_path, "nope") == ""
    assert course.attachments(tmp_path, "x-01") == {"broken.py": b"print('x)"}
    assert course.page_url("https://site/", "x-01") == "https://site/homework/x-01/"
    assert course.drafts_dir(tmp_path) == tmp_path / "meta" / "drafts"


def test_student_names(journal_root):
    assert course.student_names(journal_root) == {"alice": "Алиса", "bob": "Боб", "carol": "Кэрол"}
