import { buildTicket, checkAnswer, score, resultLine, shuffle } from './engine.js';
import { loadState, saveName, addAttempt } from './storage.js';

const BANK_BASE = '../textbook/quizzes/';
const BANK_ID = '07-1';

const app = {
  state: loadState(),
  bank: null,     // {meta, parts: [{paragraph, title, questions}]}
  mode: null,     // 'training' | 'exam'
  scope: 'all',   // 'all' | '1.1' | ...
  ticket: [],
  current: 0,
  answers: [],
  queue: [],      // тренировка: индексы вопросов к показу
};

export function showScreen(id) {
  document.querySelectorAll('.screen').forEach((s) => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

async function loadBank() {
  const manifest = await (await fetch(`${BANK_BASE}index.json`)).json();
  const meta = manifest.banks.find((b) => b.id === BANK_ID);
  const parts = await Promise.all(meta.files.map(async (name) => {
    const data = await (await fetch(BANK_BASE + name)).json();
    return { paragraph: data.paragraph, title: data.title, questions: data.questions };
  }));
  return { meta, parts };
}

function renderScope(parts) {
  const box = document.getElementById('scope-box');
  const options = [{ value: 'all', label: 'Вся глава' }].concat(
    parts.map((p) => ({ value: p.paragraph, label: `§${p.paragraph} ${p.title}` })),
  );
  for (const opt of options) {
    const label = document.createElement('label');
    const input = Object.assign(document.createElement('input'),
      { type: 'radio', name: 'scope', value: opt.value, checked: opt.value === 'all' });
    input.addEventListener('change', () => { app.scope = opt.value; });
    label.append(input, ` ${opt.label}`);
    box.append(label);
  }
}

function renderAttempts() {
  const box = document.getElementById('attempts');
  const last = app.state.attempts.slice(-3).reverse();
  box.innerHTML = last.length ? '<h3>Прошлые зачёты</h3>' : '';
  for (const a of last) {
    const p = document.createElement('p');
    p.className = a.passed ? 'attempt ok' : 'attempt';
    p.textContent = resultLine(a, '');
    box.append(p);
  }
}

async function init() {
  const trainingBtn = document.getElementById('btn-training');
  const examBtn = document.getElementById('btn-exam');
  trainingBtn.disabled = true;
  examBtn.disabled = true;
  try {
    app.bank = await loadBank();
  } catch {
    document.getElementById('bank-title').textContent =
      'Не удалось загрузить банк вопросов — обнови страницу';
    return;
  }
  document.getElementById('bank-title').textContent =
    `7 класс · глава ${app.bank.meta.chapter}. ${app.bank.meta.title}`;
  const nameInput = document.getElementById('student-name');
  nameInput.value = app.state.name;
  nameInput.addEventListener('change', () => {
    app.state = saveName(app.state, nameInput.value.trim());
  });
  renderScope(app.bank.parts);
  renderAttempts();
  trainingBtn.addEventListener('click', () => startTraining());
  examBtn.addEventListener('click', () => startExam());
  trainingBtn.disabled = false;
  examBtn.disabled = false;
}

function renderQuestion(question) {
  document.querySelector('#screen-question .card').classList.remove('right', 'wrong');
  document.getElementById('q-source').textContent =
    question.source === 'junior_it' ? 'Junior_IT' : question.source;
  document.getElementById('q-text').textContent = question.q;
  const body = document.getElementById('q-body');
  body.innerHTML = '';
  body.dataset.type = question.type;

  if (question.type === 'single' || question.type === 'multi' || question.type === 'find-error') {
    const inputType = question.type === 'multi' ? 'checkbox' : 'radio';
    question.options.forEach((text, i) => {
      const label = document.createElement('label');
      label.className = question.type === 'find-error' ? 'option code' : 'option';
      const input = Object.assign(document.createElement('input'),
        { type: inputType, name: 'opt', value: String(i) });
      label.append(input, ` ${text}`);
      body.append(label);
    });
  } else if (question.type === 'number' || question.type === 'text') {
    const input = Object.assign(document.createElement('input'), {
      type: 'text', id: 'free-answer', autocomplete: 'off',
      inputMode: question.type === 'number' ? 'numeric' : 'text',
    });
    body.append(input);
    input.focus();
  } else if (question.type === 'match') {
    question.options.left.forEach((leftText, i) => {
      const row = document.createElement('label');
      row.className = 'match-row';
      const select = document.createElement('select');
      select.dataset.row = String(i);
      select.append(new Option('—', ''));
      question.options.right.forEach((rightText, j) =>
        select.append(new Option(rightText, String(j))));
      row.append(`${leftText} `, select);
      body.append(row);
    });
  } else if (question.type === 'order') {
    const list = document.createElement('ol');
    list.id = 'order-list';
    shuffle(question.options.map((text, i) => ({ text, i })), Math.random)
      .forEach(({ text, i }) => {
        const item = document.createElement('li');
        item.dataset.index = String(i);
        const up = Object.assign(document.createElement('button'), { textContent: '↑', type: 'button' });
        const down = Object.assign(document.createElement('button'), { textContent: '↓', type: 'button' });
        up.addEventListener('click', () => item.previousElementSibling && list.insertBefore(item, item.previousElementSibling));
        down.addEventListener('click', () => item.nextElementSibling && list.insertBefore(item.nextElementSibling, item));
        item.append(Object.assign(document.createElement('span'), { textContent: text }), up, down);
        list.append(item);
      });
    body.append(list);
  }
}

function readAnswer(question) {
  const body = document.getElementById('q-body');
  switch (question.type) {
    case 'single':
    case 'find-error': {
      const checked = body.querySelector('input[name="opt"]:checked');
      return checked ? Number(checked.value) : null;
    }
    case 'multi': {
      const checked = [...body.querySelectorAll('input[name="opt"]:checked')];
      return checked.length ? checked.map((c) => Number(c.value)) : null;
    }
    case 'number':
    case 'text': {
      const value = document.getElementById('free-answer').value.trim();
      return value ? value : null;
    }
    case 'match': {
      const values = [...body.querySelectorAll('select')].map((s) => s.value);
      return values.every((v) => v !== '') ? values.map(Number) : null;
    }
    case 'order':
      return [...body.querySelectorAll('#order-list li')].map((li) => Number(li.dataset.index));
    default:
      return null;
  }
}

function trainingPool() {
  const parts = app.scope === 'all'
    ? app.bank.parts
    : app.bank.parts.filter((p) => p.paragraph === app.scope);
  return shuffle(
    parts.flatMap((p) => p.questions.map((q) => ({ ...q, paragraph: p.paragraph }))),
    Math.random,
  );
}

function startTraining() {
  app.mode = 'training';
  app.ticket = trainingPool();
  app.queue = app.ticket.map((_, i) => i);
  showScreen('screen-question');
  showTrainingQuestion();
}

function showTrainingQuestion() {
  document.getElementById('btn-answer').textContent = 'Ответить'; // не протекает текст кнопки из Зачёта
  if (!app.queue.length) {
    showScreen('screen-start');
    renderAttempts();
    return;
  }
  const question = app.ticket[app.queue[0]];
  document.getElementById('progress-label').textContent = `Осталось: ${app.queue.length}`;
  document.getElementById('progress-fill').style.width =
    `${Math.round((1 - app.queue.length / app.ticket.length) * 100)}%`;
  renderQuestion(question);
  const why = document.getElementById('q-why');
  why.hidden = true;
  toggleButtons({ answer: true, next: false });
  document.getElementById('btn-answer').onclick = () => {
    const answer = readAnswer(question);
    if (answer === null) return; // ответа нет — кнопка молчит
    const ok = checkAnswer(question, answer);
    markAnswer(ok);
    why.textContent = question.why;
    why.hidden = false;
    document.getElementById('q-body').querySelectorAll('input,select,button')
      .forEach((el) => { el.disabled = true; });
    if (ok) {
      app.queue.shift();
    } else {
      app.queue.push(app.queue.shift()); // неверный — в конец очереди
    }
    toggleButtons({ answer: false, next: true });
    document.getElementById('btn-next').onclick = () => showTrainingQuestion();
  };
}

function toggleButtons({ answer, next }) {
  document.getElementById('btn-answer').hidden = !answer;
  document.getElementById('btn-next').hidden = !next;
}

function markAnswer(ok) {
  const card = document.querySelector('#screen-question .card');
  card.classList.remove('right', 'wrong');
  card.classList.add(ok ? 'right' : 'wrong');
}

function startExam() {
  app.mode = 'exam';
  app.ticket = buildTicket(app.bank.parts, Math.random);
  app.answers = new Array(app.ticket.length).fill(null);
  app.current = 0;
  showScreen('screen-question');
  showExamQuestion();
}

function showExamQuestion() {
  const question = app.ticket[app.current];
  document.getElementById('progress-label').textContent =
    `Вопрос ${app.current + 1} из ${app.ticket.length}`;
  document.getElementById('progress-fill').style.width =
    `${Math.round((app.current / app.ticket.length) * 100)}%`;
  renderQuestion(question);
  document.getElementById('q-why').hidden = true; // в зачёте why не показываем
  toggleButtons({ answer: true, next: false });
  const btn = document.getElementById('btn-answer');
  btn.textContent = app.current + 1 === app.ticket.length ? 'Ответить и закончить' : 'Ответить';
  btn.onclick = () => {
    const answer = readAnswer(question);
    if (answer === null) return;
    app.answers[app.current] = answer;
    app.current += 1;
    if (app.current < app.ticket.length) {
      showExamQuestion();
    } else {
      finishExam();
    }
  };
}

function finishExam() {
  const result = score(app.ticket, app.answers);
  const now = new Date();
  const date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  const attempt = {
    date, // локальная дата, не UTC — toISOString отставал бы после местной полуночи
    chapter: BANK_ID,
    size: result.total,
    correct: result.correct,
    byParagraph: result.byParagraph,
    passed: result.passed,
  };
  app.state = addAttempt(app.state, attempt);
  document.getElementById('result-verdict').textContent =
    result.passed ? 'Сдано' : 'Пока нет';
  document.getElementById('result-score').textContent =
    `${result.correct} из ${result.total} (${result.percent}%)`;
  const list = document.getElementById('result-breakdown');
  list.innerHTML = '';
  for (const p of Object.keys(result.byParagraph).sort()) {
    const [ok, total] = result.byParagraph[p];
    const item = document.createElement('li');
    item.textContent = `§${p}: ${ok} из ${total}`;
    list.append(item);
  }
  const line = resultLine(attempt, app.state.name);
  document.getElementById('result-fallback')?.remove();
  document.getElementById('btn-copy').onclick = async () => {
    try {
      await navigator.clipboard.writeText(line);
      document.getElementById('btn-copy').textContent = 'Скопировано';
    } catch {
      document.getElementById('btn-copy').textContent = 'Не вышло — скопируй руками';
      document.getElementById('result-fallback')?.remove();
      const fallback = document.createElement('p');
      fallback.id = 'result-fallback';
      fallback.className = 'score-line';
      fallback.textContent = line;
      document.getElementById('btn-again').insertAdjacentElement('afterend', fallback);
    }
  };
  document.getElementById('btn-copy').textContent = 'Скопировать результат';
  document.getElementById('btn-again').onclick = () => {
    showScreen('screen-start');
    renderAttempts();
  };
  showScreen('screen-result');
}

init();
