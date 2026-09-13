import test from 'node:test';
import assert from 'node:assert/strict';
import {
  normalizeText, checkAnswer, shuffle, buildTicket, score, resultLine,
} from '../../trainer/js/engine.js';

// Детерминированный rng: выдаёт значения по кругу.
const cycleRng = (values) => {
  let i = 0;
  return () => values[i++ % values.length];
};

const q = (over = {}) => ({
  id: '07-1-01', source: 'x', type: 'single', q: '?',
  options: ['а', 'б', 'в'], answer: 1, why: 'w', terms: [], ...over,
});

test('normalizeText: регистр, ё, пробелы', () => {
  assert.equal(normalizeText('  Полёт  Нормальный '), 'полет нормальный');
});

test('single: верно и неверно', () => {
  assert.equal(checkAnswer(q(), 1), true);
  assert.equal(checkAnswer(q(), 0), false);
});

test('find-error: как single', () => {
  assert.equal(checkAnswer(q({ type: 'find-error' }), 1), true);
});

test('multi: порядок выбора не важен, состав важен', () => {
  const question = q({ type: 'multi', answer: [0, 2] });
  assert.equal(checkAnswer(question, [2, 0]), true);
  assert.equal(checkAnswer(question, [0]), false);
  assert.equal(checkAnswer(question, [0, 1, 2]), false);
});

test('number: строка с запятой равна числу', () => {
  const question = q({ type: 'number', options: undefined, answer: 2048 });
  assert.equal(checkAnswer(question, '2048'), true);
  assert.equal(checkAnswer(question, ' 2048 '), true);
  assert.equal(checkAnswer(question, '2,5'), false);
  assert.equal(checkAnswer(q({ type: 'number', options: undefined, answer: 2.5 }), '2,5'), true);
});

test('text: нормализация и список допустимых', () => {
  const question = q({ type: 'text', options: undefined, answer: ['бит', 'bit'] });
  assert.equal(checkAnswer(question, '  БИТ '), true);
  assert.equal(checkAnswer(question, 'байт'), false);
});

test('match и order: точное совпадение последовательности', () => {
  const m = q({ type: 'match', options: { left: ['а', 'б'], right: ['x', 'y'] }, answer: [1, 0] });
  assert.equal(checkAnswer(m, [1, 0]), true);
  assert.equal(checkAnswer(m, [0, 1]), false);
  const o = q({ type: 'order', answer: [2, 0, 1] });
  assert.equal(checkAnswer(o, [2, 0, 1]), true);
  assert.equal(checkAnswer(o, [0, 1, 2]), false);
});

test('shuffle: не мутирует и детерминирован при данном rng', () => {
  const src = [1, 2, 3, 4];
  const out = shuffle(src, cycleRng([0]));
  assert.deepEqual(src, [1, 2, 3, 4]);
  assert.equal(out.length, 4);
  assert.deepEqual([...out].sort(), [1, 2, 3, 4]);
});

test('buildTicket: 3 с параграфа, поле paragraph, ошибка при нехватке', () => {
  const bank = [
    { paragraph: '1.1', questions: [q({ id: 'a1' }), q({ id: 'a2' }), q({ id: 'a3' }), q({ id: 'a4' })] },
    { paragraph: '1.2', questions: [q({ id: 'b1' }), q({ id: 'b2' }), q({ id: 'b3' })] },
  ];
  const ticket = buildTicket(bank, cycleRng([0.1, 0.5, 0.9]));
  assert.equal(ticket.length, 6);
  assert.equal(ticket.filter((t) => t.paragraph === '1.1').length, 3);
  assert.equal(ticket.filter((t) => t.paragraph === '1.2').length, 3);
  assert.throws(() => buildTicket([{ paragraph: '1.3', questions: [q()] }], cycleRng([0])));
});

test('score: порог 80 процентов с округлением вверх', () => {
  const ticket = Array.from({ length: 5 }, (_, i) =>
    ({ ...q({ id: `t${i}` }), paragraph: i < 3 ? '1.1' : '1.2' }));
  // 4 из 5 верных: ceil(5 * 0.8) = 4 — сдано
  const s = score(ticket, [1, 1, 1, 1, 0]);
  assert.equal(s.correct, 4);
  assert.equal(s.passed, true);
  assert.deepEqual(s.byParagraph, { '1.1': [3, 3], '1.2': [1, 2] });
  // 3 из 5 — не сдано; null = нет ответа
  assert.equal(score(ticket, [1, 1, 1, null, 0]).passed, false);
});

test('score: пустая строка не засчитывается даже для number с answer 0', () => {
  const zero = { ...q({ type: 'number', options: undefined, answer: 0 }), paragraph: '1.5' };
  assert.equal(score([zero], ['']).correct, 0);
});

test('resultLine: формат строки для MAX', () => {
  const attempt = {
    date: '2026-09-30', chapter: '07-1', size: 15, correct: 13,
    byParagraph: { '1.2': [2, 3], '1.1': [3, 3] }, passed: true,
  };
  assert.equal(
    resultLine(attempt, 'Имя'),
    'Зачёт · 7 кл, глава 1 · 13/15 (87%) · сдано · §1.1 3/3 · §1.2 2/3 · 30.09.2026 · Имя',
  );
  assert.ok(resultLine({ ...attempt, passed: false }, '').endsWith('30.09.2026'));
  assert.ok(resultLine({ ...attempt, passed: false }, '').includes('пока нет'));
});
