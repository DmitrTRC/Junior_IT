#!/usr/bin/env bash
# Расширения VS Code по этапам курса.
#
# На старте редактор — «умный блокнот»: ноль расширений, так задумано методикой
# (см. lessons/lesson-02g-vscode). Дальше открываем слоями, по мере уроков.
#
# Запуск: bash provisioning/vscode-stage.sh <1|2|3>
#         bash provisioning/vscode-stage.sh list
set -euo pipefail

# этап 1 — когда программы начинают запускаться из редактора
STAGE1=(
  formulahendry.code-runner   # одна кнопка запускает .c, .py, .js — без терминала
  usernamehw.errorlens        # ошибка подсвечивается прямо в строке, а не в панели
)

# этап 2 — веб: живая страница и форматирование
STAGE2=(
  ritwickdey.LiveServer
  esbenp.prettier-vscode
)

# этап 3 — языковая поддержка, когда проекты подрастут
STAGE3=(
  ms-python.python
  ms-python.vscode-pylance
  ms-vscode.cpptools
  dbaeumer.vscode-eslint
)

usage() {
  cat <<TXT
Использование: bash provisioning/vscode-stage.sh <1|2|3|list>

  1  Code Runner + Error Lens        — запуск программ и видимые ошибки
  2  Live Server + Prettier          — веб-разработка
  3  Python / C++ / ESLint           — языковая поддержка

  list  показать, что стоит сейчас
TXT
}

command -v code >/dev/null 2>&1 || {
  echo "Команда code не найдена." >&2
  echo "VS Code → ⇧⌘P → Shell Command: Install 'code' command in PATH" >&2
  exit 1
}

case "${1:-}" in
  1) EXTS=("${STAGE1[@]}") ;;
  2) EXTS=("${STAGE2[@]}") ;;
  3) EXTS=("${STAGE3[@]}") ;;
  list)
    echo "Установлено сейчас:"
    code --list-extensions | sed 's/^/  /'
    exit 0
    ;;
  *) usage; exit 1 ;;
esac

INSTALLED="$(code --list-extensions)"

for e in "${EXTS[@]}"; do
  if grep -qix "$e" <<<"$INSTALLED"; then
    printf '  \033[90m·\033[0m %s — уже стоит\n' "$e"
  else
    printf '  \033[36m→\033[0m %s\n' "$e"
    code --install-extension "$e" --force >/dev/null
  fi
done

printf '\n\033[1mГотово.\033[0m Перезапусти VS Code.\n'
