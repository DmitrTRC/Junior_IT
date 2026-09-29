from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / "program.html"
VOID = {"meta", "link", "br", "img", "hr", "input"}
FORBIDDEN = ("дружин", "отряд", "контрол", "проверк", "инспекц")
KID_NAMES = ("Неля", "Маша", "Мария", "Матвей")


class BalanceChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unbalanced </{tag}> (stack: {self.stack[-3:]})")
        else:
            self.stack.pop()


def page_text():
    return PAGE.read_text(encoding="utf-8")


def js_text():
    return page_text().split("<script")[-1]


def test_page_is_balanced_html():
    checker = BalanceChecker()
    checker.feed(page_text())
    assert not checker.errors and not checker.stack


def test_page_fetches_program_json_and_has_fallback():
    assert "fetch('program.json')" in js_text()
    assert "Программа пока не собрана" in js_text()


def test_three_views_and_default():
    text = page_text()
    for view in ("student", "parents", "why"):
        assert f'data-view="{view}"' in text
    js = js_text()
    assert "return 'parents';" in js
    assert js.index("location.hash") < js.index("localStorage.getItem")   # hash важнее сохранённого выбора


def test_brand_and_forbidden_words():
    text = page_text()
    assert "Rubik" in text and "Manrope" in text and "JetBrains+Mono" in text
    assert "#0a0a14" in text and "#ffd60a" in text
    lower = text.lower()
    assert not any(word in lower for word in FORBIDDEN)
    assert not any(name in text for name in KID_NAMES)
