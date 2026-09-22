#!/usr/bin/env python3
"""Одна строка статуса группы для status-карточки кокпита.

Данные учеников приватны (students/ не в гите) — ростера может не быть.
Тогда печатаем нейтральную заглушку и выходим с кодом 0.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from journal import store
    from journal.model import JournalError
except ModuleNotFoundError:  # системный python без pyyaml — карточка не должна падать
    print("группа: нужен tools/.venv (pyyaml)")
    raise SystemExit(0)

try:
    roster = store.load_roster()
except JournalError:
    print("группа: нет данных (students/roster.yml)")
    raise SystemExit(0)

active = [s for s in roster if s.status == "active"]
print(f"учеников: {len(active)}")
