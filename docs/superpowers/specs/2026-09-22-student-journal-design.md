# Журнал классного руководителя (student-journal)

Дата: 2026-09-22.
Статус: спека утверждена по секциям, реализация не начата.
Первый из трёх подпроектов «управление учениками»: журнал → посещаемость из
Zoom → доставка материалов (Telegram/Gmail). Два следующих — свои спеки; здесь
только точки стыковки.

## Задача

Учёт учеников был упрощён до `students/roster.txt` и заглушки. Нужен полный
журнал: карточка ученика, посещаемость, домашки со статусом сдачи, баллы,
заметки, статистика и хвосты — всё приватно, вне гита, с вводом через TUI после
занятия и с машинным каналом для будущей автоматики.

Решения брейншторма:

- **Модель оценивания — баллы** (не школьная шкала): копятся, с причиной и
  источником; тариф в отдельном файле, меняется без кода.
- **Ввод — TUI** (Textual), под ним ядро операций; CLI — тонкая обёртка для
  автоматики и агента, не для ручной работы.
- **Отчёты — только преподавателю** (MVP). Дайджесты родителям — не входит.
- **Хранилище — YAML по сущностям**: ростер + файл на занятие. Баллы внутри
  занятия — только дописываемый список (аудит без event-log).

## Границы

- `students/` — единственное место данных; в `.gitignore` остаётся; бэкап на
  NAS отдельным launchd-агентом.
- Имена детей не попадают в материалы, коммиты, спеку и тесты (фикстуры —
  вымышленные `alice`/`bob`).
- Подпроекты 2 и 3 пишут в журнал только через `ops`/CLI, схему не расширяют.
- Движок info-панели (terminal-commander) получает одну нейтральную добавку:
  цель `open` вида `run:<команда>` (плавающая панель Zellij).

## Данные

### `students/roster.yml`

```yaml
students:
  - id: alice            # [a-z0-9-], ключ везде
    name: "Алиса"         # как обращаемся
    full_name: "…"        # опционально
    nick: "alice_k"       # ник в Telegram/Zoom для автоматики
    zoom_names: ["Алиса", "Alice K"]   # как Zoom подписывает участника
    platform: mac         # mac | win
    contacts: {tg: "@…", email: "…", max: "…"}
    parent: {name: "…", tg: "@…", email: "…"}
    joined: 2026-09-09
    status: active        # active | paused | left
    notes: "…"
```

Обязательны `id` и `name`; `status` по умолчанию `active`, остальное опционально. `id` уникален. Секции неверной формы (список вместо mapping, нечисловой балл) — ошибка загрузки, не трейсбек.

### `students/journal/<YYYY-MM-DD>.yml` — одно занятие

```yaml
date: 2026-09-20
attendance:
  alice: present         # present | late | absent | recording
  bob: late
homework:                # домашки, выданные этим занятием
  python-01-first-run:
    alice: {status: accepted, at: 2026-09-22}
    bob: {status: rework, note: "broken.py без traceback"}
points:
  - {who: alice, amount: 2, reason: "присутствие", by: teacher}
  - {who: alice, amount: 2, reason: "сама нашла ошибку в traceback", by: teacher}
notes:
  bob: "опоздал на 10 минут, догнал к шагу 3"
```

- `date` обязателен и равен имени файла.
- Все `id` учеников существуют в ростере — иначе ошибка загрузки.
- `by` ∈ `teacher | zoom | telegram` — источник записи.
- Статусы домашки: `issued → submitted → accepted | rework`, из `rework` снова
  `submitted`. Другие переходы — отказ.

### `students/points.yml` — тариф

```yaml
presence: 2
late: 1
homework_accepted: 3
homework_after_rework: 2
activity_max: 3           # подсказка для формы, не ограничение
quiz_per_correct: 0.25    # зачёт по тренажёру: балл за правильный ответ
```

Нет файла — встроенные значения те же.

### Связь с планом занятия

`playground/<дата>/session.yml` — план; `students/journal/<дата>.yml` — факт.
Из плана берутся тема, `homework.items` (что выдавать) и `homework.due`
(дедлайн для хвостов). Нет плана на дату — занятие всё равно можно завести,
домашки тогда только руками.

## Ядро — `tools/journal/`

Чистый Python 3.11+, PyYAML; в `tools/.venv`, как остальные инструменты.

- **`model.py`** — dataclasses `Student`, `LessonRecord`, `HomeworkMark`,
  `PointEntry`, `Tariff`; валидация схемы; сообщения ошибок называют файл и
  `id`.
- **`store.py`** — `roster_path()`, `load_roster()`, `load_lessons()`,
  `load_lesson(date)`, `save_lesson(record)`. Корень — `<repo>/students/`,
  переопределяется переменной `JUNIOR_IT_STUDENTS` (тесты, бэкап). Запись
  атомарная (temp + rename), порядок ключей фиксирован — round-trip без диффа.
- **`ops.py`** — операции; каждая идемпотентна, создаёт файл занятия при
  необходимости, возвращает изменённую запись:
  - `mark_attendance(date, student, status)` — при `present`/`late`
    начисляет тарифный балл «присутствие»/«опоздание», если такой записи
    от `teacher` за этот день ещё нет; при смене на `absent` — снимает её.
  - `issue_homework(date, hw_id=None, students=None)` — по умолчанию
    `homework.items` из `session.yml` × присутствовавшие (`present|late|recording`).
  - `set_homework(date, hw_id, student, status, note=None)` — проверка
    перехода; `accepted` начисляет `homework_accepted` (или
    `homework_after_rework`, если до этого был `rework`), однократно.
  - `add_points(date, student, amount, reason, by="teacher")` — только
    дописывает.
  - `set_note(date, student, text)`.
- **`stats.py`** — на чтении, без хранимого состояния:
  - по ученику: занятий всего/был/опоздал/по записи; домашек
    выдано/сдано/принято/в доработке; баллы всего и за период
    (`since`); последнее занятие; **хвосты** — домашки в `issued`/`rework`
    старше `homework.due`, и `submitted` без решения дольше 3 дней;
  - по группе: суммы + рейтинг по баллам; занятия без журнала (план есть,
    факта нет) — тоже хвост.
- **`cli.py`** — `python3 tools/journal/cli.py <cmd>`:
  `attend <date> <student> <status>`, `hw <date> <hw_id> <student> <status> [--note]`,
  `points <date> <student> <amount> <reason> [--by]`, `note <date> <student> <text>`,
  `report [student]` (текст), `json` (полный снимок статистики). Коды: 0 ок,
  2 — ошибка аргументов/перехода, 3 — битые данные.

## TUI — `tools/journal/tui.py`

Textual (добавить в `tools/requirements.txt`). Три экрана, без мыши,
сохранение при каждом действии, тост на каждую клавишу
(`notify(markup=False, timeout=3)`).

1. **Группа** (старт): таблица ученик × последние 6 занятий глифами
   (`●` present, `◐` late, `○` absent, `▶` recording), колонки «баллы»,
   «дз принято/выдано», «хвосты». `↑↓` — выбор, `Enter` — ученик, `l` —
   выбрать занятие (список `journal/*.yml` + прошедшие `session.yml` без
   журнала с пометкой «не заполнено»), `q` — выход.
2. **Занятие**: шапка — дата и тема из плана. Список учеников: `Space`
   циклит посещаемость `present → late → absent → recording`, `h` циклит
   домашку `issued → submitted → accepted`, `r` — `rework`, `+`/`-` — баллы
   (Input причины в нижней строке, `Enter` подтверждает, `Esc` отменяет),
   `n` — заметка. Тарифные начисления видны в списке баллов. `Esc` — назад.
3. **Ученик**: карточка (без контактов), история по занятиям, список баллов с
   причиной и источником. `e` — `roster.yml` в `tc-edit`.

Запуск: `python3 tools/journal/tui.py [--date YYYY-MM-DD]` — с датой сразу
экран занятия. Битые данные — сообщение на стартовом экране, занятие не
открывается до починки (`e` открывает файл).

Цвета — роли темы (`green`/`yellow`/`red`/`dim`), без хексов.

## Стыковка с info-панелью

- `tools/info/students.py` (слой 2 info-панели) печатает JSON lines: строка на
  ученика `Алиса · 3/4 · дз 2/3 · 14 б` (`warn` при хвосте), первая строка
  `open: "run:python3 tools/journal/tui.py"`.
- Движок: `providers.open_cmd` — цель с префиксом `run:` →
  `["zellij", "action", "new-pane", "--floating", "--close-on-exit", "--",
  "bash", "-lc", "<команда>"]`, cwd — корень проекта. Отдельный коммит в
  vault terminal-commander, тест на разбор цели.

## Бэкап

- `tools/students_backup.sh`: `rsync -a --delete students/
  /Volumes/BACKUP-VIDEO/JuniorIT/students/`; шара не смонтирована — одна
  строка в лог и выход 0.
- launchd-агент `com.juniorit.students-backup`, раз в час, лог
  `~/Library/Logs/junior-it-students-backup.log`; plist и `setup.md` в
  `provisioning/students-backup/` по образцу `provisioning/zoom-pipeline/`.
- Карточка `schedule` в `.zellij/cockpit.yml`.

## Ошибки

- Битый YAML / схема — сообщение с файлом и `id`; CLI код 3; TUI — экран
  ошибки.
- Ученик вне ростера — ошибка загрузки, не тихий пропуск.
- Недопустимый переход статуса — отказ (CLI 2 / тост), файл не тронут.
- Нет `session.yml` на дату — предупреждение, домашки только руками.

## Тесты (`tools/tests/test_journal_*.py`, pytest)

- Ядро: загрузка/валидация на фикстурах (`alice`/`bob`); каждая операция —
  идемпотентность, автосоздание файла, тарифные начисления и их снятие,
  переходы статусов; `stats` — счётчики, хвосты по дедлайну и по «3 дня без
  решения», период.
- Store: атомарная запись, round-trip без диффа.
- CLI: коды возврата, `json`.
- TUI smoke (`run_test`): стартовый экран рендерит фикстурную группу; `Space`
  меняет посещаемость и файл на диске обновился; `q` выходит. Скриншот на
  реальном каталоге — для визуального ревью.

## Не входит в MVP

- Дайджесты и любые тексты родителям.
- Автоматика из Zoom (подпроект 2) и Telegram (подпроект 3).
- Уровни/бейджи за баллы, экспорт, редактирование ростера в форме, мышь.
