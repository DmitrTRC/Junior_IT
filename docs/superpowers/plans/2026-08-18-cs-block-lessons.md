# Блок «Компьютер изнутри» (cs-01, cs-02) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Два полных урока курса `lessons/lesson-cs-01-computer/` и `lessons/lesson-cs-02-layers/` со всеми атрибутами анатомии + обвязка (лендинг, CLAUDE.md, postmortem).

**Architecture:** Статические HTML/CSS/JS-материалы без сборки и фреймворков. Каждый урок — папка с фиксированным набором файлов; слайды — самодостаточный deck по образцу `lesson-01`, демки — одиночные HTML-страницы с inline-JS. Спека: `docs/superpowers/specs/2026-08-18-cs-block-lessons-design.md`.

**Tech Stack:** vanilla HTML/CSS/JS, SVG-графика inline, Google Fonts (стек эталона), Markdown для сценариев.

## Global Constraints

- Язык материалов — русский, с детьми на «ты». Идентификаторы и код — английские.
- Палитра — только токены бренд-кита: `--bg #0a0a14`, `--card #1a1a2e`, `--card-2 #16213e`, `--deep #0f3460`, `--yellow #ffd60a`, `--orange #ff5722`, `--green #00e676`, `--cyan #00ffc8`, `--magenta #ff0096`, светлый фон печати `#faf7f2`.
- Шрифты: Space Grotesk 700 (заголовки), Manrope 400/500/600 (текст), JetBrains Mono 400/700 (код). Шрифтовый стек копировать из эталонных файлов, не менять.
- Графика — только inline-SVG в бренд-палитре. Никаких стоковых картинок и внешних генераторов.
- Никаких хрупких `position:absolute`-декораций; всё на flex/grid.
- ⛔ Запреты проекта: никакой символики СССР и силовых ведомств, ни слова «дружина». Байка про троичный компьютер — только в scenario.md, формулировка «в 1950-е в московском университете построили…».
- В первых уроках курса не всплывают «семантика», «DOCTYPE», «валидация», «парсинг», «DOM» — в cs-блоке их тоже нет.
- Эмодзи: в HTML-контенте можно (по образцу лендинга), в коммитах / идентификаторах / именах файлов — нет.
- Комментарии в коде — минимум, только неочевидное.
- Каждый коммит завершать трейлером:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- `git push` НЕ делать. Только коммиты.
- Сырьё (расшифровки занятий) — `recordings/transcripts/*.txt`, вне гита. Использовать только для сверки формулировок; никакие персональные детали (имена, обстоятельства ученицы) в материалы не переносить.

**Эталоны стиля (читать перед соответствующей задачей):**

| Что делаем | Эталон |
|---|---|
| slides.html | `lessons/lesson-01-html-css/slides.html` (структура deck: `.slide`/`.active`, per-slide `#sN`-стили, nav prev/next + стрелки клавиатуры, `.keyhint`) |
| README.md, scenario.md, glossary.md, live-code.md | `lessons/lesson-02d-js-loops/` (те же файлы) |
| cheatsheet.html, homework.html | `lessons/lesson-02f-js-functions/cheatsheet.html` (светлая печатная палитра `#faf7f2`/`#1a1a1a`, тёмный header-card, жёлтые акценты) |
| index-final.html | `lessons/lesson-02f-js-functions/index-final.html` (тёмный конспект ведущего, консольная Dracula-палитра) |
| Карточка урока на лендинге | `index.html:951-969` (блок `.js-lesson`) |

---

### Task 1: cs-01 — Markdown-ядро (README, scenario, glossary, live-code)

**Files:**
- Create: `lessons/lesson-cs-01-computer/README.md`
- Create: `lessons/lesson-cs-01-computer/scenario.md`
- Create: `lessons/lesson-cs-01-computer/glossary.md`
- Create: `lessons/lesson-cs-01-computer/live-code.md`

**Interfaces:**
- Consumes: спека (тайминг, состав), эталоны `lessons/lesson-02d-js-loops/*.md`.
- Produces: нумерацию слайдов S1–S14 (список ниже), на которую ссылаются Task 2 (slides.html) и Task 4 (index-final.html). Менять состав/порядок слайдов после этой задачи нельзя.

**Канонический список слайдов cs-01 (S1–S14)** — используется во всех задачах урока:

| № | Слайд | Содержание |
|---|---|---|
| S1 | Титул | «Компьютер изнутри», kicker `// блок «компьютер изнутри» · урок 1`, чипы: «⚙️ железо», «🧠 CPU», «💾 память» |
| S2 | Зачем | «Можно писать код и не знать, что под капотом. Но сильным программистом так не стать». Пользователь видит окна — программист видит слои |
| S3 | Материнская плата | Пустая SVG-схема: большой скруглённый прямоугольник «материнская плата», подпись «все главные детали живут на одной плате» |
| S4 | CPU и «часики» | На схеме появляется квадрат CPU. Выполняет команды одну за другой по тикам; частота = тики в секунду; 3,5 ГГц = 3,5 млрд тиков |
| S5 | Нули и единицы | «Есть напряжение = 1, нет напряжения = 0». Вся речь компьютера состоит из этого |
| S6 | RAM | На схеме появляется RAM: полка ячеек с адресами 0, 1, 2, 3… — «как дома на улице, только счёт с нуля» |
| S7 | RAM vs SSD | Таблица-сравнение: RAM быстрая/дорогая/забывает при выключении — SSD медленнее/дешевле/помнит. Упомянуть VRAM видеокарты |
| S8 | Шина | Линия CPU↔RAM из 64 «проводочков»: разрядность. По каждому бежит 0 или 1 |
| S9 | Полная схема | + блок Input/Output, USB, клавиатура, монитор, фигурка пользователя. Схема собрана целиком |
| S10 | POST | Включение → самопроверка Power-On Self-Test. «Такая же есть в микроволновке и стиральной машине» |
| S11 | Эстафета загрузки | Цепочка стрелок: ROM (BIOS/UEFI) → загрузочная запись → загрузчик → ОС |
| S12 | Дерево ОС | MS-DOS → Windows; Unix → Linux → Android; Unix → macOS/iOS. Простое SVG-дерево |
| S13 | 85% мира | Пирог: большинство устройств планеты — Unix/Linux (телефоны, машины, часы, кофеварки). Плашка «даже Windows встроил себе Linux — WSL» |
| S14 | Итог | Полная схема + путь загрузки + «дальше: слои и язык машины» + «шпаргалка и домашка уже в чате» |

- [ ] **Step 1: Прочитать эталоны и написать README.md**

Прочитать `lessons/lesson-02d-js-loops/README.md` (структура) и спеку. Написать README по той же схеме:
- Шапка: тема «Как устроен компьютер и что происходит при включении», 60 мин (потолок 75), возраст 11–14, место в курсе: «блок "Компьютер изнутри", урок 1 — отступление от JS-линейки в сторону общего IT-образования».
- «Зачем этот урок»: без понимания «что под капотом» программист остаётся слабым; JS-блок дал первые программы — теперь смотрим, где они живут.
- «Что ребёнок умеет к концу» (7–8 пунктов): называет главные части (материнка, CPU, RAM, SSD, ввод-вывод); объясняет «частота = часики»; объясняет 0/1 через напряжение; понимает разницу RAM/SSD; рассказывает путь включения POST → BIOS/UEFI → загрузчик → ОС; знает, что Windows/macOS/Linux — родственники Unix, а Android — Linux; может найти характеристики своего компьютера.
- «Связь с соседними уроками»: назад — блок 2.x (JS в консоли), вперёд — cs-02 (слои и язык машины). Хард/софт-скиллы — ссылкой на `../../docs/soft-vs-hard-skills.html`, в урок не входят.
- Таблица файлов со статусами (по образцу 02d).

- [ ] **Step 2: Написать scenario.md**

Стиль и рубрикацию взять из `lessons/lesson-02d-js-loops/scenario.md` (поминутные блоки, реплики ведущего, пинги, чек-лист готовности в конце). Тайминг из спеки:

| Мин | Блок | Слайды |
|---|---|---|
| 0–5 | Зачем заглядывать внутрь | S1–S2 |
| 5–15 | Материнка → CPU, «часики», регистры | S3–S5 |
| 15–22 | RAM vs SSD/HDD, VRAM + байка про майнинг | S6–S7 |
| 22–30 | Адреса, Instruction Pointer, шина, 64 бита | S8 |
| 30–35 | Ввод-вывод, появляется пользователь | S9 |
| 35–47 | POST → BIOS/UEFI → загрузчик → ОС + демка boot.html | S10–S11 |
| 47–56 | Карта ОС, 85% мира, WSL одним слайдом | S12–S13 |
| 56–60 | Итог, шпаргалка и домашка в чат | S14 |

Пинги в чат (вставить в соответствующие блоки): «сколько ГГц у твоего компьютера?», «у кого сколько RAM?», «кто видел чёрный экран BIOS?», «какая ОС на твоём телефоне?». Теория кусками ≤2 минут. Байки для ведущего: майнинг и VRAM (блок 15–22); IBM PC XT — процессор 16-разрядный, шина 8 бит, скорость вдвое ниже (блок 22–30, одной строкой). Авторские метафоры обязательны и дословны: такты-«часики», адреса «как дома на улице, только с нуля», «0/1 = есть напряжение / нет напряжения». Для сверки формулировок можно заглянуть в `recordings/transcripts/GMT20260812-160331_Recording.txt` (локальный, вне гита).

- [ ] **Step 3: Написать glossary.md**

Стиль — `lessons/lesson-02d-js-loops/glossary.md` (термин → 1–2 предложения простыми словами, без вложенных терминов). Термины: процессор (CPU), частота, регистр, оперативная память (RAM/ОЗУ), постоянная память (ROM/ПЗУ), SSD/жёсткий диск, VRAM, шина, разрядность, бит, ввод-вывод, POST, BIOS, UEFI, загрузчик, операционная система, WSL.

- [ ] **Step 4: Написать live-code.md («живая схема»)**

Это НЕ живой кодинг — это режиссура показа. 8 шагов, каждый шаг:
`### Шаг N — название` → какой слайд открыть (S№) → что сказать (2–4 реплики) → пинг/вопрос детям → типовая ошибка восприятия и как её снять.
Шаги: 1) пустая материнка (S3), 2) CPU и часики (S4), 3) нули-единицы (S5), 4) RAM-полка (S6–S7), 5) шина (S8), 6) полная схема с пользователем (S9), 7) включение: POST и эстафета (S10–S11, здесь переключиться на демку `demos/boot.html`), 8) карта ОС и итог (S12–S14).
В начале файла — врезка «Отступление анатомии: в cs-уроках live-code = живая схема, код не пишем» (2 строки).

- [ ] **Step 5: Проверка**

```bash
ls lessons/lesson-cs-01-computer/
grep -c '^### Шаг' lessons/lesson-cs-01-computer/live-code.md   # ожидаем: 8
grep -o 'S1[0-4]\|S[1-9]' lessons/lesson-cs-01-computer/live-code.md | sort -u | wc -l  # ожидаем: 14
grep -iL 'дружина' lessons/lesson-cs-01-computer/*.md            # все 4 файла в выводе (слова нет нигде)
```

- [ ] **Step 6: Commit**

```bash
git add lessons/lesson-cs-01-computer/
git commit -m "Add lesson cs-01 markdown core: README, scenario, glossary, live-board flow"
```

---

### Task 2: cs-01 — slides.html (14 слайдов)

**Files:**
- Create: `lessons/lesson-cs-01-computer/slides.html`

**Interfaces:**
- Consumes: список S1–S14 из Task 1 (канонический, менять нельзя); механику deck из `lessons/lesson-01-html-css/slides.html`.
- Produces: слайды `#s1`…`#s14`, на которые ссылается конспект ведущего (Task 4).

- [ ] **Step 1: Скопировать механику эталона**

Взять из `lessons/lesson-01-html-css/slides.html`: базовый CSS (`.slides`, `.slide`, `.slide.active`), навигацию (`.nav` с prev/next и индикатором `N / 14`), обработчик клавиатуры, `.keyhint`. Шрифты — тот же стек (Space Grotesk + JetBrains Mono). `<title>Слайды · Компьютер изнутри (cs-01)</title>`.

- [ ] **Step 2: Сверстать S1–S14 по канону из Task 1**

Требования к вёрстке:
- Сквозная схема компьютера (S3, S4, S6, S8, S9, S14) — один inline-SVG, повторяемый от слайда к слайду с добавлением элементов; уже показанные элементы приглушены (`opacity .45`), новый — в акцентном цвете `#ffd60a`. Блоки схемы: материнка (рамка `#16213e`), CPU (`#0f3460` + жёлтая обводка при появлении), RAM-полка из 8 ячеек с адресами 0–7, SSD, шина (64 подписью, рисуем 8 линий + подпись «…×64»), блок I/O, клавиатура/монитор/фигурка пользователя.
- S5: два больших «провода» — с напряжением (жёлтая заливка, «1») и без («0»).
- S7: таблица-сравнение на двух карточках (стиль `.point` из эталона s2).
- S10: чек-лист POST с галочками `#00e676`: «CPU ✓ RAM ✓ Диск ✓».
- S11: горизонтальная цепочка из 4 стрелок-плашек.
- S12: SVG-дерево: корни MS-DOS и Unix, ветви Windows / Linux→Android / macOS+iOS.
- S13: SVG-«пирог» (два сектора: ~85% `#00ffc8` «Unix/Linux повсюду», остальное `#ffd60a` Windows + прочие) + плашка «даже Windows встроил себе Linux (WSL)».
- Текст на слайде — минимум: заголовок + 1–2 строки; подробности живут в scenario.md.

- [ ] **Step 3: Проверка**

```bash
grep -c 'class="slide' lessons/lesson-cs-01-computer/slides.html   # ожидаем: 14
grep -c '<svg' lessons/lesson-cs-01-computer/slides.html            # ожидаем: >= 6
grep -n '/ 14' lessons/lesson-cs-01-computer/slides.html            # индикатор навигации
python3 - lessons/lesson-cs-01-computer/slides.html <<'EOF'
import re, sys
html = open(sys.argv[1]).read()
js = '\n'.join(re.findall(r'<script>(.*?)</script>', html, re.S))
open('_check.js', 'w').write(js)
EOF
node --check _check.js && rm _check.js
```

- [ ] **Step 4: Commit**

```bash
git add lessons/lesson-cs-01-computer/slides.html
git commit -m "Add lesson cs-01 slides: 14-slide layered computer diagram deck"
```

---

### Task 3: cs-01 — демка boot.html (симулятор включения)

**Files:**
- Create: `lessons/lesson-cs-01-computer/demos/boot.html`

**Interfaces:**
- Consumes: тёмную палитру бренда; терминологию слайдов S10–S11 (POST, BIOS/UEFI, загрузочная запись, загрузчик, ОС — ровно эти названия).
- Produces: страницу, на которую ссылаются сценарий (Task 1), конспект (Task 4) и лендинг (Task 9) по пути `lessons/lesson-cs-01-computer/demos/boot.html`.

- [ ] **Step 1: Написать демку**

Одна страница, тёмный фон `#0a0a14`, карточка-«системник» по центру. Сверху тумблер-чекбокс «вытащить планку RAM» и большая кнопка Power (`#00e676`). Ниже — лента шагов. Логика:

```js
const steps = [
  { id: 'power',  title: 'Кнопка Power',        text: 'Питание пошло на материнскую плату.' },
  { id: 'post',   title: 'POST — самопроверка',  text: 'Процессор на месте? Память отвечает? Диск виден?' },
  { id: 'bios',   title: 'BIOS / UEFI',          text: 'Маленькая программа из ПЗУ: читает настройки, ищет загрузочный диск.' },
  { id: 'mbr',    title: 'Загрузочная запись',   text: 'Первый кусочек диска: «вот как запускать систему».' },
  { id: 'loader', title: 'Загрузчик ОС',         text: 'Переносит операционную систему с диска в оперативную память.' },
  { id: 'os',     title: 'Операционная система', text: 'Рабочий стол загружен. Компьютер готов!' },
];
let current = -1;
function powerOn() { current = -1; clearList(); nextStep(); }
function nextStep() {
  current++;
  const step = steps[current];
  if (step.id === 'post' && ramOut.checked) {
    addRow(step.title, 'БИП-БИП! Память не найдена — загрузка остановлена.', 'fail');
    return; // дальше кнопка «Дальше» неактивна до выключения тумблера
  }
  addRow(step.title, step.text, 'ok');
  if (current === steps.length - 1) markDone();
}
```

Кнопка «Дальше →» вызывает `nextStep()`; шаг POST при исправной памяти показывает три галочки «CPU ✓ RAM ✓ Диск ✓» (цвет `#00e676`), ошибка — красным `#ff5722`. Финал: плашка «рабочего стола» с градиентом и подписью «Всё это заняло у настоящего компьютера пару секунд». Комментариев в коде — минимум.

- [ ] **Step 2: Проверка**

```bash
python3 - lessons/lesson-cs-01-computer/demos/boot.html <<'EOF'
import re, sys
html = open(sys.argv[1]).read()
js = '\n'.join(re.findall(r'<script>(.*?)</script>', html, re.S))
open('_check.js', 'w').write(js)
EOF
node --check _check.js && rm _check.js
grep -c "steps" lessons/lesson-cs-01-computer/demos/boot.html   # > 0
```

- [ ] **Step 3: Commit**

```bash
git add lessons/lesson-cs-01-computer/demos/
git commit -m "Add lesson cs-01 boot demo: interactive power-on simulator with POST failure mode"
```

---

### Task 4: cs-01 — cheatsheet.html, homework.html, index-final.html

**Files:**
- Create: `lessons/lesson-cs-01-computer/cheatsheet.html`
- Create: `lessons/lesson-cs-01-computer/homework.html`
- Create: `lessons/lesson-cs-01-computer/index-final.html`

**Interfaces:**
- Consumes: светлый печатный стиль из `lessons/lesson-02f-js-functions/cheatsheet.html`; тёмный конспект из `lessons/lesson-02f-js-functions/index-final.html`; слайды S1–S14 и демку boot.html.
- Produces: три страницы по путям, на которые ссылается лендинг (Task 9).

- [ ] **Step 1: cheatsheet.html — «Карта компьютера»**

Светлая печатная палитра эталона. Секции:
1. «Карта компьютера» — упрощённый SVG со схемой из слайдов (материнка, CPU, RAM, SSD, шина, I/O) с подписями.
2. «Путь включения» — цепочка Power → POST → BIOS/UEFI → загрузочная запись → загрузчик → ОС, каждый шаг одной строкой.
3. «Мини-словарик» — 8 самых важных терминов из glossary (CPU, частота, RAM, SSD, шина, бит, BIOS/UEFI, ОС) в формате «термин — одна строка».
4. «Кто есть кто среди ОС» — 4 строки: Windows, macOS, Linux, Android («это тоже Linux»).

- [ ] **Step 2: homework.html — «Паспорт моего компьютера»**

Тот же светлый стиль. Задание без кода:
1. Анкета-таблица с пустыми полями для заполнения (можно распечатать или переписать в тетрадь): процессор, частота (ГГц), количество ядер, RAM (ГБ), диск (ГБ, SSD или HDD), операционная система, ОС телефона.
2. Инструкции, где смотреть: Windows — «Параметры → Система → О системе»; Mac — « → Об этом Mac»; телефон — «Настройки → О телефоне».
3. Бонус со звёздочкой: «найди на своём компьютере, как зайти в BIOS/UEFI — но НЕ меняй там ничего, просто посмотри и выйди».
4. Финальная строка: «принеси заполненный паспорт на следующее занятие — сравним, у кого какая машина».

- [ ] **Step 3: index-final.html — резервный конспект ведущего**

Тёмный стиль эталона 02f (это конспект, не страница с интерактивом). Комментарий в шапке: «РЕЗЕРВНЫЙ КОНСПЕКТ урока cs-01. Если слайды не открылись — ведёшь по этому файлу». 8 блоков-шагов = 8 шагов live-code.md, в каждом: номер слайда (S№), ключевые реплики, пинг. Вместо консольных сниппетов — текстовые плашки со схемой словами («CPU ← шина ×64 → RAM»).

- [ ] **Step 4: Проверка**

```bash
grep -c '<svg' lessons/lesson-cs-01-computer/cheatsheet.html      # >= 1
grep -n 'faf7f2' lessons/lesson-cs-01-computer/cheatsheet.html lessons/lesson-cs-01-computer/homework.html  # светлая палитра в обоих
grep -in 'дружина\|СССР' lessons/lesson-cs-01-computer/*.html      # пусто
```

- [ ] **Step 5: Commit**

```bash
git add lessons/lesson-cs-01-computer/
git commit -m "Add lesson cs-01 cheatsheet, homework (computer passport), presenter fallback notes"
```

---

### Task 5: cs-02 — Markdown-ядро (README, scenario, glossary, live-code)

**Files:**
- Create: `lessons/lesson-cs-02-layers/README.md`
- Create: `lessons/lesson-cs-02-layers/scenario.md`
- Create: `lessons/lesson-cs-02-layers/glossary.md`
- Create: `lessons/lesson-cs-02-layers/live-code.md`

**Interfaces:**
- Consumes: спеку, эталоны `lessons/lesson-02d-js-loops/*.md`, README cs-01 (Task 1) для перекрёстных ссылок.
- Produces: нумерацию слайдов S1–S13 (список ниже) для Task 6 и Task 8.

**Канонический список слайдов cs-02 (S1–S13):**

| № | Слайд | Содержание |
|---|---|---|
| S1 | Титул | «Слои: от железа до твоей программы», kicker `// блок «компьютер изнутри» · урок 2`, чипы: «🧱 слои», «💡 биты», «🔢 16-ричная» |
| S2 | Эстафета-повтор | Цепочка Power → POST → BIOS/UEFI → загрузчик → ОС из cs-01, приглушённая — «вспоминаем» |
| S3 | Пирамида слоёв | 4 этажа снизу вверх: железо → BIOS/UEFI → ОС → приложение. Подписи «кто с кем говорит» |
| S4 | Программа vs приложение | Программа — код, который пишешь; приложение — готовая штука, которую запускает пользователь |
| S5 | Перфокарта | SVG-перфокарта: «есть дырочка = 1, нет дырочки = 0». Так писали первые программы |
| S6 | Биты-лампочки | 8 SVG-лампочек (горит/не горит) = байт. Под ними значение: 00101010 |
| S7 | Двоичный счёт | 0, 1, 10, 11, 100… Перенос разряда «точно как в десятичной — просто цифры кончаются раньше» |
| S8 | A–F | В 16-ричной 16 цифр: 0–9, A, B, C, D, E, F. Таблица 0–15. Правило: F + 1 = 10, а 16₁₀ = 10₁₆ |
| S9 | Hex-цвета | `#ffd60a` = ff·d6·0a = 255 красного, 214 зелёного, 10 синего. «Вы уже писали 16-ричные числа — в CSS!» |
| S10 | Лестница языков | Ступени: машинный код (0/1) → ассемблер → C → JS/Python. Чем выше — тем ближе к человеку, чем ниже — к железу |
| S11 | Hello World шок | Слева ассемблер (~12 строк, код ниже в Task 6), справа `console.log("Привет!")`. Делают одно и то же |
| S12 | Драйвер | Переводчик между ОС и устройством: поставил новую видеокарту → ставишь драйвер. Пишут на ассемблере и C |
| S13 | Итог | Пирамида + «языков больше двухсот — в следующий раз возьмём 5–7 главных» + «шпаргалка и домашка в чате» |

- [ ] **Step 1: README.md**

По схеме Task 1 Step 1. Шапка: тема «Слои компьютера и язык машины: биты, 16-ричная система, лестница языков», 60 мин, блок cs урок 2.
«Что ребёнок умеет к концу»: рисует пирамиду железо → BIOS/UEFI → ОС → приложение; отличает программу от приложения; объясняет бит и байт «лампочками»; считает до небольших чисел в двоичной; читает 16-ричное число и знает цифры A–F; раскладывает hex-цвет из CSS на три числа; понимает, зачем ассемблер и драйверы, и почему на них пишут мало кто.
«Связь»: назад — cs-01, вперёд — cs-03 «Языки программирования» (анонс), потом возвращение в JS-линейку.

- [ ] **Step 2: scenario.md**

Стиль 02d. Тайминг из спеки:

| Мин | Блок | Слайды |
|---|---|---|
| 0–5 | Повтор cs-01: эстафета включения, опрос | S1–S2 |
| 5–15 | Пирамида слоёв; ОС «берёт нули-единицы на себя»; почему ОС не встанет на любое железо; программа vs приложение | S3–S4 |
| 15–20 | Машина говорит только 0/1; перфокарты | S5 |
| 20–32 | Двоичная на демке-лампочках: бит, байт, счёт до 255, перенос разряда | S6–S7 + демка bits.html |
| 32–42 | 16-ричная: зачем, A–F, практика с hex-цветом из их CSS | S8–S9 + вкладка «собери цвет» |
| 42–52 | Лестница языков, Hello World шок, драйверы | S10–S12 |
| 52–58 | Мост к cs-03 | S13 |
| 58–60 | Шпаргалка + домашка в чат | S13 |

Пинги: «что на дне пирамиды?», «сколько влезет в 8 лампочек?», «что больше — FF или 100?», «какого цвета `#ff0000`?». Байка для ведущего (блок 20–32): «в 1950-е в московском университете построили троичный компьютер — три состояния вместо двух; оказалось, людям неудобно, и весь мир остался на двоичной» — формулировка ровно такая, без иной атрибутики. Сверка формулировок: `recordings/transcripts/GMT20260816-160329_Recording.txt` (локальный; середина файла — мусор распознавания, пропускать).

- [ ] **Step 3: glossary.md**

Термины: слой (уровень), приложение, программа, бит, байт, двоичная система, десятичная система, шестнадцатеричная система, перфокарта, машинный код, ассемблер, драйвер.

- [ ] **Step 4: live-code.md («живая схема»)**

8 шагов по механике Task 1 Step 4: 1) эстафета-повтор (S2), 2) пирамида (S3–S4), 3) перфокарта и 0/1 (S5), 4) лампочки: бит и байт (S6, переключиться на демку bits.html), 5) двоичный счёт на демке (S7), 6) A–F и 16-ричная (S8), 7) hex-цвет: вкладка «собери цвет» (S9), 8) лестница языков + Hello World + драйвер + мост (S10–S13). Та же врезка про отступление анатомии.

- [ ] **Step 5: Проверка**

```bash
grep -c '^### Шаг' lessons/lesson-cs-02-layers/live-code.md   # 8
grep -in 'дружина\|СССР\|советск' lessons/lesson-cs-02-layers/*.md  # пусто
```

- [ ] **Step 6: Commit**

```bash
git add lessons/lesson-cs-02-layers/
git commit -m "Add lesson cs-02 markdown core: layers pyramid, number systems, language ladder"
```

---

### Task 6: cs-02 — slides.html (13 слайдов)

**Files:**
- Create: `lessons/lesson-cs-02-layers/slides.html`

**Interfaces:**
- Consumes: список S1–S13 из Task 5; механику deck эталона (как Task 2).
- Produces: слайды `#s1`…`#s13` для конспекта Task 8.

- [ ] **Step 1: Сверстать deck по канону Task 5**

Механика и шрифты — как в Task 2. Особые требования:
- S3 (пирамида): 4 горизонтальных этажа-плашки; нижний `#0f3460` «железо», выше `#16213e` «BIOS/UEFI», выше `#1a1a2e` «операционная система», верхний с жёлтой обводкой «твоё приложение».
- S6: 8 SVG-«лампочек» (круги; горящая — заливка `#ffd60a` + свечение, погашенная — контур), под ними подпись `00101010 = 42`.
- S8: таблица 0–15 в три колонки (десятичная / двоичная / 16-ричная), моноширинный шрифт.
- S9: три плашки цвета фона `#ffd60a`, разбор `ff · d6 · 0a` → 255/214/10; рядом брендовые чипы-цвета `#00ffc8`, `#ff0096` для самопроверки.
- S11 (Hello World шок): слева блок кода ассемблера (моноширинный, мелкий), справа одна крупная строка JS. Код ассемблера ровно этот:

```asm
section .data
  msg db "Привет!", 10
  len equ $ - msg
section .text
  global _start
_start:
  mov rax, 1        ; системный вызов write
  mov rdi, 1        ; куда: на экран
  mov rsi, msg      ; что: адрес текста
  mov rdx, len      ; сколько байт
  syscall
  mov rax, 60       ; системный вызов exit
  xor rdi, rdi
  syscall
```

справа: `console.log("Привет!")` и подпись «обе программы делают одно и то же».
- S10 (лестница): 4 ступени слева-направо вверх, подписи «ближе к железу» / «ближе к человеку» по краям.

- [ ] **Step 2: Проверка**

```bash
grep -c 'class="slide' lessons/lesson-cs-02-layers/slides.html   # 13
grep -n '/ 13' lessons/lesson-cs-02-layers/slides.html
grep -c 'syscall' lessons/lesson-cs-02-layers/slides.html         # 2
python3 - lessons/lesson-cs-02-layers/slides.html <<'EOF'
import re, sys
html = open(sys.argv[1]).read()
js = '\n'.join(re.findall(r'<script>(.*?)</script>', html, re.S))
open('_check.js', 'w').write(js)
EOF
node --check _check.js && rm _check.js
```

- [ ] **Step 3: Commit**

```bash
git add lessons/lesson-cs-02-layers/slides.html
git commit -m "Add lesson cs-02 slides: layers pyramid, bits, hex colors, asm vs JS hello world"
```

---

### Task 7: cs-02 — демка bits.html (биты-лампочки + собери цвет)

**Files:**
- Create: `lessons/lesson-cs-02-layers/demos/bits.html`

**Interfaces:**
- Consumes: тёмную палитру бренда, терминологию S6–S9 (бит, байт, 16-ричная).
- Produces: страницу по пути `lessons/lesson-cs-02-layers/demos/bits.html` для сценария, конспекта и лендинга.

- [ ] **Step 1: Написать демку**

Одна страница, две вкладки (кнопки-табы вверху): «Лампочки» и «Собери цвет».

Вкладка «Лампочки»: 8 кликабельных кружков-битов (клик переключает 0/1; горящая — `#ffd60a` со свечением). Под ними три крупных значения: двоичное (8 знаков), десятичное, 16-ричное. Логика:

```js
const bits = [0, 0, 0, 0, 0, 0, 0, 0];
function toggle(i) { bits[i] = 1 - bits[i]; render(); }
function render() {
  const val = bits.reduce((acc, b) => acc * 2 + b, 0);
  binEl.textContent = bits.join('');
  decEl.textContent = val;
  hexEl.textContent = val.toString(16).toUpperCase().padStart(2, '0');
}
```

Вкладка «Собери цвет»: три ползунка R/G/B (0–255), рядом с каждым его hex-пара; большой прямоугольник-образец итогового цвета и крупная строка `#RRGGBB`. Кнопки-пресеты брендовых цветов: `#ffd60a`, `#00ffc8`, `#ff0096`, `#ff5722` — клик выставляет ползунки. Логика:

```js
function toHexPair(v) { return v.toString(16).padStart(2, '0'); }
function renderColor() {
  const hex = '#' + [r.value, g.value, b.value].map(v => toHexPair(+v)).join('');
  swatch.style.background = hex;
  hexLabel.textContent = hex;
}
```

- [ ] **Step 2: Проверка**

```bash
python3 - lessons/lesson-cs-02-layers/demos/bits.html <<'EOF'
import re, sys
html = open(sys.argv[1]).read()
js = '\n'.join(re.findall(r'<script>(.*?)</script>', html, re.S))
open('_check.js', 'w').write(js)
EOF
node --check _check.js && rm _check.js
node -e "const b=[0,0,1,0,1,0,1,0]; const v=b.reduce((a,x)=>a*2+x,0); console.assert(v===42 && v.toString(16)==='2a', 'FAIL'); console.log('bit math OK')"
```

- [ ] **Step 3: Commit**

```bash
git add lessons/lesson-cs-02-layers/demos/
git commit -m "Add lesson cs-02 bits demo: 8-bit lamp toggles and hex color builder"
```

---

### Task 8: cs-02 — cheatsheet.html, homework.html, index-final.html

**Files:**
- Create: `lessons/lesson-cs-02-layers/cheatsheet.html`
- Create: `lessons/lesson-cs-02-layers/homework.html`
- Create: `lessons/lesson-cs-02-layers/index-final.html`

**Interfaces:**
- Consumes: эталоны как в Task 4; слайды S1–S13 и демку bits.html.
- Produces: три страницы для лендинга (Task 9).

- [ ] **Step 1: cheatsheet.html — «Слои и язык машины»**

Светлый печатный стиль. Секции:
1. «Пирамида» — SVG 4 этажа с подписью каждого одной строкой.
2. «Таблица счёта» — 0–15 в трёх системах (десятичная / двоичная / 16-ричная), моноширинно.
3. «Как прочитать hex-цвет» — разбор `#ffd60a` → ff=255 красного, d6=214 зелёного, 0a=10 синего.
4. «Лестница языков» — машинный код → ассемблер → C → JS/Python, по строке на ступень.
5. «Запомни» — 3 факта: бит — лампочка; байт — 8 лампочек (до 255); F+1 = 10.

- [ ] **Step 2: homework.html — «Задания на листочке»**

Светлый стиль. Без компьютера, проверка — в демке bits.html (дать ссылку):
1. Переведи в десятичную: `00000011`, `00001010`, `00100000` (ответы не печатать; строка «проверь себя в демке-лампочках»).
2. Запиши свой возраст лампочками (двоичной).
3. Угадай, какой это цвет, потом проверь во вкладке «Собери цвет»: `#ff0000`, `#00ff00`, `#ffffff`.
4. Бонус со звёздочкой: что больше — `FF` или `100`? (в 16-ричной!)

- [ ] **Step 3: index-final.html — резервный конспект ведущего**

Тёмный конспект по образцу Task 4 Step 3: 8 блоков = 8 шагов live-code.md cs-02, с номерами слайдов, репликами и пингами. Таблицу 0–15 включить прямо в конспект (если слайды упали — таблица под рукой).

- [ ] **Step 4: Проверка**

```bash
grep -c '<svg' lessons/lesson-cs-02-layers/cheatsheet.html          # >= 1
grep -n 'ffd60a' lessons/lesson-cs-02-layers/cheatsheet.html        # разбор цвета на месте
grep -in 'дружина\|СССР\|советск' lessons/lesson-cs-02-layers/*.html # пусто
```

- [ ] **Step 5: Commit**

```bash
git add lessons/lesson-cs-02-layers/
git commit -m "Add lesson cs-02 cheatsheet, paper homework, presenter fallback notes"
```

---

### Task 9: Обвязка — index.html, CLAUDE.md, postmortem

**Files:**
- Modify: `index.html` (вставка между `</section>` секции `#js`, строка ~1029, и `<!-- DEMOS -->`)
- Modify: `CLAUDE.md` (раздел «Анатомия урока»)
- Create: `meta/lesson-cs-postmortem.md`

**Interfaces:**
- Consumes: все пути уроков из Task 1–8; классы `.js-lessons`/`.js-lesson`/`.jn`/`.js-links`/`.chip`/`.badge` — уже есть в CSS лендинга, новых стилей не добавлять.
- Produces: публичные ссылки на все материалы блока.

- [ ] **Step 1: Вставить секцию в index.html**

Ровно между закрывающим `</section>` блока `#js` и комментарием `<!-- DEMOS -->`. Вокруг ничего не менять (в файле есть незакоммиченные правки — они не наши). Markup:

```html
<!-- CS BLOCK -->
<section id="cs">
  <div class="container">
    <div class="section-label">// блок «компьютер изнутри»</div>
    <h2>Что <em>под капотом</em></h2>
    <p class="section-lead">
      Отступление от кода: как устроен компьютер и почему он понимает только нули и единицы. Можно писать код и без этого — но сильным программистом так не стать.
    </p>
    <div class="js-lessons">

      <div class="js-lesson">
        <div class="jn">cs·1<small>железо</small></div>
        <div>
          <h4>Компьютер изнутри</h4>
          <p>Материнка, CPU с «часиками», RAM и SSD, шина на 64 «проводочка» — и что происходит за пару секунд между кнопкой Power и рабочим столом.</p>
          <div class="js-links">
            <a href="lessons/lesson-cs-01-computer/cheatsheet.html">📖 Шпаргалка</a>
            <a href="lessons/lesson-cs-01-computer/homework.html">📝 Домашка</a>
            <a href="lessons/lesson-cs-01-computer/slides.html">🎬 Слайды</a>
            <span class="sep"></span>
            <span class="grp">демка</span>
            <a class="chip g" href="lessons/lesson-cs-01-computer/demos/boot.html" title="симулятор включения">⚙️</a>
            <span class="sep"></span>
            <a class="repo" href="https://github.com/DmitrTRC/Junior_IT/tree/main/lessons/lesson-cs-01-computer">материалы →</a>
          </div>
        </div>
      </div>

      <div class="js-lesson">
        <div class="jn">cs·2<small>слои</small></div>
        <div>
          <h4>Слои: от железа до твоей программы</h4>
          <p>Пирамида «железо → BIOS → ОС → приложение», биты-лампочки, счёт до 255 двумя цифрами — и почему <code>#ffd60a</code> из вашего CSS это три числа.</p>
          <div class="js-links">
            <a href="lessons/lesson-cs-02-layers/cheatsheet.html">📖 Шпаргалка</a>
            <a href="lessons/lesson-cs-02-layers/homework.html">📝 Домашка</a>
            <a href="lessons/lesson-cs-02-layers/slides.html">🎬 Слайды</a>
            <span class="sep"></span>
            <span class="grp">демка</span>
            <a class="chip g" href="lessons/lesson-cs-02-layers/demos/bits.html" title="биты-лампочки">💡</a>
            <span class="sep"></span>
            <a class="repo" href="https://github.com/DmitrTRC/Junior_IT/tree/main/lessons/lesson-cs-02-layers">материалы →</a>
          </div>
        </div>
      </div>

      <div class="js-lesson">
        <div class="jn">cs·3<small>языки</small></div>
        <div>
          <h4>Языки программирования<span class="badge">● скоро</span></h4>
          <p>Их больше двухсот. Возьмём 5–7 главных, напишем один и тот же Hello World на каждом и поймём, чем они отличаются на самом деле.</p>
        </div>
      </div>

    </div>
  </div>
</section>
```

- [ ] **Step 2: Дополнить CLAUDE.md**

В конец раздела «🧩 Анатомия урока» добавить подраздел:

```markdown
### Блок cs («Компьютер изнутри»)

Теоретические уроки об устройстве компьютера: `lessons/lesson-cs-NN-slug/`,
нумерация своя (cs-01, cs-02, …). Два осознанных отступления от анатомии:
`live-code.md` — «живая схема» (режиссура сборки схемы по слайдам, кода нет),
и одна интерактивная демка на урок вместо трёх эстетик. Слайдов больше
обычного (12–14): сквозная схема собирается послойно. Это норма блока,
не нарушение бренда.
```

- [ ] **Step 3: Написать meta/lesson-cs-postmortem.md**

Содержание (сжато, без воды):
- Контекст: два спонтанных занятия вне плана (12.08, 16.08), один на один, Zoom; записи расшифрованы локально, материалы восстановлены в блок cs.
- Что не сработало: Zoom-whiteboard съедал минуты урока (поиск инструментов, шрифты, «сейчас-сейчас») — на вебинаре недопустимо; вывод: любая схема заранее в slides.html. 36 минут — реальный потолок устной теории один на один; вебинар-версии добиты до 60 минут интерактивом (демки, пинги).
- Что сработало: метафоры «часики», «дома на улице», «есть напряжение/нет» — ученица следила и отвечала; отступление в «компьютер изнутри» оправдано — фиксируем как постоянный блок cs.
- Обещания: ученице обещаны наглядные слайды по шагам (закрыто этим блоком); анонсирован cs-03 «Языки» с парадом Hello World (5–7 языков) — в записи обещано сравнение объёма работы программиста и цены ошибки.
- Открытый вопрос: куда блок cs встаёт в групповом потоке — рабочая гипотеза «после 2.7, перед разминкой 2.8», решить при планировании семестра.

- [ ] **Step 4: Проверка**

```bash
grep -c 'lesson-cs-0' index.html        # ожидаем: 10 строк со ссылками (по 5 на карточку)
grep -n 'id="cs"' index.html            # секция на месте
grep -n 'Блок cs' CLAUDE.md
```

- [ ] **Step 5: Commit**

```bash
git add index.html CLAUDE.md meta/lesson-cs-postmortem.md
git commit -m "Wire CS block into landing page, document cs anatomy in CLAUDE.md, add postmortem"
```

---

### Task 10: Бренд-ревью и финальный предпросмотр

**Files:**
- Modify: любые файлы блока cs по итогам ревью (точечные правки).

**Interfaces:**
- Consumes: все материалы Task 1–9.
- Produces: подтверждённый к деплою блок (сам деплой — вне плана, по команде `/deploy`).

- [ ] **Step 1: Прогнать brand-guardian**

Запустить сабагента brand-guardian (Task tool) по путям `lessons/lesson-cs-01-computer/`, `lessons/lesson-cs-02-layers/`, диффу `index.html` и `meta/lesson-cs-postmortem.md`. В промпте явно указать: «отступления блока cs (одна демка вместо трёх эстетик, live-code = живая схема) — норма по CLAUDE.md, не нарушение».

- [ ] **Step 2: Исправить находки**

Точечно поправить всё подтверждённое ревью (цвета вне палитры, запрещённая лексика, хрупкая вёрстка). Спорное — вынести Димасу списком, не править молча.

- [ ] **Step 3: Предпросмотр с Димасом (checkpoint)**

Показать Димасу: `python3 -m http.server 8000` из корня (запускает он сам или отдельная панель — не агент) → проверить глазами слайды обоих уроков (листание, все 14 и 13), обе демки (включая «вытащить RAM» и пресеты цветов), шпаргалки/домашки, секцию на лендинге. Это блокирующий чекпойнт перед финальным коммитом правок.

- [ ] **Step 4: Финальный commit**

```bash
git add -A lessons/lesson-cs-01-computer lessons/lesson-cs-02-layers
git commit -m "Polish CS block after brand review and live preview"
```

(если правок не было — коммит пропустить)
