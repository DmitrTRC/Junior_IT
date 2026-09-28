from pathlib import Path

import build_homework_pages as pages


def make_hw(root: Path, hw_id="python-01-first-run"):
    d = root / "homework" / hw_id
    (d / "tests").mkdir(parents=True)
    (d / "task.md").write_text(
        "# Домашка: первая программа\n\nК модулю **python-01**.\n\n## Что делать\n\n"
        "1. Создай `hello.py`\n2. Запусти\n\n```python\nprint('hi')\n```\n", encoding="utf-8")
    (d / "broken.py").write_text("print('x)\n", encoding="utf-8")
    (d / "tests" / "test_hello.py").write_text("def test_x():\n    pass\n", encoding="utf-8")
    return d


def test_render_uses_h1_as_title_and_lists_attachments():
    html = pages.render_task("# Заголовок\n\nтекст `код`", "python-01-first-run", ["broken.py"])
    assert "<title>Заголовок · Junior_IT</title>" in html
    assert html.count("<h1") == 1                      # H1 только в шапке, не дублируется в теле
    assert '<a class="file" href="broken.py" download>broken.py</a>' in html
    assert "<code>код</code>" in html
    assert "Rubik" in html and "JetBrains Mono" in html


def test_render_without_attachments_has_no_section():
    html = pages.render_task("# Заголовок\n\nтекст", "x", [])
    assert "Вложения" not in html


def test_attachments_exclude_task_tests_and_hidden(tmp_path):
    d = make_hw(tmp_path)
    (d / ".DS_Store").write_bytes(b"")
    assert [p.name for p in pages.attachments_for(d)] == ["broken.py"]


def test_build_writes_page_and_copies_attachments(tmp_path):
    make_hw(tmp_path)
    out = tmp_path / "site"
    written = pages.build(tmp_path, out)
    page = out / "homework" / "python-01-first-run" / "index.html"
    assert written == [page]
    assert page.is_file() and (page.parent / "broken.py").read_text(encoding="utf-8") == "print('x)\n"
    assert not (page.parent / "tests").exists() and not (page.parent / "task.md").exists()
    assert "Создай <code>hello.py</code>" in page.read_text(encoding="utf-8")


def test_build_without_homework_dir_returns_empty(tmp_path):
    assert pages.build(tmp_path, tmp_path / "site") == []


def test_track_colors_by_prefix():
    assert pages.track_colors("devops-01-terminal") == ("#00e676", "#00803d")
    assert pages.track_colors("python-01-first-run") == ("#00ffc8", "#00806a")
    assert pages.track_colors("zzz-01-x") == ("#ffd60a", "#1a1a1a")


def test_render_uses_track_colours():
    html = pages.render_task("# Д\n\nт", "devops-01-terminal", [])
    assert "#00e676" in html and "#00803d" in html
    assert "#00ffc8" not in html
