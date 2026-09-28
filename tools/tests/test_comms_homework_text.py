from datetime import date

from comms.homework_text import homework_block, telegram_html, _balance

MD = "# Домашка\n\nК модулю **python-01**.\n\n## Что делать\n\n1. Создай `hello.py`\n2. Запусти\n\n" \
     "> На Windows `python`.\n\n```python\nprint('hi')\n```\n\nСм. [страницу](https://s/x/)\n"


def test_telegram_html_markup():
    out = telegram_html(MD)
    assert "<b>Домашка</b>" in out and "<b>python-01</b>" in out and "<b>Что делать</b>" in out
    assert "<code>hello.py</code>" in out and "<pre>print('hi')</pre>" in out
    assert 'На Windows <code>python</code>' in out and "&gt;" not in out
    assert '<a href="https://s/x/">страницу</a>' in out


def test_escapes_html_in_text():
    assert telegram_html("a < b & c") == "a &lt; b &amp; c"


def test_long_task_is_truncated_with_link():
    md = "# Д\n\n" + "\n".join(f"строка {i} " + "x" * 60 for i in range(200)) + "\n\n```\ncode\n```\n"
    out = telegram_html(md, limit=3500, more_url="https://s/hw/")
    assert len(out) <= 3600 and out.endswith("…\nПолностью: https://s/hw/")
    assert out.count("<pre>") == out.count("</pre>") and out.count("<b>") == out.count("</b>")


def test_truncation_does_not_split_pre():
    body = "\n".join("y" * 50 for _ in range(10))
    md = "текст\n\n```\n" + body + "\n```\n"
    out = telegram_html(md, limit=300, more_url="https://s/")
    assert "<pre>" not in out and out.startswith("текст")


def test_homework_block():
    out = homework_block("# Д\n\nтекст", "python-01-first-run", date(2026, 9, 30), "https://s/homework/python-01-first-run/")
    assert out.startswith("<b>Домашка до ср 30.09</b>\n") and "текст" in out
    assert out.endswith("Страница: https://s/homework/python-01-first-run/")
    assert "до " not in homework_block("# Д\n\nт", "x", None, "https://s/")


def test_code_span_keeps_double_asterisks():
    out = telegram_html("x `{**a, **b}` y")
    assert out == "x <code>{**a, **b}</code> y"


def test_truncation_single_long_line_keeps_tags_balanced():
    md = "**жирно** " + "x" * 3990 + " `код`"
    out = telegram_html(md, limit=3500, more_url="https://s/")
    assert len(out) <= 3600 and out.endswith("…\nПолностью: https://s/")
    for tag in ("b", "code", "a", "pre"):
        assert out.count(f"<{tag}>") == out.count(f"</{tag}>")


def test_balance_anchor_and_partial_tag():
    assert _balance('text <a href="https://e/">link and more').rstrip() == "text"
    assert _balance('before <b>bold</b> middle <cod').rstrip() == "before <b>bold</b> middle"
    assert _balance('text <a href="https://exa').rstrip() == "text"


def test_link_at_truncation_boundary_is_dropped_cleanly():
    out = telegram_html("текст с [ссылкой](https://example.com/very/long/path/that/keeps/going/on) и текст", limit=40, more_url="https://s/")
    assert "href=\"" not in out or out.count("<a ") == out.count("</a>")
    assert "<a href=\"" not in out or out.count("<a ") == out.count("</a>")
    assert out.count("<") == out.count(">")
    assert out.endswith("…\nПолностью: https://s/")
