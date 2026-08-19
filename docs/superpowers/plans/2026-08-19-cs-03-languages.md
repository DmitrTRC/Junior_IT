# Урок cs-03 «Языки программирования» — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Полный урок `lessons/lesson-cs-03-languages/` по анатомии cs-блока: среда исполнения, компилятор / интерпретатор / JIT на связке asm-C-C++-Python-JS, разница JS в браузере и в консоли, тренажёр на три вкладки + обвязка лендинга.

**Architecture:** Статические HTML/CSS/JS без сборки и фреймворков. Урок — папка с фиксированным набором файлов; слайды — самодостаточный deck по образцу `lesson-01`; тренажёр — одиночная HTML-страница с inline-JS и предзаписанными выводами (код не исполняется по-настоящему, кроме подсветки и подстановки ввода).

**Tech Stack:** vanilla HTML/CSS/JS, inline-SVG, Google Fonts (стек эталона), Markdown для сценариев.

**Spec:** `docs/superpowers/specs/2026-08-19-cs-03-languages-design.md`

## Global Constraints

- Язык материалов — русский, с детьми на «ты». Идентификаторы и код — английские.
- Палитра — только токены бренд-кита: `--bg #0a0a14`, `--card #1a1a2e`, `--card-2 #16213e`, `--deep #0f3460`, `--yellow #ffd60a`, `--orange #ff5722`, `--green #00e676`, `--cyan #00ffc8`, `--magenta #ff0096`, светлый фон печати `#faf7f2`.
- Консольные блоки и листинги кода — Dracula: `#8be9fd` (ключевые слова), `#f1fa8c` (строки), `#ffb86c` (числа), `#ff79c6` (логические), `#6272a4` (комментарии), `#7fd0ff` (вывод), фоны `#15151c` / `#0c0c11`.
- Шрифты: Space Grotesk 700 (заголовки), Manrope 400/500/600 (текст), JetBrains Mono 400/700 (код). Шрифтовый стек копировать из эталонных файлов, не менять.
- Графика — только inline-SVG в бренд-палитре. Никаких стоковых картинок и внешних генераторов.
- Никаких хрупких `position:absolute`-декораций; всё на flex/grid. Ничто не должно уезжать по горизонтали и переноситься на вторую строку там, где задумана одна.
- ⛔ Запреты проекта: никакой символики СССР и силовых ведомств, ни слова «дружина».
- Слова «DOM», «семантика», «парсинг», «валидация» в материалах не встречаются. Про браузерный JS говорим «дотягивается до страницы».
- Java, Go, Rust, C# — только упоминание одной строкой на слайде «языков больше двухсот». В глоссарий и тренажёр не идут.
- Эмодзи: в HTML-контенте можно (по образцу лендинга), в коммитах / идентификаторах / именах файлов — нет.
- Комментарии в коде — минимум, только неочевидное.
- Каждый коммит завершать трейлером:
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
- `git push` НЕ делать. Только коммиты.

**Эталоны стиля (читать перед соответствующей задачей):**

| Что делаем | Эталон |
|---|---|
| slides.html | `lessons/lesson-cs-02-layers/slides.html` (структура deck: `.slide`/`.active`, per-slide стили, nav prev/next + стрелки клавиатуры) |
| README.md, scenario.md, glossary.md, live-code.md | `lessons/lesson-cs-02-layers/*.md` |
| demos/languages.html | `lessons/lesson-cs-02-layers/demos/bits.html` (табы, тёмная карточная вёрстка, сетка без переносов) |
| cheatsheet.html, homework.html | `lessons/lesson-cs-02-layers/cheatsheet.html` (светлая печатная палитра) |
| index-final.html | `lessons/lesson-cs-02-layers/index-final.html` |
| Карточка урока на лендинге | блок «Компьютер изнутри» в `index.html` (карточки cs-01 и cs-02 + заглушка cs-03) |

---

## Канонический список слайдов cs-03 (S1–S13)

Используется во всех задачах урока. После Task 1 состав и порядок не меняются.

| № | Слайд | Содержание |
|---|---|---|
| S1 | Титул | «Языки программирования: кто переводит твой код», kicker `// блок «компьютер изнутри» · урок 3`, чипы: «⚙️ компилятор», «🐍 интерпретатор», «⚡ JIT» |
| S2 | Повтор cs-02 | Лестница: машинный код → ассемблер → C → Python/JS. «Языков больше двухсот — Java, Go, Rust, C#, и это только начало списка» |
| S3 | Код — просто текст | Файл `hello.py` в блокноте. Сам по себе он ничего не делает: это буквы. Процессор их не понимает |
| S4 | Среда исполнения | Рецепт и повар: рецепт — код, повар — среда исполнения. Без повара рецепт — бумажка |
| S5 | Три способа перевода | Общая схема-основа: `исходник → ??? → машинный код → CPU`. Три ветки заполняются на S6–S9 |
| S6 | Компилятор | C и C++: перевели один раз до запуска, получили готовый файл. Исходник больше не нужен. Поэтому игру качают гигабайтами, а не текстом программы |
| S7 | Ассемблер и линкер | Предельный случай: асм почти один-в-один в машинный код, линкер сшивает куски в один файл. Так пишут драйверы и ядра |
| S8 | Интерпретатор | Python: переводчик читает строку — выполняет, читает следующую. Каждый запуск заново. Нужен установленный Python |
| S9 | JIT | JS: движок сначала интерпретирует, а куски, которые выполняются часто, компилирует прямо на ходу. Браузер не может ждать компиляции — страница должна открыться сейчас |
| S10 | Таблица пяти языков | asm / C / C++ / Python / JS: кто переводит, что нужно установить, что на нём пишут |
| S11 | «Привет» впятером | Пять блоков кода рядом: 14 строк асма против одной строки Python. Результат одинаковый |
| S12 | JS: браузер vs консоль | Движок один, руки разные: `alert` и страница — только в браузере; файлы и `readline` — только в консоли; переменные, циклы, `console.log` — везде |
| S13 | Итог | Три способа перевода одной картинкой + «дальше возвращаемся в JS-линейку». Шпаргалка и домашка в чат |

---

## Канонический корпус кода тренажёра

Один источник правды для Task 2 (S11), Task 3 (демка) и Task 5 (шпаргалка).
Четыре задачи × пять языков. Листинги переносить символ в символ.

### Задача «hello» — Привет, мир!

**asm** (полный листинг):

```asm
section .data
  msg db "Привет, мир!", 10
  len equ $ - msg

section .text
  global _start
_start:
  mov rax, 1          ; системный вызов write
  mov rdi, 1          ; куда: на экран
  mov rsi, msg        ; что: адрес текста
  mov rdx, len        ; сколько байт
  syscall
  mov rax, 60         ; системный вызов exit
  xor rdi, rdi
  syscall
```

**C:**

```c
#include <stdio.h>

int main(void) {
  printf("Привет, мир!\n");
  return 0;
}
```

**C++:**

```cpp
#include <iostream>

int main() {
  std::cout << "Привет, мир!" << std::endl;
  return 0;
}
```

**Python:**

```python
print("Привет, мир!")
```

**JS:**

```js
console.log("Привет, мир!");
```

Вывод: `Привет, мир!`

### Задача «name» — спроси имя и поздоровайся

**asm** (обрезанный листинг, плашка: «и ещё около 20 строк: длину имени надо посчитать самому, лишний перевод строки — убрать вручную»):

```asm
section .data
  ask db "Как тебя зовут? "
  askLen equ $ - ask

section .bss
  name resb 64

section .text
  global _start
_start:
  mov rax, 1          ; спрашиваем
  mov rdi, 1
  mov rsi, ask
  mov rdx, askLen
  syscall

  mov rax, 0          ; читаем с клавиатуры
  mov rdi, 0
  mov rsi, name
  mov rdx, 64
  syscall
```

**C:**

```c
#include <stdio.h>

int main(void) {
  char name[64];
  printf("Как тебя зовут? ");
  scanf("%63s", name);
  printf("Привет, %s!\n", name);
  return 0;
}
```

**C++:**

```cpp
#include <iostream>
#include <string>

int main() {
  std::string name;
  std::cout << "Как тебя зовут? ";
  std::cin >> name;
  std::cout << "Привет, " << name << "!" << std::endl;
  return 0;
}
```

**Python:**

```python
name = input("Как тебя зовут? ")
print("Привет, " + name + "!")
```

**JS:**

```js
const name = prompt("Как тебя зовут?");
console.log("Привет, " + name + "!");
```

Вывод: `Как тебя зовут? <имя>` / `Привет, <имя>!`
Для JS в поле «чтобы запустить» отдельно: `браузер — в консоли Node prompt не существует`.

### Задача «sum» — сложи два числа

**asm** (обрезанный листинг, плашка: «и ещё около 40 строк: число с клавиатуры приходит текстом — символ "7" это байт 55 — его надо вручную превратить в число, а результат обратно в текст»):

```asm
section .data
  ask db "Первое число: "
  askLen equ $ - ask

section .bss
  buf resb 16

section .text
  global _start
_start:
  mov rax, 1
  mov rdi, 1
  mov rsi, ask
  mov rdx, askLen
  syscall

  mov rax, 0          ; придёт текст, а не число
  mov rdi, 0
  mov rsi, buf
  mov rdx, 16
  syscall
```

**C:**

```c
#include <stdio.h>

int main(void) {
  int a, b;
  printf("Два числа: ");
  scanf("%d %d", &a, &b);
  printf("%d + %d = %d\n", a, b, a + b);
  return 0;
}
```

**C++:**

```cpp
#include <iostream>

int main() {
  int a, b;
  std::cout << "Два числа: ";
  std::cin >> a >> b;
  std::cout << a << " + " << b << " = " << a + b << std::endl;
  return 0;
}
```

**Python:**

```python
a = int(input("Первое число: "))
b = int(input("Второе число: "))
print(a, "+", b, "=", a + b)
```

**JS:**

```js
const a = Number(prompt("Первое число:"));
const b = Number(prompt("Второе число:"));
console.log(a + " + " + b + " = " + (a + b));
```

Вывод: `Первое число: <a>` / `Второе число: <b>` / `<a> + <b> = <сумма>`

Реплика ведущего (в `scenario.md`): `int()` в Python и `Number()` в JS — это ровно то же самое превращение текста в число, просто за тебя его делает одна короткая команда, а на асме ты пишешь её сам.

### Задача «count» — посчитай до 5

**asm** (полный листинг):

```asm
section .bss
  digit resb 2

section .text
  global _start
_start:
  mov r12, 1
loop_start:
  mov rax, r12
  add rax, 48         ; цифра превращается в символ
  mov [digit], al
  mov byte [digit + 1], 10

  mov rax, 1
  mov rdi, 1
  mov rsi, digit
  mov rdx, 2
  syscall

  inc r12
  cmp r12, 6
  jl loop_start

  mov rax, 60
  xor rdi, rdi
  syscall
```

**C:**

```c
#include <stdio.h>

int main(void) {
  for (int i = 1; i <= 5; i++) {
    printf("%d\n", i);
  }
  return 0;
}
```

**C++:**

```cpp
#include <iostream>

int main() {
  for (int i = 1; i <= 5; i++) {
    std::cout << i << std::endl;
  }
  return 0;
}
```

**Python:**

```python
for i in range(1, 6):
    print(i)
```

**JS:**

```js
for (let i = 1; i <= 5; i++) {
  console.log(i);
}
```

Вывод: `1` `2` `3` `4` `5` (каждое с новой строки)

### Таблица языков (для метрики демки, S10 и шпаргалки)

| id | Подпись | Кто переводит | Чтобы запустить |
|---|---|---|---|
| `asm` | asm x86-64 | ассемблер + линкер | nasm и ld, Linux x86-64 |
| `c` | C | компилятор | gcc — один раз, дальше только готовый файл |
| `cpp` | C++ | компилятор | g++ — один раз, дальше только готовый файл |
| `py` | Python | интерпретатор | установленный Python |
| `js` | JavaScript | JIT | браузер или Node |

---

### Task 1: Markdown-ядро урока (README, scenario, glossary, live-code)

**Files:**
- Create: `lessons/lesson-cs-03-languages/README.md`
- Create: `lessons/lesson-cs-03-languages/scenario.md`
- Create: `lessons/lesson-cs-03-languages/glossary.md`
- Create: `lessons/lesson-cs-03-languages/live-code.md`

**Interfaces:**
- Consumes: спеку, канонический список слайдов S1–S13 и корпус кода выше, эталоны `lessons/lesson-cs-02-layers/*.md`.
- Produces: тексты, на которые ссылаются все следующие задачи; нумерацию слайдов, менять которую после этой задачи нельзя.

- [ ] **Step 1: README.md**

Структура как в cs-02: заголовок «Урок cs-03 — Языки программирования: кто переводит твой код», строки «Тема / Длительность 60 минут (потолок 75) / Возраст 11–14 / Место в курсе», раздел «Зачем этот урок», список «Что ребёнок умеет к концу урока»:

- объясняет, что код — просто текст, и ему нужна среда исполнения;
- различает компилятор, интерпретатор и JIT и говорит, кто из пяти языков где;
- называет, что нужно установить, чтобы запустить программу на C, на Python, на JS;
- понимает, что JS в браузере и JS в консоли — один язык в разных средах;
- читает простую программу на любом из пяти языков и видит, что задача одна.

Дальше — «Связь с соседними уроками» (назад cs-02, вперёд — возврат в JS-линейку), таблица файлов урока со статусами, «Что осталось перед уроком (вручную, за Димасом)», «Методическая заметка» про отступления анатомии cs-блока.

- [ ] **Step 2: scenario.md**

Тайминг по спеке восемью блоками (0–4, 4–12, 12–22, 22–30, 30–38, 38–48, 48–56, 56–60). На каждый блок: что говорим, какой слайд открыт, пинг в чат. Пинги: «на чём написана твоя любимая игра?», «почему игру качают гигабайтами, а не текстом программы?», «у кого установлен Python?», «сколько строк на асме против питона — угадай до того, как покажу», «что случится, если написать alert в консоли без браузера?». Реплики ведущего сверх слайдов: байткод Python (`.pyc` — «питон всё-таки немножко компилирует, но в свой внутренний код, не в машинный»); реплика про `int()`/`Number()` из корпуса кода. В конце — чек-лист готовности к уроку.

- [ ] **Step 3: glossary.md**

Термины простыми словами, по образцу cs-02: исходный код, среда исполнения (рантайм), компилятор, интерпретатор, JIT, линкер, машинный код, движок, Node.js, кроссплатформенность. На каждый — одно-два предложения и пример из урока.

- [ ] **Step 4: live-code.md**

Живая схема, 8 шагов режиссуры: 1) повтор лестницы (S2), 2) код это текст (S3–S4), 3) общая схема перевода (S5), 4) компилятор (S6–S7), 5) интерпретатор (S8), 6) JIT (S9), 7) тренажёр: задачник и конвейер (переключение на `demos/languages.html`), 8) JS браузер vs консоль (S12) и итог (S13). На каждый шаг: что появляется на экране, что сказать, пинг. Врезка про отступление анатомии — как в cs-02.

- [ ] **Step 5: Проверка**

```bash
ls lessons/lesson-cs-03-languages/
grep -riE "дружина|DOM|семантик|парсинг|валидац" lessons/lesson-cs-03-languages/ && echo "НАЙДЕНЫ ЗАПРЕЩЁННЫЕ СЛОВА" || echo "чисто"
grep -c "S1[0-3]\|S[1-9]" lessons/lesson-cs-03-languages/live-code.md
```

Ожидаемо: четыре файла на месте, запрещённых слов нет, ссылки на слайды в live-code есть.

- [ ] **Step 6: Commit**

```bash
git add lessons/lesson-cs-03-languages/
git commit -m "Add lesson cs-03 markdown core: readme, scenario, glossary, live schema"
```

---

### Task 2: slides.html (13 слайдов)

**Files:**
- Create: `lessons/lesson-cs-03-languages/slides.html`

**Interfaces:**
- Consumes: канонический список S1–S13, корпус кода (S11 берёт «hello» на пяти языках), таблицу языков (S10).
- Produces: deck, на который ссылаются `live-code.md`, `index-final.html` и карточка лендинга.

- [ ] **Step 1: Скопировать каркас deck из cs-02**

Структура, навигация и стили — как в `lessons/lesson-cs-02-layers/slides.html`: секции `.slide` с id `s1`…`s13`, класс `active` на текущем, кнопки prev/next, стрелки клавиатуры, счётчик слайдов. Контент заменить на cs-03.

- [ ] **Step 2: Слайды S1–S5**

S1 титул, S2 лестница из cs-02 (SVG-ступени, сверху подпись «языков больше двухсот: Java, Go, Rust, C# — и это только начало списка»), S3 «код — просто текст» (окно блокнота с `hello.py`, стрелка к процессору перечёркнута), S4 рецепт и повар (два SVG-блока), S5 схема-основа `исходник → ??? → машинный код → CPU` с пустым ромбом в середине.

- [ ] **Step 3: Слайды S6–S9 (три способа, послойно)**

Каждый слайд достраивает схему S5, ромб заполняется:

```
S6  исходник.c   → [компилятор] → готовый файл → CPU      подпись: перевод ДО запуска, один раз
S7  исходник.asm → [ассемблер] → [линкер] → файл → CPU    подпись: почти один-в-один
S8  исходник.py  → [интерпретатор строка за строкой] → CPU подпись: перевод ВО ВРЕМЯ, каждый запуск
S9  исходник.js  → [движок: интерпретатор + JIT] → CPU     подпись: и так, и так; горячий кусок компилируется на лету
```

Всё — inline-SVG в бренд-палитре, стрелки `--cyan`, блоки-переводчики `--yellow`.

- [ ] **Step 4: Слайды S10–S13**

S10 — таблица пяти языков (три колонки из раздела «Таблица языков»). S11 — пять блоков кода «hello» рядом, под каждым число строк, акцент на контрасте 14 против 1. S12 — две колонки «браузер» / «консоль (Node)» с тремя строками общего и по две строки уникального, внизу плашка «движок один — руки разные». S13 — итоговая схема трёх способов + анонс возврата в JS-линейку.

- [ ] **Step 5: Проверка**

```bash
grep -c 'class="slide' lessons/lesson-cs-03-languages/slides.html
grep -o 'id="s[0-9]*"' lessons/lesson-cs-03-languages/slides.html | tr '\n' ' '
grep -riE "дружина|DOM|семантик|парсинг" lessons/lesson-cs-03-languages/slides.html && echo "ЗАПРЕТ" || echo "чисто"
```

Ожидаемо: 13 секций, id от `s1` до `s13` по порядку, запрещённых слов нет.

- [ ] **Step 6: Commit**

```bash
git add lessons/lesson-cs-03-languages/slides.html
git commit -m "Add lesson cs-03 slides: runtime, compiler, interpreter, JIT, five languages"
```

---

### Task 3: demos/languages.html — корпус кода и вкладка «Одна задача — пять языков»

**Files:**
- Create: `lessons/lesson-cs-03-languages/demos/languages.html`

**Interfaces:**
- Consumes: корпус кода и таблицу языков из этого плана, вёрстку `demos/bits.html`.
- Produces: файл `demos/languages.html` с готовым каркасом табов и объектами `LANGS`, `TASKS`, `CODE`, функциями `highlight(code, langId)` и `renderTask()` — Task 4 дописывает в этот же файл вкладки 2 и 3.

- [ ] **Step 1: Каркас страницы и данные**

Шапка как в `bits.html` (kicker `// cs-03 · языки и переводчики`, заголовок «Одна задача — пять языков», подзаголовок). Три кнопки-таба: «Одна задача», «Как это запускается», «JS: консоль vs браузер»; вторая и третья панели пока пустые — их наполняет Task 4.

Данные (листинги переносить из корпуса кода символ в символ):

```js
const LANGS = [
  { id: 'asm', name: 'asm x86-64', how: 'ассемблер + линкер', need: 'nasm и ld, Linux x86-64' },
  { id: 'c',   name: 'C',          how: 'компилятор',         need: 'gcc — один раз, дальше только готовый файл' },
  { id: 'cpp', name: 'C++',        how: 'компилятор',         need: 'g++ — один раз, дальше только готовый файл' },
  { id: 'py',  name: 'Python',     how: 'интерпретатор',      need: 'установленный Python' },
  { id: 'js',  name: 'JavaScript', how: 'JIT',                need: 'браузер или Node' },
];

const TASKS = [
  { id: 'hello', title: 'Привет, мир!',      out: () => ['Привет, мир!'] },
  { id: 'name',  title: 'Спроси имя',        out: (s) => ['Как тебя зовут? ' + s.name, 'Привет, ' + s.name + '!'] },
  { id: 'sum',   title: 'Сложи два числа',   out: (s) => ['Первое число: ' + s.a, 'Второе число: ' + s.b, s.a + ' + ' + s.b + ' = ' + (s.a + s.b)] },
  { id: 'count', title: 'Посчитай до 5',     out: () => ['1', '2', '3', '4', '5'] },
];

const CODE = { hello: {}, name: {}, sum: {}, count: {} };   // ключи внутри — id языка: asm, c, cpp, py, js;
                                                            // значения — шаблонные строки с листингами из раздела
                                                            // «Канонический корпус кода тренажёра», символ в символ
const CUT = {                                               // плашки обрезки для асма
  name: 'и ещё около 20 строк: длину имени надо посчитать самому, лишний перевод строки — убрать вручную',
  sum:  'и ещё около 40 строк: число с клавиатуры приходит текстом — символ "7" это байт 55 — его надо вручную превратить в число, а результат обратно в текст',
};
const NEED_OVERRIDE = { 'name:js': 'браузер — в консоли Node prompt не существует' };
```

- [ ] **Step 2: Подсветка кода**

Одна функция на все языки, один проход — строки выигрывают у ключевых слов:

```js
const KEYWORDS = {
  asm: ['section', 'global', 'db', 'equ', 'resb', 'byte', 'mov', 'add', 'inc', 'cmp', 'jl', 'xor', 'syscall'],
  c:   ['include', 'int', 'char', 'void', 'return', 'for', 'printf', 'scanf', 'main'],
  cpp: ['include', 'int', 'void', 'return', 'for', 'std', 'string', 'cout', 'cin', 'endl', 'main'],
  py:  ['for', 'in', 'range', 'print', 'input', 'int'],
  js:  ['const', 'let', 'for', 'console', 'log', 'prompt', 'Number'],
};
const COMMENT = { asm: ';[^\\n]*', c: '//[^\\n]*', cpp: '//[^\\n]*', py: '#[^\\n]*', js: '//[^\\n]*' };

function highlight(code, langId) {
  const esc = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const re = new RegExp(
    '("[^"\\n]*")|(' + COMMENT[langId] + ')|(\\b(?:' + KEYWORDS[langId].join('|') + ')\\b)|(\\b\\d+\\b)', 'g');
  return esc.replace(re, (m, str, com, kw) =>
    '<span class="' + (str ? 'str' : com ? 'com' : kw ? 'kw' : 'num') + '">' + m + '</span>');
}
```

Вызывается как `highlight(CODE[taskId][lang.id], lang.id)`. Классы в Dracula: `.kw { color: #8be9fd }`, `.str { color: #f1fa8c }`, `.num { color: #ffb86c }`, `.com { color: #6272a4 }`, фон блока `#15151c`.

- [ ] **Step 3: Вкладка «Одна задача — пять языков»**

Сетка: слева колонка из четырёх кнопок-задач, справа — табы языков, блок кода, строка-метрика и окно вывода. На узком экране колонка задач уезжает наверх (`grid-template-columns: 1fr` в медиазапросе до 720px), табы языков не переносятся — `display: grid; grid-template-columns: repeat(5, 1fr)`.

Строка-метрика под кодом собирается так:

```js
function metrics(taskId, lang) {
  const code = CODE[taskId][lang.id];
  const lines = code.trim().split('\n').length;
  const cut = lang.id === 'asm' && CUT[taskId] ? ' + обрезано' : '';
  const need = NEED_OVERRIDE[taskId + ':' + lang.id] || lang.need;
  return 'строк: ' + lines + cut + '  ·  перевод: ' + lang.how + '  ·  чтобы запустить: ' + need;
}
```

Поля ввода над окном вывода: «твоё имя» (по умолчанию `Лиза`), «первое число» (7), «второе число» (5). Они общие для всех языков: меняешь — вывод пересчитывается везде одинаково. Вывод печатается по символам, ~18 мс на символ, с курсором в конце; повторный клик по задаче или языку перезапускает печать.

Плашка обрезки показывается только для `asm` и только для задач `name` и `sum`: строка `CUT[taskId]` в приглушённом `#6272a4` сразу под блоком кода.

- [ ] **Step 4: Проверка**

```bash
python3 - lessons/lesson-cs-03-languages/demos/languages.html <<'EOF'
import re, sys
html = open(sys.argv[1], encoding='utf-8').read()
js = '\n'.join(re.findall(r'<script>(.*?)</script>', html, re.S))
open('_check.js', 'w', encoding='utf-8').write(js)
EOF
node --check _check.js && rm _check.js
```

Плюс проверка данных: все 20 листингов на месте и не пустые.

```bash
node -e '
const fs = require("fs"), src = fs.readFileSync("lessons/lesson-cs-03-languages/demos/languages.html", "utf8");
for (const t of ["hello", "name", "sum", "count"])
  for (const l of ["asm", "c", "cpp", "py", "js"])
    if (!new RegExp(l + "\\s*:\\s*`").test(src.split(t)[1] || "")) console.log("проверь листинг", t, l);
console.log("листинги проверены");
'
```

Ожидаемо: `node --check` молчит, скрипт печатает «листинги проверены» без строк «проверь листинг».

- [ ] **Step 5: Проверка листингов настоящими компиляторами**

Листинги C, C++, Python и JS обязаны быть рабочим кодом, а не похожим на код текстом. Проверяются вне репозитория, во временных файлах в скретчпаде; сами файлы после проверки удаляются.

```bash
T=$(mktemp -d)
# по одному файлу на каждый из четырёх листингов C, затем C++
cc -fsyntax-only "$T"/hello.c "$T"/name.c "$T"/sum.c "$T"/count.c && echo "C ok"
c++ -fsyntax-only "$T"/hello.cpp "$T"/name.cpp "$T"/sum.cpp "$T"/count.cpp && echo "C++ ok"
python3 -m py_compile "$T"/hello.py "$T"/name.py "$T"/sum.py "$T"/count.py && echo "Python ok"
node --check "$T"/count.js && echo "JS ok"
rm -rf "$T"
```

Листинги с `prompt` (`name.js`, `sum.js`) проверять `node --check` можно — это синтаксис, а не запуск. Ассемблер на macOS не собрать (листинги под Linux x86-64), он сверяется глазами со слайдом S11 урока cs-02, откуда взят стиль.

Ожидаемо: четыре строки «ok», ни одной ошибки компилятора.

- [ ] **Step 6: Commit**

```bash
git add lessons/lesson-cs-03-languages/demos/
git commit -m "Add lesson cs-03 trainer: one task in five languages with run metrics"
```

---

### Task 4: demos/languages.html — вкладки «Как это запускается» и «JS: консоль vs браузер»

**Files:**
- Modify: `lessons/lesson-cs-03-languages/demos/languages.html`

**Interfaces:**
- Consumes: каркас табов, `LANGS`, палитру и стили из Task 3.
- Produces: законченный тренажёр для сценария, конспекта и лендинга.

- [ ] **Step 1: Вкладка «Как это запускается»**

Четыре дорожки, каждая — ряд «чипов», соединённых стрелками:

```
asm     исходник → ассемблер → линкер → машинный код → CPU        перевод до запуска
C/C++   исходник → компилятор → линкер → машинный код → CPU       один раз, дальше только файл
Python  исходник → интерпретатор: строка за строкой → CPU         каждый запуск заново
JS      исходник → движок: интерпретирует, горячее компилирует → CPU   и так, и так
```

Кнопка «Прогнать» на каждой дорожке подсвечивает чипы по очереди:

```js
function runTrack(track) {
  const chips = track.querySelectorAll('.chip');
  chips.forEach(c => c.classList.remove('lit'));
  chips.forEach((chip, i) => setTimeout(() => chip.classList.add('lit'), i * 420));
}
```

У дорожки Python подпись «и так — при каждом запуске», у JS горячий чип получает пульсацию (`animation: pulse 1s ease-in-out 2`). Подсветка `lit` — фон `--yellow`, текст `--bg`.

- [ ] **Step 2: Вкладка «JS: консоль vs браузер»**

Один общий код и две колонки-вердикта:

```js
const JS_LINES = [
  { code: 'const name = "Лиза";',            browser: true,  node: true,  why: '' },
  { code: 'console.log("Привет, " + name);', browser: true,  node: true,  why: '' },
  { code: 'alert("Привет, " + name);',       browser: true,  node: false, why: 'в консоли: alert is not defined' },
  { code: 'document.title = "Привет!";',     browser: true,  node: false, why: 'в консоли: document is not defined' },
  { code: 'const fs = require("node:fs");',  browser: false, node: true,  why: 'в браузере: require is not defined' },
];
```

Рендер: строка кода моноширинно, справа две отметки — «браузер» и «консоль», зелёная `--green` галочка или красный крест `--orange`, под строкой — текст `why` мелким шрифтом, если есть. Кнопка «Запустить» проигрывает строки сверху вниз по 500 мс, красные строки печатают ошибку в окошко вывода. Внизу плашка: «Язык один, движок один. Разные среды выдают разные руки: браузеру — страницу, консоли — файлы».

- [ ] **Step 3: Проверка**

```bash
python3 - lessons/lesson-cs-03-languages/demos/languages.html <<'EOF'
import re, sys
html = open(sys.argv[1], encoding='utf-8').read()
js = '\n'.join(re.findall(r'<script>(.*?)</script>', html, re.S))
open('_check.js', 'w', encoding='utf-8').write(js)
EOF
node --check _check.js && rm _check.js
grep -c 'class="tab' lessons/lesson-cs-03-languages/demos/languages.html
grep -c 'panel' lessons/lesson-cs-03-languages/demos/languages.html
```

Ожидаемо: синтаксис чистый, три таба, три панели.

- [ ] **Step 4: Commit**

```bash
git add lessons/lesson-cs-03-languages/demos/languages.html
git commit -m "Add lesson cs-03 trainer tabs: run pipeline and browser vs console"
```

---

### Task 5: cheatsheet.html, homework.html, index-final.html

**Files:**
- Create: `lessons/lesson-cs-03-languages/cheatsheet.html`
- Create: `lessons/lesson-cs-03-languages/homework.html`
- Create: `lessons/lesson-cs-03-languages/index-final.html`

**Interfaces:**
- Consumes: корпус кода, таблицу языков, слайды S1–S13, готовый тренажёр.
- Produces: три страницы, на которые ссылается карточка лендинга (Task 6).

- [ ] **Step 1: cheatsheet.html — «Кто переводит твой код»**

Светлый печатный стиль (`#faf7f2` фон, `#1a1a1a` текст, жёлтые акценты), одна страница A4. Секции:

1. «Три способа перевода» — три SVG-дорожки: компилятор (до запуска), интерпретатор (во время), JIT (и так, и так).
2. «Таблица пяти языков» — три колонки из раздела «Таблица языков» этого плана.
3. «Привет, мир на пяти языках» — пять коротких листингов подряд с числом строк.
4. «Браузер и консоль» — табличка: что работает везде, что только в браузере, что только в консоли.
5. «Запомни» — три факта: код это текст, без среды исполнения он мёртв; компилятор переводит один раз, интерпретатор — каждый раз; JS в браузере и в консоли — один язык, разные руки.

- [ ] **Step 2: homework.html — «Кто переводит твой код»**

Тот же печатный стиль. Три задания:

1. Соотнеси: пять языков ↔ три способа перевода. Рядом с каждым языком — строка «чтобы запустить, нужно: ______».
2. Открой в браузере консоль (F12 → Console), набери три строки и запиши, что вывелось:
   `let x = 5;` / `let y = 7;` / `console.log(x + y);`
3. Бонус: пройди в тренажёре все четыре задачи на всех пяти языках и найди, где разница в количестве строк самая большая. Запиши задачу и оба числа.

Внизу — ссылка на тренажёр `demos/languages.html` и напоминание, что устанавливать ничего не нужно.

- [ ] **Step 3: index-final.html — резервный конспект ведущего**

Тёмный конспект по образцу cs-02: тайминг блоками, ключевые формулировки, все листинги «hello» на пяти языках в Dracula-палитре, схема трёх способов, таблица браузер/консоль. Нужен, если слайды или тренажёр не откроются на вебинаре.

- [ ] **Step 4: Проверка**

```bash
ls lessons/lesson-cs-03-languages/
grep -riE "дружина|DOM|семантик|парсинг|валидац" lessons/lesson-cs-03-languages/*.html && echo "ЗАПРЕТ" || echo "чисто"
grep -l "faf7f2" lessons/lesson-cs-03-languages/cheatsheet.html lessons/lesson-cs-03-languages/homework.html
```

Ожидаемо: все файлы урока на месте, запрещённых слов нет, обе печатные страницы в светлой палитре.

- [ ] **Step 5: Commit**

```bash
git add lessons/lesson-cs-03-languages/
git commit -m "Add lesson cs-03 cheatsheet, homework and host notes"
```

---

### Task 6: Лендинг и финальная проверка урока

**Files:**
- Modify: `index.html` (блок «Компьютер изнутри»: заглушка cs-03 → карточка урока)

**Interfaces:**
- Consumes: готовые файлы урока из Task 1–5, разметку карточек cs-01 и cs-02.
- Produces: рабочий вход в урок с главной страницы.

- [ ] **Step 1: Найти заглушку**

```bash
grep -n "cs-03" index.html
```

- [ ] **Step 2: Заменить заглушку карточкой**

Карточка по образцу соседних cs-01 и cs-02: номер урока, заголовок «Языки программирования», строка-описание «Кто переводит твой код: компилятор, интерпретатор, JIT. Пять языков — одна задача», чипы-ссылки на `slides.html`, `cheatsheet.html`, `homework.html` и тренажёр `demos/languages.html` (иконка-чип, как у демок cs-01 и cs-02). Разметку соседних карточек не переписывать.

- [ ] **Step 3: Проверка ссылок**

```bash
node -e '
const fs = require("fs");
const html = fs.readFileSync("index.html", "utf8");
const links = [...html.matchAll(/href="(lessons\/lesson-cs-03-languages\/[^"]+)"/g)].map(m => m[1]);
if (!links.length) { console.log("НЕТ ССЫЛОК НА cs-03"); process.exit(1); }
links.forEach(p => console.log(fs.existsSync(p) ? "ok   " + p : "БИТАЯ " + p));
'
```

Ожидаемо: все ссылки существуют, битых нет.

- [ ] **Step 4: brand-guardian**

Прогнать сабагента `brand-guardian` по `lessons/lesson-cs-03-languages/` и изменённому блоку `index.html`. Найденные нарушения бренда и запретов исправить до коммита.

- [ ] **Step 5: Ручной предпросмотр (за Димасом, не за агентом)**

Отдать Димасу список: слайды листаются стрелками до S13; в тренажёре работают все три вкладки, имя и числа подставляются во все пять языков, обрезка асма видна только на «Спроси имя» и «Сложи два числа»; шпаргалка и домашка открываются и печатаются; на телефоне ничего не уезжает по горизонтали.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Wire lesson cs-03 into landing page"
```

---

## Порядок и зависимости

Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6, строго последовательно: каждая следующая опирается на нумерацию слайдов и корпус кода, зафиксированные раньше. Внутри Task 3 и Task 4 файл один и тот же — параллелить их нельзя.
