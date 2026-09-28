from datetime import date

from comms.drafts import lesson_date, max_section, new_drafts

DRAFT = "## Фактические тайминги\n\nтекст\n\n## Сообщение в MAX\n\nДобрый вечер!\n\nЗапись: https://z/x\n\n## Ещё\n\nхвост\n"


def test_new_drafts_sorted_and_unseen(tmp_path):
    for name in ("lesson-2026-09-27-1700-analysis.md", "lesson-2026-09-20-1731-analysis.md", "other.md"):
        (tmp_path / name).write_text(DRAFT, encoding="utf-8")
    found = new_drafts(tmp_path, seen=["lesson-2026-09-20-1731-analysis.md"])
    assert [p.name for p in found] == ["lesson-2026-09-27-1700-analysis.md"]
    assert new_drafts(tmp_path / "nope", seen=[]) == []


def test_max_section_and_date(tmp_path):
    assert max_section(DRAFT) == "Добрый вечер!\n\nЗапись: https://z/x"
    assert max_section("## Только тайминги\n\nx") is None
    assert lesson_date(tmp_path / "lesson-2026-09-27-1700-analysis.md") == date(2026, 9, 27)
    assert lesson_date(tmp_path / "other.md") is None
