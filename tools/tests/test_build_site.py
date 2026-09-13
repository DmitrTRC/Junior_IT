import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "tools" / "build_site.sh"


def build(tmp_path):
    out = tmp_path / "site"
    subprocess.run([str(BUILD), str(out)], check=True)
    return out


def test_teacher_dirs_never_published(tmp_path):
    out = build(tmp_path)
    assert list(out.rglob("teacher")) == []


def test_student_and_shared_are_published(tmp_path):
    out = build(tmp_path)
    assert (out / "tracks" / "web" / "m-01-html-css" / "student" / "cheatsheet.html").is_file()
    assert (out / "tracks" / "web" / "m-01-html-css" / "shared").is_dir()


def test_landing_page_is_published(tmp_path):
    out = build(tmp_path)
    assert (out / "index.html").is_file()


def test_trainer_is_published(tmp_path):
    out = build(tmp_path)
    assert (out / "trainer" / "index.html").is_file()
    assert (out / "trainer" / "trainer.css").is_file()
    assert (out / "trainer" / "js" / "engine.js").is_file()


def test_quizzes_bank_is_published(tmp_path):
    out = build(tmp_path)
    assert (out / "textbook" / "quizzes" / "index.json").is_file()
    assert (out / "textbook" / "quizzes" / "07-1.1.json").is_file()


def test_quiz_review_not_published_before_proofread(tmp_path):
    out = build(tmp_path)
    assert not (out / "textbook" / "quizzes" / "REVIEW-07-1.md").exists()


def test_internal_dirs_never_published(tmp_path):
    out = build(tmp_path)
    # Всё, что не перечислено в белом списке PUBLISH — не публикуется.
    for internal in (
        ".git", ".github", ".claude", ".aos", ".vscode",
        "tools", "meta", "refs", "homework", "playground",
        "provisioning", "print", "students", "recordings", "TO_PARENTS",
        "graphify-out", ".superpowers",
    ):
        assert not (out / internal).exists(), f"{internal}/ не должен публиковаться"


def test_internal_root_files_never_published(tmp_path):
    out = build(tmp_path)
    for internal in ("CLAUDE.md", "pyrightconfig.json"):
        assert not (out / internal).exists(), f"{internal} не должен публиковаться"


def test_nested_excluded_dir_never_published(tmp_path):
    out = build(tmp_path)
    assert not (out / "docs" / "superpowers").exists()


def test_live_code_never_published(tmp_path):
    out = build(tmp_path)
    assert list(out.rglob("live-code.md")) == []


def test_course_map_generated_and_valid(tmp_path):
    import json
    out = build(tmp_path)
    data = json.loads((out / "course-map.json").read_text(encoding="utf-8"))
    assert data["modules"], "карта не должна быть пустой на живом репо"
