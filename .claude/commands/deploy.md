---
description: Ревью изменений, commit и push в main (триггерит GH Pages)
argument-hint: ["сообщение коммита"]
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(git log:*)
---

Текущее состояние репозитория:

- Статус: !`git status --short`
- Изменения: !`git diff --stat`

## Что сделать

1. Покажи Димасу краткое резюме: какие файлы меняются и зачем. **Не коммить молча.**
2. Убедись, что не уходит приватное/генерируемое (`students/`, `graphify-out/`,
   `.claude/settings.local.json` — должны быть в `.gitignore`).
3. Если правились материалы для детей/родителей — напомни прогнать `/brand-check`
   перед пушем (запреты из `CLAUDE.md`).
4. `git add` нужных файлов → `git commit`. Сообщение: **$ARGUMENTS**; если пусто —
   сгенерируй краткое осмысленное в стиле истории репо (одна строка, по сути правки).
5. `git push origin main`.
6. Напомни, что push в `main` запускает GH Pages auto-deploy, и дай ссылки:
   - https://dmitrtrc.github.io/Junior_IT/
   - https://github.com/DmitrTRC/Junior_IT/actions (статус деплоя)
