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
  app.bank = await loadBank();
  document.getElementById('bank-title').textContent =
    `7 класс · глава ${app.bank.meta.chapter}. ${app.bank.meta.title}`;
  const nameInput = document.getElementById('student-name');
  nameInput.value = app.state.name;
  nameInput.addEventListener('change', () => {
    app.state = saveName(app.state, nameInput.value.trim());
  });
  renderScope(app.bank.parts);
  renderAttempts();
  document.getElementById('btn-training').addEventListener('click', () => startTraining());
  document.getElementById('btn-exam').addEventListener('click', () => startExam());
}

function startTraining() { /* Task 7 */ }
function startExam() { /* Task 7–8 */ }

init();
