import re
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LANDING = REPO / "index.html"

VOID = {"meta", "link", "br", "img", "hr", "input", "path", "circle",
        "rect", "line", "polyline", "stop", "use"}


class BalanceChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"несбалансированный </{tag}>")
        else:
            self.stack.pop()


def landing_text():
    return LANDING.read_text(encoding="utf-8")


def test_html_balanced():
    checker = BalanceChecker()
    checker.feed(landing_text())
    assert not checker.errors and not checker.stack


def test_positioning_and_identity_present():
    text = landing_text()
    assert "Углублённая информатика и программирование" in text
    assert "Junior_IT" in text


def test_no_forbidden_words():
    text = landing_text().lower()
    for word in ("дружин", "отряд", "инспекц", "полици", "фсб", "ссср", "юдо"):
        assert word not in text, word


def test_no_links_to_unpublished():
    text = landing_text()
    assert "teacher/" not in text
    assert "live-code.md" not in text
    assert "homework/" not in text


def test_fallback_tracks_present_without_js():
    text = landing_text()
    assert 'id="course-map"' in text
    for chip in ("BOOK", "PY", "PAS", "OPS", "CS", "WEB"):
        assert chip in text, chip


def test_fetches_course_map():
    assert re.search(r"fetch\(['\"]course-map\.json['\"]\)", landing_text())
