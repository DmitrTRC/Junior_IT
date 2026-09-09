/**
 * ============================================================================
 *  ЗАДАЧА ПРО РАЗВЕДЧИКА  —  шесть способов решить одно и то же
 * ============================================================================
 *
 *  Условие:
 *    От разведчика получена радиограмма азбукой Морзе. Разбиение на буквы
 *    потеряно. Известно, что использовались только пять букв:
 *
 *        И = ··      А = ·-      Н = -·      Г = --·      Ч = ---·
 *
 *    Сообщение:  - · · - · · - - · · - - - - ·
 *    Расшифровать текст.
 *
 *  ---------------------------------------------------------------------------
 *  ГЛАВНАЯ ИДЕЯ (ради неё задача и придумана)
 *  ---------------------------------------------------------------------------
 *
 *    Кажется, что раз разбиение потеряно — нужен перебор всех вариантов.
 *    Не нужен. Посмотри на коды:
 *
 *        ··      ·-      -·      --·     ---·
 *
 *    Ни один код не является НАЧАЛОМ другого кода.
 *    Начинается с «·» — значит длина ровно 2 (·· или ·-), решает второй знак.
 *    Начинается с «-» — считаем тире: одно → Н, два → Г, три → Ч, дальше точка.
 *
 *    Такой код называется ПРЕФИКСНЫМ (условие Фано). У префиксного кода
 *    разбиение восстанавливается однозначно и «жадно» — слева направо,
 *    без возвратов. Ровно на этом стоят настоящие ZIP и JPEG (коды Хаффмана).
 *
 *    Проверка перебором: у нашего сообщения ровно ОДИН вариант разбора.
 *
 *  Ответ:  Н(-·) А(·-) И(··) Г(--·) А(·-) Ч(---·)  =  «НАИГАЧ»
 *
 *  (слово бессмысленное — похоже, в исходной цепочке со слайда опечатка;
 *   на алгоритм это никак не влияет, он работает на любой строке)
 *
 *  ---------------------------------------------------------------------------
 *  Запуск:  node morse.js
 *  ---------------------------------------------------------------------------
 */

'use strict';  // eslint-disable no-console

const assert = require('node:assert/strict');

/** Таблица из условия задачи. Точка = '.', тире = '-'. */
const TABLE = Object.freeze({
  '..'  : 'И',
  '.-'  : 'А',
  '-.'  : 'Н',
  '--.' : 'Г',
  '---.': 'Ч',
});

/** Радиограмма со слайда (снята с картинки попиксельно). */
const RADIOGRAM = '-..-..--..----.';

/**
 * Приводит «типографские» знаки к ASCII.
 * В учебниках точка — это «·» (U+00B7), а тире — «−»/«–»/«—», а не дефис.
 */
function normalize(raw) {
  return String(raw)
    .replace(/[·•∙]/g, '.')
    .replace(/[−–—]/g, '-')
    .replace(/\s+/g, '');
}


/* ===========================================================================
 * 1. УЧЕНИК.  Только while, if/else, сравнение символов, склейка строк.
 * ===========================================================================
 *
 * Ничего лишнего: ни массивов, ни объектов, ни регулярок. Ровно те кирпичи,
 * которые есть у ребёнка после уроков «переменные / условия / циклы».
 */
function decodeStudent(code) {
  let result = '';   // сюда копим буквы
  let i = 0;         // на каком знаке стоим

  // Идём по строке, пока не кончилась.
  while (i < code.length) {

    // Берём знак под пальцем и следующий за ним.
    // Если следующего нет — там будет undefined, и ни одно условие не сработает.
    const a = code[i];
    const b = code[i + 1];

    // --- буквы из ДВУХ знаков ---
    if (a === '.' && b === '.') {          // ··
      result = result + 'И';
      i = i + 2;                            // перепрыгнули два знака
    }
    else if (a === '.' && b === '-') {     // ·-
      result = result + 'А';
      i = i + 2;
    }
    else if (a === '-' && b === '.') {     // -·
      result = result + 'Н';
      i = i + 2;
    }

    // --- буква из ТРЁХ знаков ---
    // Важно: эту проверку пишем РАНЬШЕ, чем проверку на Ч,
      // иначе «--·» никогда не сработает.
      //   (потому что «---·» начинается с «--·», и if/else берёт первый вариант)
      //   (это и есть «жадный» разбор: берём самый длинный код, который подходит)
    else if (a === '-' && b === '-' && code[i + 2] === '.') {   // --·
      result = result + 'Г';
      i = i + 3;
    }

    // --- буква из ЧЕТЫРЁХ знаков ---
    else if (a === '-' && b === '-' && code[i + 2] === '-' && code[i + 3] === '.') {  // ---·
      result = result + 'Ч';
      i = i + 4;
    }

    // --- ничего не подошло: в радиограмме мусор ---
    else {
      console.log('Не понимаю знак на позиции ' + i);
      return null;   // null = «расшифровать не смог»
    }
  }

  return result;
}


/* ===========================================================================
 * 2. МИДЛ.  Идиоматичный JS: таблица + «липкая» регулярка.
 * ===========================================================================
 *
 * Велосипед не изобретаем. Задача «откуси с начала один из известных токенов»
 * в JS решается флагом /y (sticky): регулярка обязана совпасть ровно
 * в позиции lastIndex, иначе не совпадёт вообще. Это бесплатно даёт валидацию:
 * дырок и мусора между токенами быть не может по построению.
 *
 * Альтернатива — /g + matchAll, но тогда пришлось бы вручную проверять,
 * что куски идут встык. Sticky делает это за нас.
 */
const ALPHABET = new Map(Object.entries(TABLE));

// Строим регулярку ИЗ таблицы, а не дублируем её руками:
// добавили букву в TABLE — регулярка обновилась сама (DRY).
// Сортировка по убыванию длины обязательна: чередование в JS ленивое,
// без неё '---.' никогда не победит, потому что '-.' совпадёт раньше.
const TOKEN = new RegExp(
  [...ALPHABET.keys()]
    .sort((a, b) => b.length - a.length)
    .map((code) => code.replace(/[.\-]/g, '\\$&'))
    .join('|'),
  'y',
);

function decodeMiddle(code) {
  const re = new RegExp(TOKEN.source, 'y');   // свой экземпляр: lastIndex — это состояние
  const letters = [];

  while (re.lastIndex < code.length) {
    const at = re.lastIndex;
    const hit = re.exec(code);
    if (hit === null) {
      throw new SyntaxError(`Неизвестный код в позиции ${at}: «${code.slice(at, at + 4)}…»`);
    }
    letters.push(ALPHABET.get(hit[0]));
  }

  return letters.join('');   // join, а не += : одна аллокация вместо n
}


/* ===========================================================================
 * 3. ЭКСТРЕМАЛЬНО БЫСТРЫЙ.  Биты, LUT, никаких строк в горячем цикле.
 * ===========================================================================
 *
 * Так пишут под микроконтроллер: развернуть данные в биты, все решения
 * вынести в таблицу, в цикле оставить только индексацию массива.
 *
 * Трюк №1 — точка/тире в бит одной операцией:
 *     '.' = 0x2E = 46  → чётный → 46 & 1 = 0
 *     '-' = 0x2D = 45  → нечётный → 45 & 1 = 1
 *   То есть  charCodeAt(i) & 1  уже и есть бит. Ни сравнений, ни ветвлений.
 *
 * Трюк №2 — код префиксный и не длиннее 4 знаков, значит окна в 4 бита
 *   ХВАТАЕТ, чтобы однозначно определить и букву, и её длину.
 *   Строим две таблицы на 16 входов (LUT — Look-Up Table):
 *
 *     окно   биты   буква  длина      (x = «не важно»)
 *     0..3   00xx     И      2
 *     4..7   01xx     А      2
 *     8..11  10xx     Н      2
 *     12,13  110x     Г      3
 *     14     1110     Ч      4
 *     15     1111     —      0   ← невалидно
 *
 *   В цикле: собрать окно, взять LEN[w] и CHAR[w]. Ни одного if по данным —
 *   предсказатель переходов процессора счастлив.
 *
 * Трюк №3 — один проход. Никакого промежуточного буфера битов: строку
 *   читаем напрямую. Цикл разбит на «горячую» часть (до n-3, где окно
 *   заведомо целиком внутри строки — проверок границ нет вообще) и хвост
 *   из последних <4 знаков, где недостающие биты добиваются нулями.
 *
 * Сложность O(n), ОДНА аллокация — под результат.
 */
const LUT_CHAR = new Uint16Array(16);   // код символа UTF-16
const LUT_LEN  = new Uint8Array(16);    // 0 = невалидное окно

// Таблицы считаем один раз при загрузке модуля — из TABLE, чтобы не разъехалось.
for (const [code, letter] of Object.entries(TABLE)) {
  const k = code.length;
  let bits = 0;
  for (let i = 0; i < k; i++) bits = (bits << 1) | (code.charCodeAt(i) & 1);
  const base = bits << (4 - k);                 // подняли в старшие биты окна
  for (let tail = 0; tail < (1 << (4 - k)); tail++) {   // все «не важно» хвосты
    LUT_CHAR[base | tail] = letter.charCodeAt(0);
    LUT_LEN [base | tail] = k;
  }
}

function decodeExtreme(code) {
  const n = code.length;
  if (n === 0) return '';

  // Букв не больше, чем n/2 (самая короткая буква — 2 знака).
  // Пишем сразу коды UTF-16 в типизированный массив: ни одной строки в цикле.
  const out = new Uint16Array((n >> 1) + 1);

  let i = 0;
  let o = 0;

  // ── ГОРЯЧИЙ ЦИКЛ ────────────────────────────────────────────────────────
  // Пока до конца строки заведомо ≥ 4 знака, окно собирается без проверок
  // границ. Внутри: 4 charCodeAt, 4 & 1, 3 сдвига, 2 чтения из таблицы.
  // Ни одного ветвления, зависящего от данных.
  const limit = n - 3;
  while (i < limit) {
    const w = ((code.charCodeAt(i)     & 1) << 3)
            | ((code.charCodeAt(i + 1) & 1) << 2)
            | ((code.charCodeAt(i + 2) & 1) << 1)
            |  (code.charCodeAt(i + 3) & 1);
    const len = LUT_LEN[w];
    if (len === 0) throw new RangeError(`Битый код в позиции ${i} (окно 0b1111)`);
    out[o++] = LUT_CHAR[w];
    i += len;
  }

  // ── ХВОСТ ───────────────────────────────────────────────────────────────
  // Последние <4 знака: за концом строки подставляем нули (точки).
  // Обрезанную букву ловим проверкой i + len > n.
  while (i < n) {
    let w = 0;
    for (let k = 0; k < 4; k++) w = (w << 1) | (i + k < n ? (code.charCodeAt(i + k) & 1) : 0);
    const len = LUT_LEN[w];
    if (len === 0 || i + len > n) {
      throw new RangeError(`Битый код в позиции ${i} (окно 0b${w.toString(2).padStart(4, '0')})`);
    }
    out[o++] = LUT_CHAR[w];
    i += len;
  }

  return codeUnitsToString(out.subarray(0, o));
}

/** String.fromCharCode(...arr) ломается на длинных массивах — режем на куски. */
function codeUnitsToString(units) {
  const CHUNK = 8192;
  if (units.length <= CHUNK) return String.fromCharCode.apply(null, units);
  let s = '';
  for (let i = 0; i < units.length; i += CHUNK) {
    s += String.fromCharCode.apply(null, units.subarray(i, i + CHUNK));
  }
  return s;
}


/* ===========================================================================
 * 4. УЛЬТРА-ФУНКЦИОНАЛЬНЫЙ.  Ни одного цикла, ни одной мутации.
 * ===========================================================================
 *
 * Всё выражено композицией чистых функций:
 *   • Either (Right/Left) — ошибка как значение, а не как throw;
 *   • cons-список — неизменяемый аккумулятор за O(1) на добавление
 *     (spread-в-новый-массив дал бы O(n²));
 *   • батут (trampoline) — хвостовая рекурсия без переполнения стека,
 *     потому что V8 TCO так и не завёз.
 *
 * Читается тяжелее, работает медленнее — зато состояния нет вообще,
 * и каждый кусок тестируется отдельно.
 */
const pipe = (...fns) => (x) => fns.reduce((v, f) => f(v), x);

const Right = (v) => ({
  isRight: true,
  map:   (f) => Right(f(v)),
  chain: (f) => f(v),
  fold:  (_l, r) => r(v),
});
const Left = (e) => ({
  isRight: false,
  map:   () => Left(e),
  chain: () => Left(e),
  fold:  (l) => l(e),
});

// Батут: функция возвращает либо результат, либо «продолжение» — thunk.
const trampoline = (fn) => (...args) => {
  let bounce = fn(...args);
  while (typeof bounce === 'function') bounce = bounce();
  return bounce;
};

// Неизменяемый список: cons(head, tail). Копим в обратном порядке.
const cons = (head, tail) => ({ head, tail });
const listToString = trampoline(function walk(list, acc) {
  return list === null ? acc : () => walk(list.tail, list.head + acc);
});

// Пары [код, буква], длинные коды первыми — то же правило, что и у мидла.
const ENTRIES = Object.freeze(
  Object.entries(TABLE).sort(([a], [b]) => b.length - a.length),
);

// Чистый матчер: (строка, позиция) → [код, буква] | undefined
const matchAt = (code) => (at) => ENTRIES.find(([token]) => code.startsWith(token, at));

const decodeFP = (code) => {
  const match = matchAt(code);

  const walk = trampoline(function go(at, acc) {
    if (at >= code.length) return Right(acc);
    const hit = match(at);
    return hit === undefined
      ? Left(`Неизвестный код в позиции ${at}`)
      : () => go(at + hit[0].length, cons(hit[1], acc));
  });

  return pipe(
    () => walk(0, null),
    (either) => either.map((list) => listToString(list, '')),
    (either) => either.fold(
      (err) => { throw new SyntaxError(err); },
      (str) => str,
    ),
  )();
};


/* ===========================================================================
 * 5. ООП СПОКОЙНЫЙ.  Два класса, без церемоний.
 * ===========================================================================
 *
 * Ровно та степень ООП, которая окупается: алфавит знает про коды,
 * декодер знает про обход строки. Разделили — и хватит.
 * Никаких интерфейсов, фабрик и контейнеров: их здесь нечем оправдать.
 */
class MorseAlphabet {
  #byCode;
  #maxCodeLength;

  constructor(table = TABLE) {
    this.#byCode = new Map(Object.entries(table));
    this.#maxCodeLength = Math.max(...[...this.#byCode.keys()].map((c) => c.length));
  }

  /**
   * Ищет самый длинный код, совпадающий с началом строки в позиции `at`.
   * @returns {{letter: string, length: number} | null}
   */
  matchAt(code, at) {
    // Пробуем от длинного к короткому: '---.' раньше '-.'
    for (let len = this.#maxCodeLength; len >= 1; len--) {
      const letter = this.#byCode.get(code.slice(at, at + len));
      if (letter !== undefined) return { letter, length: len };
    }
    return null;
  }
}

class MorseDecoder {
  #alphabet;

  constructor(alphabet = new MorseAlphabet()) {
    this.#alphabet = alphabet;
  }

  decode(code) {
    const letters = [];
    let at = 0;
    while (at < code.length) {
      const hit = this.#alphabet.matchAt(code, at);
      if (hit === null) throw new SyntaxError(`Неизвестный код в позиции ${at}`);
      letters.push(hit.letter);
      at += hit.length;
    }
    return letters.join('');
  }
}

const decodeOOP = (code) => new MorseDecoder().decode(code);


/* ===========================================================================
 * 6. ООП ПО ФЭНШУЮ.  SOLID во всей красе.
 * ===========================================================================
 *
 * Оговорка честного взрослого: для этой задачи это оверкилл. Показываю,
 * КАК выглядит по учебнику, а не КОГДА так надо делать. Пятнадцать знаков
 * азбуки Морзе не заслуживают пяти абстракций — но система, у которой
 * завтра появится код Хаффмана, Бодо и Base32, уже заслуживает.
 *
 * S (Single Responsibility) — каждый класс делает ровно одно:
 *       нормализация / хранение кодов / нарезка на токены / сборка результата.
 * O (Open-Closed)          — новый алфавит или новая стратегия нарезки
 *       добавляются НОВЫМ классом, MorseDecoder не трогаем.
 * L (Liskov)               — любой наследник Tokenizer подставляется вместо
 *       базового и не ломает декодер: контракт «отдай последовательность букв».
 * I (Interface Segregation)— интерфейсы крошечные, по одному методу.
 *       Токенайзеру не нужен normalize(), нормализатору не нужен lookup().
 * D (Dependency Inversion) — MorseDecoder зависит от АБСТРАКЦИЙ, которые
 *       приходят в конструктор, а не создаёт конкретику внутри себя.
 */

/** Доменная ошибка: несёт позицию, а не только текст. */
class DecodeError extends Error {
  constructor(message, position) {
    super(message);
    this.name = 'DecodeError';
    this.position = position;
  }
}

/** @interface — нормализация входа. */
class SymbolNormalizer {
  /** @param {string} raw @returns {string} */
  normalize(raw) { throw new Error('not implemented'); }
}

class MorseSymbolNormalizer extends SymbolNormalizer {
  normalize(raw) { return normalize(raw); }
}

/** @interface — источник соответствий «код → буква». */
class CodeTable {
  /** @returns {string|undefined} */
  lookup(code) { throw new Error('not implemented'); }
  /** @returns {number[]} длины кодов, по убыванию */
  lengths() { throw new Error('not implemented'); }
}

/**
 * Таблица, которая в конструкторе ДОКАЗЫВАЕТ префиксность (условие Фано).
 * Инвариант класса: если объект построился — жадный разбор однозначен.
 * Именно это и есть математическая суть задачи, зафиксированная в коде.
 */
class PrefixFreeCodeTable extends CodeTable {
  #map;
  #lengths;

  constructor(table) {
    super();
    this.#map = new Map(Object.entries(table));
    const codes = [...this.#map.keys()];

    for (const a of codes) {
      for (const b of codes) {
        if (a !== b && b.startsWith(a)) {
          throw new DecodeError(`Код «${a}» — префикс кода «${b}», разбор неоднозначен`, -1);
        }
      }
    }

    this.#lengths = [...new Set(codes.map((c) => c.length))].sort((x, y) => y - x);
  }

  lookup(code) { return this.#map.get(code); }
  lengths() { return this.#lengths; }
}

/** @interface — стратегия нарезки потока на буквы. */
class Tokenizer {
  /** @param {string} stream @returns {Iterable<string>} */
  tokenize(stream) { throw new Error('not implemented'); }
}

/**
 * Жадная нарезка: в каждой позиции берём самый длинный подходящий код.
 * Зависит от CodeTable (абстракции), а не от конкретного алфавита Морзе.
 * Генератор — ленивый: буквы отдаются по одной, вся строка в память не лезет.
 */
class GreedyPrefixTokenizer extends Tokenizer {
  #table;

  constructor(table) {
    super();
    this.#table = table;
  }

  *tokenize(stream) {
    let at = 0;
    while (at < stream.length) {
      let matched = false;
      for (const len of this.#table.lengths()) {
        const letter = this.#table.lookup(stream.slice(at, at + len));
        if (letter !== undefined) {
          yield letter;
          at += len;
          matched = true;
          break;
        }
      }
      if (!matched) {
        throw new DecodeError(`Неизвестный код в позиции ${at}`, at);
      }
    }
  }
}

/** @interface — то, что умеет расшифровывать. */
class Decoder {
  decode(raw) { throw new Error('not implemented'); }
}

class MorseDecoderSolid extends Decoder {
  #normalizer;
  #tokenizer;

  /** Зависимости — снаружи. Внутри — ни одного new. */
  constructor(normalizer, tokenizer) {
    super();
    this.#normalizer = normalizer;
    this.#tokenizer = tokenizer;
  }

  decode(raw) {
    const stream = this.#normalizer.normalize(raw);
    return [...this.#tokenizer.tokenize(stream)].join('');
  }

  /** Фабрика «по умолчанию» — единственное место, где собирается конкретика. */
  static forMorse(table = TABLE) {
    return new MorseDecoderSolid(
      new MorseSymbolNormalizer(),
      new GreedyPrefixTokenizer(new PrefixFreeCodeTable(table)),
    );
  }
}

const SOLID_DECODER = MorseDecoderSolid.forMorse();
const decodeSolid = (code) => SOLID_DECODER.decode(code);


/* ===========================================================================
 *  ПРОВЕРКА: все шесть обязаны давать один и тот же ответ
 * ===========================================================================
 */
const SOLUTIONS = [
  ['1. ученик         ', decodeStudent],
  ['2. мидл           ', decodeMiddle],
  ['3. экстремальный  ', decodeExtreme],
  ['4. функциональный ', decodeFP],
  ['5. ООП спокойный  ', decodeOOP],
  ['6. ООП SOLID      ', decodeSolid],
];

/** Единый вид результата: строка при успехе, null при любой ошибке. */
const attempt = (fn, input) => {
  try { return fn(input); } catch { return null; }
};

/** Кодирует текст обратно в Морзе — нужен для round-trip проверки. */
const LETTER_TO_CODE = new Map(Object.entries(TABLE).map(([code, letter]) => [letter, code]));
const encode = (text) => [...text].map((ch) => LETTER_TO_CODE.get(ch)).join('');

function randomText(letters) {
  const alphabet = [...LETTER_TO_CODE.keys()];
  let out = '';
  for (let i = 0; i < letters; i++) out += alphabet[(Math.random() * alphabet.length) | 0];
  return out;
}

function runTests() {
  console.log('── ТЕСТЫ ─────────────────────────────────────────────');
  console.log('  (строки «Не понимаю знак…» — это ученическая версия: она печатает');
  console.log('   сообщение и возвращает null вместо throw. Так и задумано.)');

  const cases = [
    [RADIOGRAM, 'НАИГАЧ'],   // сама задача
    ['', ''],                // пустой вход
    ['..', 'И'],
    ['.-', 'А'],
    ['-.', 'Н'],
    ['--.', 'Г'],
    ['---.', 'Ч'],
    ['---.--..-..-.', 'ЧГАИН'],
    ['..'.repeat(50), 'И'.repeat(50)],
  ];

  const broken = [
    '-',        // тире без продолжения
    '.',        // одинокая точка
    '----',     // четыре тире, точки нет
    '-----.',   // пять тире — такой буквы нет
    '..-',      // хвост оборван
    '..x..',    // мусор
  ];

  for (const [name, fn] of SOLUTIONS) {
    for (const [input, expected] of cases) {
      assert.equal(attempt(fn, input), expected, `${name}: «${input}» → ожидалось «${expected}»`);
    }
    for (const input of broken) {
      assert.equal(attempt(fn, input), null, `${name}: «${input}» должно быть ошибкой`);
    }
    console.log(`  ✓ ${name} — базовые кейсы и битый вход`);
  }

  // Round-trip: случайный текст → код → расшифровка. 200 прогонов.
  for (let round = 0; round < 200; round++) {
    const text = randomText(1 + ((Math.random() * 40) | 0));
    const code = encode(text);
    for (const [name, fn] of SOLUTIONS) {
      assert.equal(attempt(fn, code), text, `${name}: round-trip сломался на «${text}»`);
    }
  }
  console.log('  ✓ round-trip: 200 случайных текстов, все шесть согласны');

  // Инвариант SOLID-таблицы: непрефиксный код обязан отвергаться.
  assert.throws(
    () => new PrefixFreeCodeTable({ '.': 'X', '..': 'Y' }),
    DecodeError,
    'PrefixFreeCodeTable должна ловить нарушение условия Фано',
  );
  console.log('  ✓ PrefixFreeCodeTable ловит нарушение условия Фано');

  // Типографские знаки из учебника тоже должны читаться.
  assert.equal(decodeSolid('-·· -·· --· ·- ---·'), 'НАИГАЧ');
  console.log('  ✓ нормализация «·» и пробелов');

  console.log('  ВСЁ ЗЕЛЁНОЕ\n');
}


/* ===========================================================================
 *  БЕНЧМАРК: во что реально обходится красота
 * ===========================================================================
 */
function runBenchmark(letters = 400_000, rounds = 7) {
  const text = randomText(letters);
  const code = encode(text);
  console.log(`── БЕНЧМАРК (${letters.toLocaleString('ru')} букв, ${code.length.toLocaleString('ru')} знаков) ──`);

  const best = new Map(SOLUTIONS.map(([name]) => [name, Infinity]));

  // Прогрев JIT: без него первый в списке всегда «проигрывает».
  for (const [, fn] of SOLUTIONS) { fn(code); fn(code); }

  // Раунды снаружи, реализации внутри — так эффекты GC и порядка размазываются.
  // Берём МИНИМУМ по раундам: он ближе к честной стоимости кода,
  // чем среднее, которое тянут вверх случайные паузы сборщика мусора.
  for (let r = 0; r < rounds; r++) {
    for (const [name, fn] of SOLUTIONS) {
      const t0 = process.hrtime.bigint();
      const out = fn(code);
      const t1 = process.hrtime.bigint();
      assert.equal(out, text, `${name}: неверный результат в бенчмарке`);
      best.set(name, Math.min(best.get(name), Number(t1 - t0) / 1e6));
    }
  }

  const fastest = Math.min(...best.values());
  for (const [name, ms] of best) {
    const ratio = ms / fastest;
    const bar = '█'.repeat(Math.max(1, Math.round(Math.log2(ratio) * 5) + 1));  // шкала логарифмическая
    console.log(`  ${name} ${ms.toFixed(1).padStart(7)} мс   ×${ratio.toFixed(1).padStart(5)}  ${bar}`);
  }
  console.log('  (лучшее из ' + rounds + ' раундов; цифры пляшут от машины и версии V8)');
  console.log();
}


/* ===========================================================================
 *  ОТВЕТ НА ЗАДАЧУ
 * ===========================================================================
 */
function demo() {
  console.log('── РАДИОГРАММА ───────────────────────────────────────');
  console.log(`  код:    ${RADIOGRAM.replace(/\./g, '·')}`);
  console.log(`  знаков: ${RADIOGRAM.length}`);
  for (const [name, fn] of SOLUTIONS) {
    console.log(`  ${name} → ${fn(RADIOGRAM)}`);
  }
  console.log();
  console.log('  Разбор:  Н(-·) А(·-) И(··) Г(--·) А(·-) Ч(---·)');
  console.log('  Код префиксный (условие Фано) → разбиение ЕДИНСТВЕННОЕ,');
  console.log('  перебор вариантов не нужен, хватает жадного прохода слева направо.');
  console.log();
}

if (require.main === module) {
  demo();
  runTests();
  runBenchmark();
}

module.exports = {
  TABLE, RADIOGRAM, normalize, encode,
  decodeStudent, decodeMiddle, decodeExtreme, decodeFP, decodeOOP, decodeSolid,
  MorseAlphabet, MorseDecoder,
  DecodeError, PrefixFreeCodeTable, GreedyPrefixTokenizer, MorseDecoderSolid,
};
