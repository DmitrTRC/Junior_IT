import test from 'node:test';
import assert from 'node:assert/strict';
import { loadState, saveName, addAttempt } from '../../trainer/js/storage.js';

const fakeStorage = () => {
  const map = new Map();
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, String(v)),
  };
};

test('loadState: пусто и битый JSON дают чистое состояние', () => {
  const s = fakeStorage();
  assert.deepEqual(loadState(s), { name: '', attempts: [] });
  s.setItem('jit-trainer', '{оборвано');
  assert.deepEqual(loadState(s), { name: '', attempts: [] });
});

test('saveName и addAttempt: пишут и читаются обратно', () => {
  const s = fakeStorage();
  let state = loadState(s);
  state = saveName(state, 'Имя', s);
  const attempt = {
    date: '2026-09-30', chapter: '07-1', size: 15, correct: 13,
    byParagraph: { '1.1': [3, 3] }, passed: true,
  };
  state = addAttempt(state, attempt, s);
  const reloaded = loadState(s);
  assert.equal(reloaded.name, 'Имя');
  assert.deepEqual(reloaded.attempts, [attempt]);
});
