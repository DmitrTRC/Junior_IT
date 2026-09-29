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
    assert "homework/" not in text.split('<script')[0]      # в разметке ссылок нет; JS строит их из карты


def test_fallback_tracks_present_without_js():
    text = landing_text()
    assert 'id="course-map"' in text
    for chip in ("BOOK", "PY", "PAS", "OPS", "CS", "WEB"):
        assert chip in text, chip


def test_fetches_course_map():
    assert re.search(r"fetch\(['\"]course-map\.json['\"]\)", landing_text())


def test_inline_tokens_match_brand_css():
    css = (REPO / "meta" / "brand-tokens.css").read_text(encoding="utf-8")
    landing = landing_text()
    for name, value in re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})", css):
        assert f"{name}: {value}" in landing, f"{name} разошёлся с brand-tokens.css"


def test_module_nodes_link_to_all_materials():
    js = landing_text().split("<script")[-1]
    for key, label in (("slides", "слайды"), ("cheatsheet", "шпаргалка"), ("glossary", "словарик"), ("homework", "домашка")):
        assert re.search(r"links\.%s\b" % key, js), key
        assert label in js, label
    assert "module-links" in landing_text()


def test_homework_now_block_rendered_from_map():
    js = landing_text().split("<script")[-1]
    assert "homework_now" in js and "Домашка сейчас" in js


def test_fallback_track_cards_link_to_site():
    text = landing_text()
    for track in ("book", "python", "devops", "cs", "web"):
        assert f"github.com/DmitrTRC/Junior_IT/tree/main/tracks/{track}" not in text, track


def test_hero_gets_homework_button_from_map():
    js = landing_text().split("<script")[-1]
    assert "hero-homework" in js and "btn-row" in js


def test_landing_links_to_program_page():
    text = landing_text()
    assert text.count('href="program.html"') >= 2
    assert "Программа года" in text
