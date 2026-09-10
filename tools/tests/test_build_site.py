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


def test_internal_dirs_never_published(tmp_path):
    out = build(tmp_path)
    for internal in ("tools", "meta", "refs", "homework", "playground", "provisioning"):
        assert not (out / internal).exists(), f"{internal}/ не должен публиковаться"
