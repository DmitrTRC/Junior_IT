from pathlib import Path

from module_schema import TRACKS, TRACK_TOKEN

REPO = Path(__file__).resolve().parents[2]
TOKENS_CSS = REPO / "meta" / "brand-tokens.css"


def test_every_track_has_dark_and_ink_token():
    css = TOKENS_CSS.read_text(encoding="utf-8")
    for track in TRACKS:
        short = TRACK_TOKEN[track]
        assert f"--track-{short}:" in css, f"нет тёмного токена для трека {track}"
        assert f"--track-{short}-ink:" in css, f"нет печатного токена для трека {track}"


def test_base_palette_survives():
    css = TOKENS_CSS.read_text(encoding="utf-8")
    for token, value in [
        ("--bg", "#0a0a14"),
        ("--card", "#1a1a2e"),
        ("--yellow", "#ffd60a"),
        ("--bg-light", "#faf7f2"),
    ]:
        assert f"{token}: {value}" in css, f"базовый токен {token} потерян или изменён"
