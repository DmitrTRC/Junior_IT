from make_redirects import MOVES, plan_redirects, redirect_html, write_redirects


def test_redirect_html_has_refresh_and_link():
    html = redirect_html("../../tracks/web/m-01-html-css/student/cheatsheet.html")
    assert "http-equiv=\"refresh\"" in html
    assert "../../tracks/web/m-01-html-css/student/cheatsheet.html" in html
    assert "<html lang=\"ru\">" in html


def test_plan_covers_existing_files_only(tmp_path):
    module_dir = tmp_path / "tracks" / "web" / "m-01-html-css" / "student"
    module_dir.mkdir(parents=True)
    (module_dir / "cheatsheet.html").write_text("x", encoding="utf-8")
    plan = plan_redirects(tmp_path)
    stubs = {path.relative_to(tmp_path).as_posix() for path, _ in plan}
    assert "lessons/lesson-01-html-css/cheatsheet.html" in stubs
    assert "lessons/lesson-01-html-css/homework.html" not in stubs


def test_plan_target_is_relative_and_correct(tmp_path):
    module_dir = tmp_path / "tracks" / "cs" / "m-01-computer" / "shared"
    module_dir.mkdir(parents=True)
    (module_dir / "slides.html").write_text("x", encoding="utf-8")
    plan = plan_redirects(tmp_path)
    targets = dict(
        (path.relative_to(tmp_path).as_posix(), url) for path, url in plan
    )
    assert (
        targets["lessons/lesson-cs-01-computer/slides.html"]
        == "../../tracks/cs/m-01-computer/shared/slides.html"
    )


def test_write_creates_files(tmp_path):
    module_dir = tmp_path / "tracks" / "web" / "m-01-html-css" / "student"
    module_dir.mkdir(parents=True)
    (module_dir / "cheatsheet.html").write_text("x", encoding="utf-8")
    count = write_redirects(tmp_path)
    stub = tmp_path / "lessons" / "lesson-01-html-css" / "cheatsheet.html"
    assert count == 1
    assert "refresh" in stub.read_text(encoding="utf-8")


def test_moves_cover_all_eleven_lessons():
    assert len(MOVES) == 11


def test_plan_covers_demos_with_correct_relative_path(tmp_path):
    module_dir = tmp_path / "tracks" / "web" / "m-01-html-css" / "shared" / "demos"
    module_dir.mkdir(parents=True)
    (module_dir / "gamer.html").write_text("x", encoding="utf-8")
    plan = plan_redirects(tmp_path)
    targets = dict(
        (path.relative_to(tmp_path).as_posix(), url) for path, url in plan
    )
    assert (
        targets["lessons/lesson-01-html-css/demos/gamer.html"]
        == "../../../tracks/web/m-01-html-css/shared/demos/gamer.html"
    )


def test_plan_skips_modules_without_demos(tmp_path):
    module_dir = tmp_path / "tracks" / "web" / "m-01-html-css" / "student"
    module_dir.mkdir(parents=True)
    (module_dir / "cheatsheet.html").write_text("x", encoding="utf-8")
    plan = plan_redirects(tmp_path)
    stubs = {path.relative_to(tmp_path).as_posix() for path, _ in plan}
    assert "lessons/lesson-01-html-css/demos/gamer.html" not in stubs
