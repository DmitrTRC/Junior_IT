# Провайдеры info-панели Junior_IT (info-providers)

Дата: 2026-09-22.
Статус: спека утверждена по секциям, реализация не начата.
Слой 2 info-панели: движок (terminal-commander, спека
`2026-09-21-info-panel-design.md`) готов; журнал (`2026-09-22-student-journal-design.md`)
готов. Здесь — только то, что живёт в репо курса: провайдеры и манифест.

## Задача

Вкладка `info` у Junior_IT сейчас показывает встроенный дефолт (часы, git,
ссылки). Нужны боксы курса: ближайшее занятие, ученики, домашки, готовность
материалов, сводка по курсу. Движок про курс не знает — каждый бокс это
скрипт, печатающий JSON lines по контракту `command`.

Решения брейншторма: семь боксов (пять `command` + `clock` + `git`); один
CLI с подкомандами и модуль на бокс; чистые функции строк, тестируемые без
диска; приватность — на панель только имена.

## Боксы и правила

**Ближайшее занятие** — минимальная дата `playground/*/session.yml`, которая
≥ сегодня. Нет такой — последнее прошедшее, помеченное `warn` «план на
следующее не создан». Отсчёт: «сегодня» (`ok`), «завтра», «через N дн.».

| бокс | строки (по порядку) | стиль | Enter |
|---|---|---|---|
| **занятие** | `ср 24.09 20:00 · через 2 дня`; тема; плейлист `python-01-first-run · 35 мин` на модуль; `домашка до 23.09: python-01-first-run`; `буфер N мин` | заголовок `ok` сегодня / `warn` если план устарел; буфер `dim` | план → `session.yml`; модуль → `teacher/scenario.md` (нет — `module.yml`); домашка → `homework/<id>/task.md` |
| **ученики** | `журнал · N занятий`; на активного ученика `Неля · был 3/4 · дз 2/3 · 14 б`; `без журнала: 2026-09-13` на каждое | ученик `warn` при хвостах; без журнала `warn` | первая → `run:<tui>`; без журнала → `run:<tui> --date D`; ученик → `run:<tui>` |
| **домашки** | по выданным в журнале, свежие сверху: `python-01-first-run · сдано 1/3 · принято 0/3 · до 23.09`; домашка ближайшего плана, ещё не выданная — `не выдана` | все приняты `ok`; просрочка (due < today и не все приняты) `warn`; не выдана `dim` | `homework/<id>/task.md` |
| **готовность** | модуль плейлиста ближайшего занятия: `python-01 · scenario ✓ live-code ✓ slides ✓ cheatsheet ✓ glossary ✓ · validate ✓`; строка домашки плана `task.md ✓/✗` | все ✓ `ok`; нет файла `warn`; `validate_module` вернул ошибки — `err` с первой ошибкой в тексте | сценарий модуля (нет — `module.yml`); домашка → `task.md` |
| **курс** | `занятий проведено: N`; `модулей: done/всего`; по трекам `python 1/2 · devops 1/1 · …` | `dim` | GH Pages `https://dmitrtrc.github.io/Junior_IT/` |
| **clock**, **git** | движок | | |

`<tui>` = `tools/.venv/bin/python tools/journal/tui.py`. Нет ростера —
«ученики» печатает одну строку `warn` «нет students/roster.yml», «домашки» —
`dim` «нет журнала»; это не ошибки.

Файлы анатомии для «готовности»: `teacher/scenario.md`, `shared/live-code.md`,
`shared/slides.html`, `student/cheatsheet.html`, `student/glossary.md`.
Домашка модуля — `module.yml: homework` → `homework/<id>/task.md`.

## Пакет `tools/info/`

- **`common.py`** — `REPO_ROOT`; `Line(text, open=None, style=None)`;
  `emit(lines)` печатает `{"lines": [...]}` (`ensure_ascii=False`);
  `next_session(sessions, today) -> (session | None, stale: bool)`;
  `countdown(day, today) -> str`; `weekday_ru(day)`; `module_dir(module_id)`,
  `scenario_path(module_id)`, `homework_task(hw_id)`. Ничего про экран.
- **`lesson.py`, `students.py`, `homework.py`, `readiness.py`, `course.py`** —
  по одной чистой функции `lines(...) -> list[Line]`:
  `lesson.lines(session, stale, today)`, `students.lines(group, tui_cmd)`,
  `homework.lines(lessons, plans, today)`,
  `readiness.lines(playlist_modules, validate_fn, repo_root)`,
  `course.lines(modules, sessions, today)`.
- **`cli.py <box> [--today D] [--repo P] [--students R]`** — грузит данные
  (`build_course_map.load_modules/load_sessions/module_statuses`,
  `journal.store/stats`, `module_schema.validate_module`), зовёт `lines`,
  печатает. Самолокация `sys.path`, как у `journal/cli.py`. Режим `+x`.
  Коды: 0 ок; 2 неизвестный бокс/аргументы; 3 битые данные.

## Ошибки

- Битый `session.yml` или журнал — исключение наверх → stderr с файлом, код
  3 → движок показывает `⚠` с хвостом stderr в этом боксе, остальные живут.
- Отсутствие ростера/журнала — не ошибка (см. таблицу).
- Нет ни одного `session.yml` — «занятие» печатает `warn` «планов нет»,
  «готовность» — `dim` «нет плейлиста».

## Приватность

На панель попадают только `name` из ростера и счётчики. Контакты, заметки,
`full_name` — никогда. Скриншот с реальными именами — только в scratchpad
сессии, не в репо и не в workspace плана.

## Манифест `.zellij/info.yml`

```yaml
version: 1
layout:
  - [{box: lesson, weight: 2}, {box: students, weight: 2}, {box: clock, weight: 1}]
  - [{box: homework, weight: 2}, {box: readiness, weight: 3}, {box: course, weight: 1}, {box: git, weight: 1}]
boxes:
  - id: clock
    type: clock
  - id: git
    type: git
    title: "хвосты"
  - id: lesson
    type: command
    title: "занятие"
    run: "tools/.venv/bin/python tools/info/cli.py lesson"
    interval: 300
  - id: students
    type: command
    title: "ученики"
    run: "tools/.venv/bin/python tools/info/cli.py students"
    interval: 120
  - id: homework
    type: command
    title: "домашки"
    run: "tools/.venv/bin/python tools/info/cli.py homework"
    interval: 300
  - id: readiness
    type: command
    title: "готовность"
    run: "tools/.venv/bin/python tools/info/cli.py readiness"
    interval: 120
  - id: course
    type: command
    title: "курс"
    run: "tools/.venv/bin/python tools/info/cli.py course"
    interval: 600
```

## Тесты (`tools/tests/test_info_*.py`)

- Чистые функции: ближайшее занятие (будущее / только прошедшие / сегодня /
  нет планов), отсчёт и день недели, строки каждого бокса — стили и
  `open`-цели, «нет ростера», просрочка домашки, «не выдана», модуль без
  файла, красный `validate`.
- CLI smoke: каждая подкоманда на фикстурном репо (`tmp_path` с
  `playground/`, модули через `make_module` из `test_build_course_map.py`,
  `students/` из `conftest.journal_root`) — JSON разбирается, `lines`
  непустой; коды 0/2/3.
- Манифест: `cockpit.info.manifest.load_info_manifest` из деплойнутого
  venv движка — без ошибок и предупреждений.
- Скриншот `tc-info` на реальном репо (headless `run_test`): семь боксов,
  ни одного `⚠`.

## Не входит

Сетевые боксы (слой 3), редактирование планов из панели, кэш между тиками,
ученические контакты на экране.
