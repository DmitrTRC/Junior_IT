#!/usr/bin/env python3
"""Одна строка статуса группы для status-карточки кокпита.

Данные учеников приватны (students/ не в гите) — файла может не быть.
Тогда печатаем нейтральную заглушку и выходим с кодом 0.
"""
from pathlib import Path

roster = Path(__file__).resolve().parent.parent / "students" / "roster.txt"
if not roster.exists():
    print("группа: нет данных (students/ приватно)")
    raise SystemExit(0)

lines = [ln for ln in roster.read_text().splitlines() if ln.strip()]
print(f"учеников: {len(lines)}")
