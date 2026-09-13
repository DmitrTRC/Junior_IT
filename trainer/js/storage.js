const KEY = 'jit-trainer';

export function loadState(storage = window.localStorage) {
  try {
    const raw = storage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (parsed && typeof parsed === 'object') {
      return {
        name: typeof parsed.name === 'string' ? parsed.name : '',
        attempts: Array.isArray(parsed.attempts) ? parsed.attempts : [],
      };
    }
  } catch {
    // битые данные не повод падать — начинаем с чистого состояния
  }
  return { name: '', attempts: [] };
}

function persist(state, storage) {
  storage.setItem(KEY, JSON.stringify(state));
  return state;
}

export function saveName(state, name, storage = window.localStorage) {
  return persist({ ...state, name }, storage);
}

export function addAttempt(state, attempt, storage = window.localStorage) {
  return persist({ ...state, attempts: [...state.attempts, attempt] }, storage);
}
