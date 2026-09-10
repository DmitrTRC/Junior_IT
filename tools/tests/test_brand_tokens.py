from pathlib import Path

from module_schema import TRACKS, TRACK_TOKEN

REPO = Path(__file__).resolve().parents[2]
TOKENS_CSS = REPO / "meta" / "brand-tokens.css"


TRACK_TOKEN_VALUES = {
    "book": ("#7aa2ff", "#2b4fa8"),
    "python": ("#00ffc8", "#00806a"),
    "pascal": ("#ff5722", "#b3350f"),
    "devops": ("#00e676", "#00803d"),
    "cs": ("#ff0096", "#a8005f"),
    "web": ("#8892b0", "#4a5568"),
}


def test_every_track_has_dark_and_ink_token():
    css = TOKENS_CSS.read_text(encoding="utf-8")
    for track in TRACKS:
        short = TRACK_TOKEN[track]
        dark, ink = TRACK_TOKEN_VALUES[track]
        assert f"--track-{short}: {dark}" in css, f"тёмный токен трека {track} потерян или изменён"
        assert f"--track-{short}-ink: {ink}" in css, f"печатный токен трека {track} потерян или изменён"


def test_base_palette_survives():
    css = TOKENS_CSS.read_text(encoding="utf-8")
    for token, value in [
        ("--bg", "#0a0a14"),
        ("--card", "#1a1a2e"),
        ("--card-2", "#16213e"),
        ("--deep", "#0f3460"),
        ("--yellow", "#ffd60a"),
        ("--orange", "#ff5722"),
        ("--green", "#00e676"),
        ("--cyan", "#00ffc8"),
        ("--magenta", "#ff0096"),
        ("--bg-light", "#faf7f2"),
    ]:
        assert f"{token}: {value}" in css, f"базовый токен {token} потерян или изменён"
