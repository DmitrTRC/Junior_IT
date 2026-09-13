#!/usr/bin/env python3
"""Валидатор банка вопросов тренажёра: textbook/quizzes/*.json.

Схема — docs/superpowers/specs/2026-09-13-trainer-design.md. Ошибки
собираются списком, а не бросаются: одна прогонка показывает всё сразу.
"""

import json
import sys
from pathlib import Path

TYPES = {"single", "multi", "number", "text", "match", "order", "find-error"}
MIN_QUESTIONS = 3


def _is_str_list(value, minimum=2):
    return (isinstance(value, list) and len(value) >= minimum
            and all(isinstance(v, str) and v.strip() for v in value))


def _check_question(q, path, errors):
    qid = q.get("id", "?")
    for field in ("id", "source", "q", "why"):
        if not isinstance(q.get(field), str) or not q[field].strip():
            errors.append(f"{path}: вопрос {qid}: пустое поле {field}")
    if not isinstance(q.get("terms"), list) or not all(
            isinstance(t, dict) and t.get("ru") and t.get("en")
            for t in q.get("terms", [])):
        errors.append(f"{path}: вопрос {qid}: terms — список пар ru/en")
    qtype = q.get("type")
    options, answer = q.get("options"), q.get("answer")
    if qtype not in TYPES:
        errors.append(f"{path}: вопрос {qid}: неизвестный type {qtype!r}")
    elif qtype in ("single", "find-error"):
        if not _is_str_list(options):
            errors.append(f"{path}: вопрос {qid}: options — список строк, минимум 2")
        elif not (isinstance(answer, int) and 0 <= answer < len(options)):
            errors.append(f"{path}: вопрос {qid}: answer вне диапазона options")
    elif qtype == "multi":
        if not _is_str_list(options):
            errors.append(f"{path}: вопрос {qid}: options — список строк, минимум 2")
        elif (not isinstance(answer, list) or not answer
              or len(set(answer)) != len(answer)
              or not all(isinstance(a, int) and 0 <= a < len(options) for a in answer)):
            errors.append(f"{path}: вопрос {qid}: answer — список индексов без дублей в диапазоне options")
    elif qtype == "number":
        if options is not None:
            errors.append(f"{path}: вопрос {qid}: у number не бывает options")
        if not isinstance(answer, (int, float)) or isinstance(answer, bool):
            errors.append(f"{path}: вопрос {qid}: answer у number — число")
    elif qtype == "text":
        if options is not None:
            errors.append(f"{path}: вопрос {qid}: у text не бывает options")
        accepted = answer if isinstance(answer, list) else [answer]
        if not _is_str_list(accepted, minimum=1):
            errors.append(f"{path}: вопрос {qid}: answer у text — непустая строка или их список")
    elif qtype == "match":
        left = options.get("left") if isinstance(options, dict) else None
        right = options.get("right") if isinstance(options, dict) else None
        if not _is_str_list(left) or not _is_str_list(right):
            errors.append(f"{path}: вопрос {qid}: options у match — left и right, минимум по 2")
        elif (not isinstance(answer, list) or len(answer) != len(left)
              or not all(isinstance(a, int) and 0 <= a < len(right) for a in answer)):
            errors.append(f"{path}: вопрос {qid}: answer у match — индекс right на каждый left")
    elif qtype == "order":
        if not _is_str_list(options):
            errors.append(f"{path}: вопрос {qid}: options — список строк, минимум 2")
        elif not (isinstance(answer, list) and sorted(answer) == list(range(len(options)))):
            errors.append(f"{path}: вопрос {qid}: answer у order — перестановка индексов options")


def validate(repo_root):
    errors = []
    bank_dir = Path(repo_root) / "textbook" / "quizzes"
    manifest_path = bank_dir / "index.json"
    if not manifest_path.is_file():
        return [f"{manifest_path}: манифест не найден"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    listed = set()
    for bank in manifest.get("banks", []):
        seen_ids = {}
        for name in bank.get("files", []):
            listed.add(name)
            path = bank_dir / name
            if not path.is_file():
                errors.append(f"{path}: файл из манифеста не найден")
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            for field in ("grade", "chapter", "paragraph", "title"):
                if field not in data:
                    errors.append(f"{path}: в шапке нет поля {field}")
            if not str(data.get("paragraph", "")).startswith(f"{bank['chapter']}."):
                errors.append(f"{path}: paragraph не из главы {bank['chapter']}")
            questions = data.get("questions", [])
            if len(questions) < MIN_QUESTIONS:
                errors.append(f"{path}: меньше 3 вопросов — билет 3x5 не собрать")
            for q in questions:
                _check_question(q, path.name, errors)
                if q.get("id") in seen_ids:
                    errors.append(f"{path.name}: дубль id {q['id']} (уже в {seen_ids[q['id']]})")
                seen_ids[q.get("id")] = path.name
    stray = {p.name for p in bank_dir.glob("[0-9][0-9]-*.json")} - listed
    for name in sorted(stray):
        errors.append(f"{name}: файла нет в манифесте")
    return errors


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    repo_root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    errors = validate(repo_root)
    for e in errors:
        print(f"quizzes: {e}", file=sys.stderr)
    if errors:
        return 1
    print("quizzes: банк валиден")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
