// Чистая логика тренажёра: без DOM, без fetch, без localStorage.
// rng передаётся параметром — в тестах детерминированный.

export function normalizeText(s) {
  return s.trim().toLowerCase().replaceAll('ё', 'е').replace(/\s+/g, ' ');
}

function sameSequence(a, b) {
  return a.length === b.length && a.every((v, i) => v === b[i]);
}

export function checkAnswer(question, answer) {
  switch (question.type) {
    case 'single':
    case 'find-error':
      return answer === question.answer;
    case 'multi': {
      const given = [...answer].sort((x, y) => x - y);
      const right = [...question.answer].sort((x, y) => x - y);
      return sameSequence(given, right);
    }
    case 'number':
      return Number(String(answer).trim().replace(',', '.')) === question.answer;
    case 'text': {
      const accepted = Array.isArray(question.answer) ? question.answer : [question.answer];
      return accepted.some((v) => normalizeText(v) === normalizeText(String(answer)));
    }
    case 'match':
    case 'order':
      return sameSequence(answer, question.answer);
    default:
      throw new Error(`неизвестный тип вопроса: ${question.type}`);
  }
}

export function shuffle(items, rng) {
  const arr = [...items];
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export function buildTicket(bank, rng, perParagraph = 3) {
  const picked = [];
  for (const part of bank) {
    if (part.questions.length < perParagraph) {
      throw new Error(`в параграфе ${part.paragraph} меньше ${perParagraph} вопросов`);
    }
    for (const question of shuffle(part.questions, rng).slice(0, perParagraph)) {
      picked.push({ ...question, paragraph: part.paragraph });
    }
  }
  return shuffle(picked, rng);
}

export function score(ticket, answers) {
  const byParagraph = {};
  let correct = 0;
  ticket.forEach((question, i) => {
    const given = answers[i];
    const ok = given !== null && given !== undefined && given !== '' && checkAnswer(question, given);
    const bucket = byParagraph[question.paragraph] ?? (byParagraph[question.paragraph] = [0, 0]);
    bucket[1] += 1;
    if (ok) {
      bucket[0] += 1;
      correct += 1;
    }
  });
  const total = ticket.length;
  return {
    correct,
    total,
    percent: Math.round((correct / total) * 100),
    byParagraph,
    passed: correct >= Math.ceil(total * 0.8),
  };
}

export function resultLine(attempt, name) {
  const [grade, chapter] = attempt.chapter.split('-');
  const paragraphs = Object.keys(attempt.byParagraph).sort().map(
    (p) => `§${p} ${attempt.byParagraph[p][0]}/${attempt.byParagraph[p][1]}`,
  );
  const [y, m, d] = attempt.date.split('-');
  const pieces = [
    'Зачёт',
    `${Number(grade)} кл, глава ${Number(chapter)}`,
    `${attempt.correct}/${attempt.size} (${Math.round((attempt.correct / attempt.size) * 100)}%)`,
    attempt.passed ? 'сдано' : 'пока нет',
    ...paragraphs,
    `${d}.${m}.${y}`,
  ];
  if (name) {
    pieces.push(name);
  }
  return pieces.join(' · ');
}
