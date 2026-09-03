# История JavaScript: версии и изменения в стандарте

> Полная хронология ECMA-262 от Mocha (1995) до ES2026 (17-е издание, июнь 2026)
> и того, что уже стоит в очереди на ES2027.
> Справочник для разработчика. Актуально на **31 августа 2026**.

---

## 0. Как вообще устроена нумерация

Три разных вещи, которые постоянно путают:

| Термин | Что это |
|---|---|
| **JavaScript** | Торговая марка. Принадлежит Oracle (унаследована от Sun через покупку 2010 г.). Разговорное имя языка. |
| **ECMAScript** | Название стандарта. Придумано именно потому, что имя «JavaScript» было занято. Brendan Eich называл его «an unwanted trade name that sounds like a skin disease». |
| **ECMA-262** | Номер документа Ecma International, в котором стандарт живёт. Есть зеркало ISO/IEC 16262. |

Плюс отдельные спецификации, которые формально **не** ECMA-262, но входят в «язык» в широком смысле:

- **ECMA-402** — Internationalization API (`Intl`), свой годовой цикл.
- **ECMA-404** — JSON Data Interchange Syntax.
- **ECMA-419** — ECMAScript embedded systems API.

### Двойная нумерация версий

С 2015 года у каждого издания два имени: порядковое (`ES6`, `ES7`…) и по году (`ES2015`, `ES2016`…).
TC39 официально продвигает **годовое** именование — как раз чтобы убить культ «ES6 = современный JS».
`ES6` жив только как жаргон, означающий «всё, что появилось после ES5».

### Процесс TC39 (введён в 2015 вместе с годовым циклом)

| Stage | Название | Смысл | Что требуется для перехода дальше |
|---|---|---|---|
| **0** | Strawperson | Идея, оформленная кем угодно | Чемпион из состава TC39 |
| **1** | Proposal | Комитет готов рассматривать | Описание проблемы, черновик API, полифилл/демо |
| **2** | Draft | Синтаксис и семантика описаны формально | Полный текст спеки на spec-языке |
| **2.7** | — | *(добавлена в 2023)* спека одобрена, ждём тесты | Тесты test262 написаны и приняты |
| **3** | Candidate | Спека финальна, нужен фидбек от реализаций | Минимум **две** независимые совместимые реализации |
| **4** | Finished | Готово, войдёт в ближайший релиз | PR в ecma262 принят |

**Годовой ритм:** снимок берётся в феврале-марте (TC39 approval), Генеральная ассамблея Ecma
утверждает в июне. Всё, что не успело до stage 4 к моменту снимка, едет в следующий год.
Релиз — это не «мы что-то придумали», а «мы зафиксировали то, что уже год как работает в браузерах».

---

## 1. Доисторический период (1995–1996)

**Май 1995.** Брендан Айк нанят в Netscape. Задача — «Scheme в браузере».
Реальность: маркетинг требует, чтобы это выглядело как Java. Прототип написан за **10 дней**,
название — **Mocha**.

Генеалогия языка (важно понимать, откуда все странности):

- **Scheme** → функции как значения первого класса, замыкания.
- **Self** → прототипное наследование вместо классов.
- **Java** → синтаксис (C-подобный), `try/catch`, примитивы/обёртки, имя.
- **AWK / Perl** → регулярки, лёгкое отношение к типам.
- **HyperTalk** → идея обработчиков событий на элементах.

Отсюда же и вечные болячки: `null` vs `undefined` (два «ничего»), `typeof null === "object"`
(баг первой реализации, тег типа 0 = объект), автоматическая вставка точек с запятой,
неявные приведения типов, `var`-хойстинг.

| Дата | Событие |
|---|---|
| Май 1995 | Прототип **Mocha** за 10 дней |
| Сентябрь 1995 | Переименован в **LiveScript**, отгружен в Netscape Navigator 2.0 beta |
| 4 декабря 1995 | Маркетинговая сделка Netscape + Sun → **JavaScript**. Java была на пике хайпа |
| Август 1996 | Microsoft выпускает **JScript** в IE 3.0 — реверс-инжиниринг, чтобы обойти лицензию |
| Ноябрь 1996 | Netscape сдаёт язык в **Ecma International**, создан **TC39** |

Причина стандартизации предельно прагматичная: два несовместимых движка = война браузеров,
и Netscape нужен был нейтральный арбитр.

---

## 2. ES1 — июнь 1997

Первое издание ECMA-262. По сути, это документированный Netscape JavaScript 1.1.

**Что зафиксировано:**

- Типы: `Undefined`, `Null`, `Boolean`, `Number` (IEEE-754 double), `String` (UTF-16), `Object`.
- Прототипное наследование через `[[Prototype]]`, `new`, конструкторы, `this`.
- Функции как объекты первого класса, замыкания, `arguments`.
- `var`, функциональная область видимости, хойстинг.
- Автоматическая вставка точек с запятой (ASI).
- Встроенные: `Object`, `Function`, `Array`, `String`, `Boolean`, `Number`, `Math`, `Date`.
- Управляющие конструкции: `if/else`, `for`, `for-in`, `while`, `with`, `switch` **отсутствует**.
- Приведение типов: `ToPrimitive`, `ToNumber`, `ToString`, `==` с его таблицей.

**Чего ещё нет:** `try/catch`, регулярных выражений (как встроенного типа), `switch`,
`do-while`, `Array.prototype.push/pop` (появятся в JS 1.2, стандартизуются в ES3).

---

## 3. ES2 — июнь 1998

**Ноль изменений в языке.** Чисто редакционное издание для приведения текста
в соответствие с ISO/IEC 16262. Единственная версия ECMAScript, которую можно
пропустить, ничего не потеряв.

---

## 4. ES3 — декабрь 1999

Первое издание, которое реально расширило язык. Именно ES3 — это тот JavaScript,
на котором мир писал следующие **десять лет** (IE6 поддерживал ES3, и всё).

**Добавлено:**

- **Регулярные выражения** как встроенный тип: литералы `/.../ `, `RegExp`, `String.prototype.match/replace/search/split`.
- **`try / catch / finally`** и `throw`. Иерархия ошибок: `Error`, `EvalError`, `RangeError`, `ReferenceError`, `SyntaxError`, `TypeError`, `URIError`.
- **`switch`**, **`do...while`**, метки (`label:`) с `break`/`continue`.
- `in` и `instanceof` как операторы.
- Форматирование чисел: `Number.prototype.toFixed / toExponential / toPrecision`.
- `encodeURI` / `decodeURI` / `encodeURIComponent` / `decodeURIComponent`.
- `Function.prototype.apply` и `call` формализованы.
- `Array.prototype.push/pop/shift/unshift/splice/slice/concat/join/sort/reverse` — стандартизованы.
- `String.prototype.concat`, `Object.prototype.hasOwnProperty/isPrototypeOf/propertyIsEnumerable`.

**Практический вывод:** «поддержка ES3» и сегодня встречается как baseline в самых
консервативных сборках. Всё, что делает Babel в режиме `es5`, опирается на этот фундамент.

---

## 5. ES4 — версия, которой не было (1999–2008)

Самый поучительный эпизод в истории языка.

**Что хотели:** классы, интерфейсы, пространства имён, пакеты, **опциональная статическая
типизация**, параметризованные типы (дженерики), `const`-биндинги, итераторы/генераторы,
модули. Фактически — превратить JS в что-то среднее между Java и Python.

**Хронология провала:**

| Год | Что произошло |
|---|---|
| 1999–2003 | Работа над ES4 идёт, потом фактически замирает |
| 2000–2006 | Adobe/Macromedia реализуют черновик ES4 как **ActionScript 3** во Flash |
| 2005 | ES4 реанимируют: Mozilla, Adobe, Opera, Google — за |
| 2007 | **Microsoft и Yahoo — против**. Аргумент: слишком большой разрыв обратной совместимости, невозможно внедрить в IE. Дуглас Крокфорд ведёт публичную кампанию против |
| 2007–2008 | Раскол. Douglas Crockford + Microsoft продвигают **ES3.1** — минимальный набор безопасных улучшений |
| Июль 2008 | Встреча TC39 в Осло. **ES4 официально закрыт.** Компромисс назван **«Harmony»** |

**Итоги раскола:**

- **ES3.1** переименован в **ES5** и выпущен в 2009.
- Часть идей ES4 (классы, модули, генераторы, `const`) вернулась в **ES2015** — уже без статической типизации и без пакетов.
- Статическая типизация не вернулась никогда. Её нишу заняли **TypeScript** (2012) и Flow (2014).
- ActionScript 3 остался единственной массовой реализацией ES4 — и умер вместе с Flash в 2020.

**Урок, который TC39 усвоил:** большие ревизии «одним куском» не работают.
Отсюда — годовой цикл и stage-процесс.

---

## 6. ES5 — декабрь 2009

Возвращение языка к жизни после десятилетнего застоя.

**Строгий режим (`"use strict"`)** — главное нововведение. Опциональный, на уровне файла или функции:

- присваивание необъявленной переменной → `ReferenceError`, а не создание глобала;
- `this` в обычном вызове функции = `undefined`, а не глобальный объект;
- запрещены `with`, восьмеричные литералы вида `010`, дублирующиеся имена параметров и ключей;
- `delete` неудаляемого свойства → `TypeError`;
- `arguments.callee` / `caller` / `Function.prototype.caller` запрещены;
- `eval` не «протекает» переменными в окружающую область видимости.

**Работа с объектами (property descriptors):**

- `Object.create`, `Object.defineProperty`, `Object.defineProperties`;
- `Object.getOwnPropertyDescriptor`, `Object.getOwnPropertyNames`, `Object.keys`;
- `Object.getPrototypeOf`;
- `Object.freeze` / `seal` / `preventExtensions` + `isFrozen` / `isSealed` / `isExtensible`;
- геттеры и сеттеры в литералах объектов: `{ get x() {}, set x(v) {} }`;
- атрибуты `writable`, `enumerable`, `configurable`, `value`, `get`, `set`.

**Функциональные методы массивов** (то, ради чего половина людей и переходила на ES5):
`forEach`, `map`, `filter`, `reduce`, `reduceRight`, `some`, `every`, `indexOf`, `lastIndexOf`, `Array.isArray`.

**Прочее:**

- **`JSON`** — встроенный объект `JSON.parse` / `JSON.stringify` (до этого — библиотека Крокфорда).
- `Function.prototype.bind`.
- `String.prototype.trim`.
- `Date.now`, `Date.prototype.toISOString`, `Date.parse` понимает ISO 8601.
- Зарезервированные слова разрешены как имена свойств: `obj.class`, `obj.new`.
- Висячие запятые в литералах массивов и объектов легализованы.
- `String` стал индексируемым: `"abc"[1] === "b"`.

### ES5.1 — июнь 2011

Редакционное издание, синхронизация с ISO/IEC 16262:2011. Изменений языка нет.
Именно ES5.1 — тот самый «стабильный baseline», на который до сих пор компилирует
Babel по умолчанию в legacy-конфигах.

---

## 7. ES2015 (ES6) — 17 июня 2015

Крупнейший релиз в истории языка. Шесть лет разработки, спека выросла с ~250 до ~600 страниц.
До сих пор именно ES2015 определяет, как выглядит современный JS-код.

### Синтаксис

| Фича | Суть |
|---|---|
| `let` / `const` | Блочная область видимости, **TDZ** (temporal dead zone), запрет повторного объявления |
| Стрелочные функции | `x => x * 2`. Лексический `this`, нет `arguments`, нет `prototype`, нельзя `new` |
| Классы | `class`, `extends`, `super`, `constructor`, `static`. **Синтаксический сахар** над прототипами — не новая модель объектов |
| Шаблонные литералы | `` `${a} + ${b}` ``, многострочность, **tagged templates** и `String.raw` |
| Деструктуризация | `const {a, b: [c]} = obj`, значения по умолчанию, в параметрах функций |
| Параметры по умолчанию | `function f(a = 1) {}` |
| Rest / spread | `function f(...args)`, `[...arr]`, `f(...arr)` |
| Сокращённые записи | `{ x, y }`, `{ method() {} }`, вычисляемые ключи `{ [key]: v }` |
| `for...of` | Обход по протоколу итератора, а не по ключам |

### Новые типы и структуры данных

- **`Symbol`** — новый примитив. Уникальные ключи + «well-known symbols», которыми
  настраивается поведение языка: `Symbol.iterator`, `Symbol.hasInstance`,
  `Symbol.toPrimitive`, `Symbol.toStringTag`, `Symbol.species`.
- **`Map` / `Set`** — коллекции с ключами любого типа и предсказуемым порядком вставки.
- **`WeakMap` / `WeakSet`** — слабые ссылки, ключи только объекты, не итерируемы.
- **Typed Arrays** — `ArrayBuffer`, `DataView`, `Int8Array`…`Float64Array`. Перенесены
  из отдельной спеки Khronos в ядро языка.

### Асинхронность и итерация

- **`Promise`** — стандартизован (`then`, `catch`, `Promise.all`, `race`, `resolve`, `reject`).
  До этого — зоопарк из jQuery.Deferred, Q, Bluebird, RSVP.
- **Итераторы** — протокол `[Symbol.iterator]() → { next() → {value, done} }`.
- **Генераторы** — `function*`, `yield`, `yield*`. Основа для корутин и для
  «синхронно выглядящего асинхронного кода» (co, redux-saga).

### Модули

`import` / `export` — **статическая** система модулей на уровне синтаксиса.
Ключевое отличие от CommonJS: связи разрешаются до выполнения, отсюда возможность
tree-shaking и циклических зависимостей через live bindings.

⚠️ Важный исторический нюанс: **синтаксис** модулей вошёл в ES2015, а **механизм
загрузки** — нет. Loader-спека осталась за бортом, её роль на годы взяли на себя
бандлеры (webpack, Rollup). Нативные ES-модули в браузерах поехали только к 2017–2018,
а в Node.js стабилизировались к версии 14 (2020).

### Метапрограммирование

- **`Proxy`** — перехват фундаментальных операций над объектом (13 ловушек: `get`, `set`, `has`, `deleteProperty`, `apply`, `construct`…).
- **`Reflect`** — набор функций, зеркалящих внутренние методы объектов. Правильные дефолты для ловушек Proxy.

### Пополнение стандартной библиотеки

- `Object.assign`, `Object.is`, `Object.setPrototypeOf`, `Object.getOwnPropertySymbols`.
- `Array.from`, `Array.of`, `Array.prototype.find`, `findIndex`, `fill`, `copyWithin`, `entries`, `keys`, `values`. (`Array.prototype.includes` — уже ES2016.)
- `String.prototype.startsWith`, `endsWith`, `includes`, `repeat`, `normalize`, `codePointAt`, `String.fromCodePoint`, `String.raw`.
- `Number.isNaN`, `isFinite`, `isInteger`, `isSafeInteger`, `parseFloat`, `parseInt`, `EPSILON`, `MAX_SAFE_INTEGER`, `MIN_SAFE_INTEGER`.
- `Math`: `trunc`, `sign`, `cbrt`, `hypot`, `log2`, `log10`, `log1p`, `expm1`, `clz32`, `fround`, `imul`, гиперболические.

### Прочее

- Флаг `u` (unicode) у регулярок, флаг `y` (sticky).
- Двоичные (`0b1010`) и восьмеричные (`0o777`) литералы.
- Юникод в идентификаторах и escape вида `\u{1F600}`.
- **Proper tail calls** — единственная фича ES2015, которая **не взлетела**: реализована
  только в JavaScriptCore (Safari). V8 и SpiderMonkey отказались из-за потери стектрейсов.
  Формально в спеке до сих пор.

---

## 8. Годовой цикл: ES2016 → ES2026

С 2016 года релизы небольшие и предсказуемые: снимок берётся в феврале-марте, утверждается в июне.

### ES2016 (ES7) — июнь 2016

Самый маленький релиз в истории. Две фичи — и это была демонстрация того,
что новый процесс работает.

- `Array.prototype.includes` — `NaN`-safe поиск (в отличие от `indexOf`, использует SameValueZero).
- Оператор возведения в степень `**`. `2 ** 10 === 1024`. Правоассоциативен.

### ES2017 (ES8) — июнь 2017

- **`async` / `await`** — главное. Синтаксический сахар над промисами + генераторами.
  Убил callback hell и `.then()`-цепочки как основной стиль.
- `Object.values`, `Object.entries`.
- `Object.getOwnPropertyDescriptors` — нужен для корректного копирования геттеров/сеттеров через `Object.defineProperties`.
- `String.prototype.padStart` / `padEnd` (тот самый релиз, где случился инцидент с `left-pad`… который был годом раньше, но осадочек привёл к добавлению в стандарт).
- Висячие запятые в списках параметров и аргументов функций.
- **`SharedArrayBuffer`** и **`Atomics`** — разделяемая память между воркерами.
  ⚠️ В январе 2018 отключены во всех браузерах из-за **Spectre/Meltdown**; вернулись
  только в 2020+ под требованием заголовков COOP/COEP (cross-origin isolation).

### ES2018 (ES9) — июнь 2018

- **Асинхронная итерация**: `for await (const x of asyncIterable)`, `Symbol.asyncIterator`, `async function*`.
- **Rest/spread для объектов**: `const {a, ...rest} = obj`, `{...obj1, ...obj2}`.
  Заменил `Object.assign` в 90% случаев.
- `Promise.prototype.finally`.
- Регулярки — четыре независимых предложения:
  - именованные группы `(?<name>...)` и `\k<name>`, доступ через `match.groups.name`;
  - **lookbehind** `(?<=...)` и `(?<!...)` — JS был последним из мейнстрима без них;
  - флаг `s` (dotAll) — `.` матчит перевод строки;
  - Unicode property escapes `\p{Script=Cyrillic}`, `\p{Emoji}` (требует флаг `u`).
- Template literal revision — в **tagged** шаблонах разрешены некорректные escape-последовательности (`\unicode`), `cooked` при этом `undefined`, а `raw` доступен. Сделано ради DSL вроде LaTeX-шаблонов.

### ES2019 (ES10) — июнь 2019

- `Array.prototype.flat` / `flatMap`.
  Историческая деталь: метод чуть не назвали `flatten`, но это **сломало бы MooTools**
  на живых сайтах («SmooshGate»). Переименовали в `flat`.
- `Object.fromEntries` — обратная операция к `Object.entries`. Наконец-то нормальный `map` по объекту.
- `String.prototype.trimStart` / `trimEnd`.
- **Опциональный catch binding**: `try {} catch {}` без переменной.
- `Symbol.prototype.description`.
- **Стабильная сортировка** `Array.prototype.sort` — гарантирована спекой (V8 и так уже её дал в Chrome 70).
- `Function.prototype.toString` revision — точный возврат исходного текста, включая комментарии.
- JSON superset — `U+2028` / `U+2029` разрешены в строковых литералах JS (JSON был не подмножеством JS, теперь стал).
- Well-formed `JSON.stringify` — одинокие суррогаты экранируются, а не выдаются как невалидный UTF-8.

### ES2020 (ES11) — июнь 2020

- **`BigInt`** — новый примитив, целые произвольной точности: `9007199254740993n`.
  Не смешивается с `Number` в арифметике (осознанно — чтобы не было тихой потери точности).
- **Optional chaining** `?.` — `a?.b?.[c]?.()`. Короткое замыкание на `null`/`undefined`.
- **Nullish coalescing** `??` — в отличие от `||`, не срабатывает на `0` и `""`.
- `Promise.allSettled`.
- `String.prototype.matchAll` — итератор по всем совпадениям с группами.
- **Динамический `import()`** — возвращает промис, работает в любом контексте. Основа для code splitting.
- `import.meta` — метаданные модуля (`import.meta.url`).
- `export * as ns from "mod"`.
- **`globalThis`** — единый способ добраться до глобального объекта (`window` / `self` / `global` / `this`).
- Порядок обхода `for-in` наконец специфицирован (де-факто работал так везде).

### ES2021 (ES12) — июнь 2021

- `String.prototype.replaceAll` — без `/g`-регулярки.
- `Promise.any` + `AggregateError` — первый **успешный**, зеркало `Promise.all`.
- **Логические операторы присваивания**: `||=`, `&&=`, `??=`. Важно: они **short-circuit**,
  то есть присваивания вообще не происходит (в отличие от `a = a || b`) — критично для сеттеров и Proxy.
- **Числовые разделители**: `1_000_000`, `0xFF_FF`, `1_000n`.
- **`WeakRef`** и **`FinalizationRegistry`** — слабые ссылки и колбэки на сборку мусора.
  В спеке прямым текстом: «не полагайтесь на это, поведение GC не гарантировано».

### ES2022 (ES13) — июнь 2022

Релиз, который «дозакрыл» классы.

- **Поля классов**: публичные (`x = 1`) и **приватные** (`#x = 1`), инстансные и статические.
- **Приватные методы и аксессоры**: `#method() {}`, `get #x() {}`. Настоящая инкапсуляция
  на уровне движка, а не соглашение `_x`.
- **Статические блоки инициализации**: `static { ... }`.
- **Ergonomic brand checks**: `#x in obj` — проверка «этот объект нашего класса» без try/catch.
- **Top-level `await`** — в модулях. Меняет модуль на асинхронный, блокирует импортёров.
- `Object.hasOwn(obj, key)` — замена `Object.prototype.hasOwnProperty.call(obj, key)`.
- `.at()` у `String`, `Array`, `TypedArray` — отрицательные индексы: `arr.at(-1)`.
- **`Error.prototype.cause`**: `new Error("msg", { cause: err })` — цепочки ошибок.
- Флаг `d` (`hasIndices`) у регулярок — `match.indices` со смещениями групп.

### ES2023 (ES14) — июнь 2023

- **Поиск с конца**: `Array.prototype.findLast` / `findLastIndex` (и на TypedArray).
- **Change Array by Copy** — иммутабельные версии мутирующих методов:
  `toSorted()`, `toReversed()`, `toSpliced()`, `with(i, v)`.
  Огромная вещь для React/Redux — конец `[...arr].sort()`.
- **Hashbang grammar**: `#!/usr/bin/env node` в первой строке — легализовано в спеке
  (Node и раньше это ел, но нестандартно).
- **Symbols as WeakMap keys** — незарегистрированные символы можно использовать как слабые ключи.

### ES2024 (ES15) — июнь 2024

- **`Object.groupBy` / `Map.groupBy`** — группировка коллекции по ключу.
  Обратите внимание: `Object.groupBy` возвращает объект с **null-прототипом**.
- **`Promise.withResolvers()`** — `{promise, resolve, reject}` одним вызовом.
  Конец паттерна с внешними переменными и `let resolve;`.
- **Resizable ArrayBuffer** (`maxByteLength` + `.resize()`) и **growable SharedArrayBuffer** (`.grow()`).
- **`ArrayBuffer.prototype.transfer`** / `transferToFixedLength` — явный move-семантик буфера (detach).
- **`Atomics.waitAsync`** — неблокирующее ожидание на разделяемой памяти. Работает в главном потоке.
- `String.prototype.isWellFormed` / `toWellFormed` — проверка и починка одиноких суррогатов.
- **Флаг `v` регулярок** (`unicodeSets`) — множества строк, разность/пересечение
  (`[\p{X}--\p{Y}]`, `[\p{X}&&\p{Y}]`), корректная работа с многокодпойнтовыми графемами.
- Well-formed `Unicode` + «RegExp `v` flag» — вместе закрывают старую боль
  «эмодзи ломает мою регулярку».

### ES2025 (ES16) — 25 июня 2025

Крупный релиз, в основном про итераторы и модули.

- **Iterator helpers** — ленивые методы прямо на итераторах:
  `.map()`, `.filter()`, `.take()`, `.drop()`, `.flatMap()`, `.reduce()`,
  `.toArray()`, `.forEach()`, `.some()`, `.every()`, `.find()`.
  Плюс `Iterator.from()`. Наконец-то можно обрабатывать бесконечные последовательности
  без промежуточных массивов.
- **Set methods** — `union`, `intersection`, `difference`, `symmetricDifference`,
  `isSubsetOf`, `isSupersetOf`, `isDisjointFrom`. Через 10 лет после появления `Set`.
- **`Promise.try(fn)`** — оборачивает синхронный бросок в отклонённый промис.
- **Import Attributes** — `import data from "./d.json" with { type: "json" }`.
  (Переименование из `assert {}`, которое так и не дожило до стандарта.)
- **JSON Modules** — собственно импорт JSON, требует import attribute.
- **`RegExp.escape(str)`** — экранирование строки для вставки в регулярку.
- **RegExp Modifiers** — локальные флаги внутри паттерна: `(?i:...)`, `(?-i:...)`.
- **Duplicate named capture groups** — `(?<y>a)|(?<y>b)` в разных альтернативах.
- **`Float16Array`**, `DataView.prototype.getFloat16/setFloat16`, `Math.f16round`.
  Для ML-инференса и графики.
- Redeclarable global `eval`-introduced vars — уборка мусора в спеке.

### ES2026 (ES17) — 30 июня 2026 · **текущая версия**

Одобрено TC39 в марте 2026, утверждено Генеральной ассамблеей Ecma **30 июня 2026**.
Восемь фич, тема релиза — точность данных и байты.

| Фича | Что даёт |
|---|---|
| **`Math.sumPrecise(iterable)`** | Суммирование без накопления ошибки округления (алгоритм Шевчука). `Math.sumPrecise([0.1, 0.2]) === 0.30000000000000004`? Нет — точная сумма |
| **`Iterator.concat(...iterables)`** | Ленивое склеивание итераторов без ручного генератора. Дополняет iterator helpers из ES2025 |
| **`Array.fromAsync(asyncIterable)`** | Асинхронный аналог `Array.from`. Собирает async-итерируемое в массив, последовательно |
| **`Error.isError(v)`** | Надёжная проверка «это Error» — работает через realm-границы, не обманывается `Object.create(Error.prototype)` и подделкой `Symbol.toStringTag` |
| **Upsert: `Map.prototype.getOrInsert` / `getOrInsertComputed`** (и на `WeakMap`) | Получить-или-вставить за один проход хеша вместо `has` + `get` + `set` |
| **`Uint8Array` ↔ Base64/Hex** | `toBase64()`, `fromBase64()`, `toHex()`, `fromHex()`, `setFromBase64()`, `setFromHex()`. Конец костылям через `btoa` + `String.fromCharCode` |
| **JSON.parse source text access** | Третий аргумент reviver'а — контекст с `source`: исходный текст значения. Позволяет прочитать `12345678901234567890` как BigInt/Decimal без потери точности |
| **`JSON.rawJSON(str)`** | Обратная сторона: вставить в `JSON.stringify` заранее подготовленный сырой JSON-литерал. `JSON.isRawJSON()` в комплекте |

Практически: последние две фичи вместе решают **round-trip проблему** — раньше
`JSON.stringify(JSON.parse(s))` мог тихо испортить большие числа и денежные суммы.

---

## 9. ES2027 — что уже прошло stage 4

Эти предложения формально завершены (**stage 4**) и войдут в 18-е издание,
которое ожидается в июне 2027.

- **`Temporal`** — новый API даты/времени. Гигантский: `Temporal.Instant`,
  `PlainDate`, `PlainTime`, `PlainDateTime`, `ZonedDateTime`, `Duration`, `PlainYearMonth`,
  `PlainMonthDay`. Иммутабельный, с явными таймзонами и календарями, с нормальной
  арифметикой. Похороны `Date` (который был скопирован с `java.util.Date` в 1995
  и был плох уже тогда). Уже отгружается за флагами / в Firefox.
- **Explicit Resource Management** — `using` и `await using`, `Symbol.dispose`,
  `Symbol.asyncDispose`, `DisposableStack` / `AsyncDisposableStack`.
  RAII в JavaScript: детерминированное освобождение файлов, сокетов, локов.
- **Joint Iteration** — `Iterator.zip()` и `Iterator.zipKeyed()`. Параллельный обход
  нескольких итераторов.
- **`Atomics.pause()`** — подсказка процессору в spin-wait цикле (аналог `PAUSE` / `YIELD`).

---

## 10. Что сейчас в stage 3 (следующая волна)

Stage 3 = спека финальна, идёт сбор фидбека от реализаций. Обычно 1–3 года до релиза.

| Предложение | Суть |
|---|---|
| **Deferring Module Evaluation** | `import defer * as ns from "mod"` — модуль загружается, но не выполняется до первого обращения. Стартовое время приложений |
| **Source Phase Imports** | `import source Mod from "./m.wasm"` — получить неинстанцированный модуль (в первую очередь для WebAssembly) |
| **Import Text** | Импорт файла как строки: `import txt from "./x.txt" with { type: "text" }` |
| **Iterator chunking** | `.chunks(n)` и `.windows(n)` на итераторах |
| **Iterator Includes / Join** | `.includes()` и `.join()` для итераторов — добивают паритет с массивами |
| **Error Stack Accessor** | Стандартизация `error.stack` (де-факто есть везде, в спеке — нет) |
| **Dynamic Code Brand Checks** | Безопасная работа с `eval`/`Function` в Trusted Types окружении |
| **RegExp Buffer Boundaries** | `\A`, `\z`, `\Z` — якоря начала/конца строки, не зависящие от флага `m` |
| **Legacy RegExp features** | Формализация древних `RegExp.$1`, `RegExp.lastMatch` — чтобы их можно было корректно **не** реализовывать |
| **Non-extensible Applies to Private** | Запрет добавления приватных полей к non-extensible объектам |

Отдельно стоит следить за **Decorators** (stage 3 много лет, четвёртая по счёту редакция
дизайна; уже используются в Angular/TypeScript в разных несовместимых версиях),
**Records & Tuples** (stage 2, судьба под вопросом — движки жаловались на сложность),
**Pattern Matching** (stage 1, `match` выражение) и **Signals** (stage 1, реактивность в ядре).

---

## 11. Сводная таблица

| Издание | Дата | Кодовое имя | Ключевое |
|---|---|---|---|
| 1 | Июнь 1997 | ES1 | Базовый язык, прототипы, `var`, ASI |
| 2 | Июнь 1998 | ES2 | Только правки под ISO |
| 3 | Декабрь 1999 | ES3 | RegExp, `try/catch`, `switch`, `do-while` |
| — | 1999–2008 | ES4 | **Отменено.** Классы + статическая типизация |
| 5 | Декабрь 2009 | ES5 | strict mode, JSON, дескрипторы, методы массивов |
| 5.1 | Июнь 2011 | ES5.1 | Только правки под ISO |
| 6 | Июнь 2015 | ES2015 / ES6 | `let/const`, классы, модули, Promise, стрелки, Map/Set, Symbol, Proxy, генераторы |
| 7 | Июнь 2016 | ES2016 | `includes`, `**` |
| 8 | Июнь 2017 | ES2017 | `async/await`, `Object.values/entries`, SharedArrayBuffer |
| 9 | Июнь 2018 | ES2018 | `for await`, object spread, lookbehind, named groups |
| 10 | Июнь 2019 | ES2019 | `flat`, `fromEntries`, optional catch, стабильный sort |
| 11 | Июнь 2020 | ES2020 | `BigInt`, `?.`, `??`, `import()`, `globalThis` |
| 12 | Июнь 2021 | ES2021 | `replaceAll`, `Promise.any`, `\|\|=`, `1_000`, WeakRef |
| 13 | Июнь 2022 | ES2022 | Приватные поля `#x`, top-level await, `Object.hasOwn`, `.at()`, `Error.cause` |
| 14 | Июнь 2023 | ES2023 | `findLast`, `toSorted`/`with`, hashbang |
| 15 | Июнь 2024 | ES2024 | `Object.groupBy`, `Promise.withResolvers`, resizable buffers, regexp `v` |
| 16 | Июнь 2025 | ES2025 | Iterator helpers, Set methods, import attributes, `Promise.try`, `RegExp.escape` |
| **17** | **Июнь 2026** | **ES2026** | **`Math.sumPrecise`, `Iterator.concat`, `Array.fromAsync`, `Error.isError`, upsert, Uint8Array↔base64, JSON source access** |
| 18 | Июнь 2027 *(ожид.)* | ES2027 | `Temporal`, `using`, `Iterator.zip`, `Atomics.pause` |

---

## 12. Что в языке умерло или помечено как legacy

Полезно держать в голове — обратная совместимость в JS практически абсолютна,
поэтому «мёртвое» никуда не девается, а оседает в **Annex B** (нормативно-опциональное
приложение «для веб-браузеров»).

**Annex B / не использовать:**

- `escape()` / `unescape()` — сломаны для не-ASCII.
- `String.prototype.substr` — путается с `substring`, семантика другая.
- `String.prototype.anchor/big/blink/bold/fontcolor/…` — HTML-обёртки из 1996.
- `Date.prototype.getYear` / `setYear` — Y2K-наследие.
- `RegExp.$1`…`$9`, `RegExp.lastMatch`, `RegExp.input` — глобальное состояние.
- HTML-подобные комментарии `<!--` и `-->` в теле скрипта.
- Восьмеричные литералы `0777` (запрещены в strict mode).
- `document.all` — единственный объект со специальным `[[IsHTMLDDA]]`: `typeof document.all === "undefined"`, но `document.all` истинен как объект. Оставлен, потому что удаление сломало бы сайты.

**Не рекомендовано, но не Annex B:**

- `with` — запрещён в strict mode и в модулях.
- `arguments.callee` / `caller` — `TypeError` в strict mode.
- `__proto__` как свойство — нормативно в Annex B; используйте `Object.getPrototypeOf/setPrototypeOf`.
- `var` — работает, но `let`/`const` покрывают все сценарии.
- `eval` — не удалён, но с ним не работает ни один статический анализатор.

**Фичи, которые не дожили:**

| Предложение | Судьба |
|---|---|
| ES4 целиком | Отменено в 2008 |
| Proper tail calls | В спеке ES2015, реализовано только в JavaScriptCore |
| `Object.observe` | Stage 2, отозвано в 2015 в пользу `Proxy` |
| SIMD.js | Отозвано, роль ушла к WebAssembly SIMD |
| ES Module Loader spec | Выпилено из ES2015, отдано хостам (HTML/Node) |
| `Array.prototype.flatten` | Переименован в `flat` из-за SmooshGate (MooTools) |
| Import Assertions (`assert {}`) | Заменены на Import Attributes (`with {}`) до релиза |
| Records & Tuples | Stage 2, фактически заморожено — движки против |
| Decorators v1/v2/v3 | Три полностью переписанных дизайна, актуален четвёртый |

---

## 13. Практические заметки

**Что значит «версия» на практике.** Реализации не выпускают «поддержку ES2026» целиком.
Фичи приезжают по одной, обычно на stage 3, за флагом, потом по умолчанию.
Ориентироваться надо не на номер издания, а на:

- **[caniuse.com](https://caniuse.com)** и **[kangax compat-table](https://compat-table.github.io/compat-table/es2016plus/)** — по фичам;
- **Baseline** (Web Platform Dashboard) — консенсусный статус «можно брать»;
- `@babel/preset-env` + browserslist — если нужен реальный контроль над выводом.

**Правило большого пальца на 2026 год:** всё до **ES2022** включительно можно считать
безопасным без транспиляции для evergreen-браузеров и Node ≥ 18. ES2023–ES2024 —
почти везде. ES2025 — iterator helpers и Set methods широко есть, import attributes
местами. ES2026 — только-только начинает разъезжаться.

**Кто пишет спецификацию.** TC39 — технический комитет Ecma. Участники — Google (V8),
Apple (JavaScriptCore), Mozilla (SpiderMonkey), Microsoft, Igalia, Bloomberg, Sony,
Salesforce и др. Заседания раз в два месяца, решения — **консенсусом** (одно «нет»
блокирует). Всё публично на [github.com/tc39](https://github.com/tc39).

**Про торговую марку.** Имя «JavaScript» до сих пор принадлежит Oracle. В ноябре 2024
компания Deno подала в USPTO петицию об аннулировании марки по основаниям
genericness / abandonment / fraud. Дело продолжается; публичного финального
решения TTAB на август 2026 нет. Именно поэтому стандарт называется ECMAScript,
а не JavaScript.

---

## Источники

- [ECMA-262, актуальное издание](https://262.ecma-international.org/) — Ecma International
- [tc39/ecma262 — releases](https://github.com/tc39/ecma262/releases)
- [tc39/proposals — finished proposals](https://github.com/tc39/proposals/blob/main/finished-proposals.md)
- [tc39/proposals — stage 3](https://github.com/tc39/proposals)
- [The TC39 Process](https://tc39.es/process-document/)
- [ECMAScript 2026 specification approved — InfoWorld](https://www.infoworld.com/article/4193461/ecmascript-2026-specification-approved.html)
- [ES2026: What's new in JavaScript — rasc.ch](https://blog.rasc.ch/2026/03/es2026.html)
- [Deno v. Oracle: Canceling the JavaScript Trademark](https://deno.com/blog/deno-v-oracle)
- [MDN: JavaScript language resources](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference)
