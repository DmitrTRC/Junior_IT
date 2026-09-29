"""Страницы домашек и словариков для сайта: homework/<id>/task.md -> <out>/homework/<id>/index.html,
tracks/<track>/<module>/student/glossary.md -> тот же путь с .html.

Публикуются страница и вложения (стартовые файлы); task.md и tests/ — нет.
Запуск: build_homework_pages.py <repo_root> <out_dir>
"""
from __future__ import annotations
import html
import re
import shutil
import sys
from pathlib import Path

import markdown

SKIP_FILES = {"task.md", "index.html"}
SKIP_DIRS = {"tests"}
SITE_URL = "https://dmitrtrc.github.io/Junior_IT/"

TRACK_COLORS = {
    "book": ("#7aa2ff", "#2b4fa8"),
    "python": ("#00ffc8", "#00806a"),
    "pascal": ("#ff5722", "#b3350f"),
    "devops": ("#00e676", "#00803d"),
    "cs": ("#ff0096", "#a8005f"),
    "web": ("#8892b0", "#4a5568"),
}

PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · Junior_IT</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@700&family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ background: #faf7f2; color: #1a1a1a; font-family: 'Manrope', sans-serif; line-height: 1.6; }}
  body {{ padding: 24px 16px 60px; }}
  .container {{ max-width: 820px; margin: 0 auto; }}
  header {{ background: linear-gradient(135deg, #1a1a2e, #16213e 60%, #0f3460); color: #fff;
            padding: 36px 30px; border-radius: 24px; margin-bottom: 24px; }}
  .kicker {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; color: {track_color}; letter-spacing: .08em; }}
  h1 {{ font-family: 'Rubik', sans-serif; font-size: 30px; margin-top: 8px; }}
  main h2 {{ font-family: 'Rubik', sans-serif; font-size: 22px; margin: 28px 0 10px; }}
  main h3 {{ font-family: 'Rubik', sans-serif; font-size: 18px; margin: 22px 0 8px; }}
  main p, main li {{ margin-bottom: 10px; }}
  main ul, main ol {{ padding-left: 24px; }}
  main blockquote {{ border-left: 4px solid #ffd60a; padding: 8px 14px; background: #fff8dc; border-radius: 8px; margin: 14px 0; }}
  code {{ font-family: 'JetBrains Mono', monospace; font-size: .92em; background: #eee9e0; padding: 1px 5px; border-radius: 5px; }}
  pre {{ background: #15151c; color: #7fd0ff; padding: 14px 16px; border-radius: 12px; overflow-x: auto; margin: 14px 0; }}
  pre code {{ background: none; color: inherit; padding: 0; }}
  table {{ border-collapse: collapse; margin: 14px 0; }}
  td, th {{ border: 1px solid #d9d2c5; padding: 6px 10px; }}
  .files {{ margin-top: 32px; padding: 18px 20px; background: #fff; border-radius: 16px; box-shadow: 0 4px 18px rgba(0,0,0,.06); }}
  .files h2 {{ margin-top: 0; }}
  a.file {{ display: inline-block; font-family: 'JetBrains Mono', monospace; background: #1a1a2e; color: {track_color};
            padding: 8px 14px; border-radius: 10px; text-decoration: none; margin: 6px 8px 0 0; }}
  a.file:hover {{ background: #0f3460; }}
  footer {{ margin-top: 40px; font-size: 14px; color: #666; }}
  footer a {{ color: {track_ink}; }}
  @media (max-width: 600px) {{
    table, tbody, tr, td {{ display: block; width: 100%; }}
    thead {{ display: none; }}
    tr {{ border: 1px solid #d9d2c5; border-radius: 12px; margin-bottom: 12px; overflow: hidden; }}
    td {{ border: 0; border-top: 1px solid #eee9e0; }}
    td:first-child {{ border-top: 0; font-weight: 700; background: #f3efe7; }}
  }}
</style>
</head>
<body>
<div class="container">
<header>
  <div class="kicker">{kicker}</div>
  <h1>{title}</h1>
</header>
<main>
{body}
</main>
{files}
<footer>Материалы курса — <a href="{site}">{site}</a></footer>
</div>
</body>
</html>
"""

FILES = """<section class="files">
  <h2>Вложения</h2>
  {links}
</section>"""


def colors_for_track(track: str) -> tuple[str, str]:
    """Пара цветов трека (яркий для тёмного фона, чернильный для светлого). Неизвестный трек → жёлтый/чёрный."""
    return TRACK_COLORS.get(track, ("#ffd60a", "#1a1a1a"))


def track_colors(hw_id: str) -> tuple[str, str]:
    """Цвета трека по префиксу hw_id (всё до первого '-')."""
    return colors_for_track(hw_id.split("-")[0] if "-" in hw_id else hw_id)


def split_title(md_text: str) -> tuple[str, str]:
    """Первый заголовок первого уровня — в шапку; из тела он убирается."""
    match = re.search(r"^# (.+)$", md_text, flags=re.MULTILINE)
    if not match:
        return "Домашка", md_text
    body = md_text[:match.start()] + md_text[match.end():]
    return match.group(1).strip(), body.lstrip("\n")


def render_page(md_text: str, kicker: str, track: str, attachments: list[str]) -> str:
    """Страница ученика в бренде: шапка с подписью-кикером, тело из Markdown, вложения."""
    title, body_md = split_title(md_text)
    body = markdown.markdown(body_md, extensions=["fenced_code", "tables"])
    links = "\n  ".join(
        f'<a class="file" href="{html.escape(name, quote=True)}" download>{html.escape(name)}</a>'
        for name in attachments)
    files = FILES.format(links=links) if attachments else ""
    track_color, track_ink = colors_for_track(track)
    return PAGE.format(title=html.escape(title), kicker=html.escape(kicker), body=body, files=files, site=SITE_URL,
                       track_color=track_color, track_ink=track_ink)


def render_task(md_text: str, hw_id: str, attachments: list[str]) -> str:
    return render_page(md_text, f"ДОМАШКА · {hw_id}", hw_id.split("-")[0], attachments)


def render_glossary(md_text: str, module_id: str) -> str:
    return render_page(md_text, f"СЛОВАРИК · {module_id}", module_id.split("/")[0], [])


def attachments_for(hw_dir: Path) -> list[Path]:
    return sorted(p for p in hw_dir.iterdir()
                  if p.is_file() and p.name not in SKIP_FILES and not p.name.startswith("."))


def build(repo_root: Path, out_dir: Path) -> list[Path]:
    homework = Path(repo_root) / "homework"
    written: list[Path] = []
    if not homework.is_dir():
        return written
    for task in sorted(homework.glob("*/task.md")):
        hw_dir = task.parent
        target = Path(out_dir) / "homework" / hw_dir.name
        target.mkdir(parents=True, exist_ok=True)
        files = attachments_for(hw_dir)
        for src in files:
            shutil.copy2(src, target / src.name)
        page = target / "index.html"
        page.write_text(render_task(task.read_text(encoding="utf-8"), hw_dir.name, [p.name for p in files]),
                        encoding="utf-8")
        written.append(page)
    return written


def build_glossaries(repo_root: Path, out_dir: Path) -> list[Path]:
    """tracks/<track>/<module>/student/glossary.md -> <out>/tracks/<track>/<module>/student/glossary.html."""
    repo_root, written = Path(repo_root), []
    for md in sorted(repo_root.glob("tracks/*/*/student/glossary.md")):
        module_id = f"{md.parents[2].name}/{md.parents[1].name}"
        page = Path(out_dir) / md.relative_to(repo_root).with_suffix(".html")
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(render_glossary(md.read_text(encoding="utf-8"), module_id), encoding="utf-8")
        written.append(page)
    return written


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2:
        print("usage: build_homework_pages.py <repo_root> <out_dir>", file=sys.stderr)
        return 2
    pages = build(Path(args[0]), Path(args[1]))
    glossaries = build_glossaries(Path(args[0]), Path(args[1]))
    print(f"домашки: {len(pages)} страниц, словарики: {len(glossaries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
