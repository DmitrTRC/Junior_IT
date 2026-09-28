"""Черновики текста через `claude -p` под сессией Димаса. Ответ — только текст, детям не уходит сам."""
from __future__ import annotations
import logging
import subprocess
from pathlib import Path

from comms.config import Config

log = logging.getLogger("comms.claude")
CLAUDE_TIMEOUT = 900
PROMPTS = Path(__file__).resolve().parent / "prompts"
KINDS = ("answer", "review", "task")


class SafeDict(dict):
    def __missing__(self, key):
        return ""


def render_prompt(kind: str, fields: dict) -> str:
    if kind not in KINDS:
        raise ValueError(f"неизвестный вид черновика {kind!r}")
    template = (PROMPTS / f"{kind}.md").read_text(encoding="utf-8")
    rules = (PROMPTS / "_rules.md").read_text(encoding="utf-8")
    return template.format_map(SafeDict({**fields, "rules": rules}))


def draft(kind: str, fields: dict, cfg: Config, runner) -> str | None:
    prompt = render_prompt(kind, fields)
    try:
        result = runner(list(cfg.claude_cmd), timeout=CLAUDE_TIMEOUT, stdin_text=prompt)
    except subprocess.TimeoutExpired:
        log.warning("claude -p %s: не ответил за %s с", kind, CLAUDE_TIMEOUT)
        return None
    text = (result.stdout or "").strip()
    if result.returncode != 0 or not text:
        log.warning("claude -p %s: код %s, %s", kind, result.returncode, (result.stderr or "").strip()[:200])
        return None
    return text
