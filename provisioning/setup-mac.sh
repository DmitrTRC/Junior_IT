#!/usr/bin/env bash
# Провижининг учебного Mac для ученика Junior_IT.
# Ставит тулчейн C/C++, Python, JS/TS + приложения и правит настройки macOS,
# на которых спотыкаются новички.
#
# Запуск:      bash provisioning/setup-mac.sh
# Прогон вхолостую: DRY_RUN=1 bash provisioning/setup-mac.sh
#
# Скрипт идемпотентный: гонять можно сколько угодно раз, уже сделанное пропускается.
set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
STEP=0
TOTAL=8

# ── вспомогательное ─────────────────────────────────────────────────────────

step()  { STEP=$((STEP + 1)); printf '\n\033[1m[%d/%d] %s\033[0m\n' "$STEP" "$TOTAL" "$1"; }
ok()    { printf '  \033[32m✓\033[0m %s\n' "$1"; }
skip()  { printf '  \033[90m·\033[0m %s\n' "$1"; }
warn()  { printf '  \033[33m!\033[0m %s\n' "$1"; }
die()   { printf '\n\033[31m✗ %s\033[0m\n' "$1" >&2; exit 1; }

# run <описание> <команда...> — выполняет или печатает, если DRY_RUN=1
run() {
  local desc="$1"; shift
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '  \033[36m→\033[0m %s\n    \033[90m%s\033[0m\n' "$desc" "$*"
  else
    printf '  \033[36m→\033[0m %s\n' "$desc"
    "$@"
  fi
}

have() { command -v "$1" >/dev/null 2>&1; }

# ── 1. Проверки окружения ───────────────────────────────────────────────────

step "Проверка окружения"

[[ "$(uname -s)" == "Darwin" ]] || die "Это скрипт для macOS."
[[ "$(uname -m)" == "arm64" ]]  || warn "Не Apple Silicon — Homebrew встанет в /usr/local, пути в отчёте будут другие."
[[ "$EUID" -ne 0 ]]             || die "Не запускай через sudo. Скрипт сам попросит пароль там, где нужно."

ok "macOS $(sw_vers -productVersion), $(uname -m), пользователь $(whoami)"

if [[ "$DRY_RUN" == "1" ]]; then
  warn "DRY_RUN — ничего не будет изменено, только показаны команды."
else
  printf '\n  Сейчас на этой машине будет установлен тулчейн разработчика.\n'
  printf '  Продолжить? [y/N] '
  read -r answer
  [[ "$answer" =~ ^[Yy]$ ]] || die "Отменено."
fi

# ── 2. Xcode Command Line Tools (компиляторы C/C++) ─────────────────────────

step "Xcode Command Line Tools — clang, clang++, lldb, make, git"

if xcode-select -p >/dev/null 2>&1; then
  skip "уже установлены: $(xcode-select -p)"
else
  warn "Откроется окно установки. Дождись окончания и запусти скрипт заново."
  run "запуск установщика" xcode-select --install
  [[ "$DRY_RUN" == "1" ]] || exit 0
fi

# ── 3. Homebrew ─────────────────────────────────────────────────────────────

step "Homebrew"

BREW_PREFIX="/opt/homebrew"
[[ "$(uname -m)" == "arm64" ]] || BREW_PREFIX="/usr/local"

if have brew; then
  skip "уже установлен: $(brew --prefix)"
else
  warn "Установщик Homebrew попросит пароль администратора."
  run "установка Homebrew" /bin/bash -c \
    "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# PATH в ~/.zprofile — чтобы brew работал в новых сессиях терминала
ZPROFILE="$HOME/.zprofile"
if [[ -f "$ZPROFILE" ]] && grep -q 'brew shellenv' "$ZPROFILE"; then
  skip "PATH уже прописан в ~/.zprofile"
else
  run "прописать brew в ~/.zprofile" \
    bash -c "echo 'eval \"\$($BREW_PREFIX/bin/brew shellenv)\"' >> '$ZPROFILE'"
fi

# подхватываем brew в текущей сессии
if [[ -x "$BREW_PREFIX/bin/brew" ]]; then
  eval "$("$BREW_PREFIX/bin/brew" shellenv)"
fi

# ── 4. Пакеты: Python, Node, сборка C/C++ ───────────────────────────────────

step "Пакеты разработчика"

FORMULAE=(
  python@3.13   # Python
  uv            # быстрый менеджер пакетов и venv для Python
  node          # JS + npm
  cmake         # сборка C/C++
  ninja         # быстрый бэкенд сборки
  git           # свежее системного
)

for f in "${FORMULAE[@]}"; do
  if brew list --formula "$f" >/dev/null 2>&1; then
    skip "$f"
  else
    run "brew install $f" brew install "$f"
  fi
done

# ── 5. TypeScript ───────────────────────────────────────────────────────────

step "TypeScript"

if have npm; then
  for pkg in typescript tsx; do
    if npm ls -g --depth=0 "$pkg" >/dev/null 2>&1; then
      skip "$pkg"
    else
      run "npm install -g $pkg" npm install -g "$pkg"
    fi
  done
else
  warn "npm не найден — пропускаю. Запусти скрипт заново после установки node."
fi

# ── 6. Приложения ───────────────────────────────────────────────────────────

step "Приложения"

# "имя каска|путь к .app" — приложение могли поставить и руками, мимо brew
CASKS=(
  "visual-studio-code|/Applications/Visual Studio Code.app"
  "google-chrome|/Applications/Google Chrome.app"
  "zoom|/Applications/zoom.us.app"
)

for entry in "${CASKS[@]}"; do
  c="${entry%%|*}"
  apppath="${entry#*|}"
  if brew list --cask "$c" >/dev/null 2>&1; then
    skip "$c"
  elif [[ -d "$apppath" ]]; then
    skip "$c — уже стоит мимо brew"
  else
    run "brew install --cask $c" brew install --cask "$c"
  fi
done

# Tailscale — имя каска у Apple Silicon-версии менялось, пробуем оба
if brew list --cask tailscale-app >/dev/null 2>&1 || brew list --cask tailscale >/dev/null 2>&1 \
   || [[ -d "/Applications/Tailscale.app" ]]; then
  skip "tailscale"
elif [[ "$DRY_RUN" == "1" ]]; then
  printf '  \033[36m→\033[0m установка Tailscale\n    \033[90mbrew install --cask tailscale-app || tailscale\033[0m\n'
else
  printf '  \033[36m→\033[0m установка Tailscale\n'
  brew install --cask tailscale-app 2>/dev/null \
    || brew install --cask tailscale 2>/dev/null \
    || warn "Tailscale не встал — поставь вручную с tailscale.com"
fi

# ── 7. Настройки macOS ──────────────────────────────────────────────────────

step "Настройки macOS под написание кода"

# Смарт-кавычки превращают " в «ёлочки» и ломают код — главный убийца новичков
run "выключить смарт-кавычки"  defaults write NSGlobalDomain NSAutomaticQuoteSubstitutionEnabled -bool false
run "выключить смарт-тире"     defaults write NSGlobalDomain NSAutomaticDashSubstitutionEnabled  -bool false
run "выключить автозаглавные"  defaults write NSGlobalDomain NSAutomaticCapitalizationEnabled    -bool false
run "выключить автозамену"     defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false

# Без расширений не виден смысл урока про .js / .html
run "показывать расширения файлов" defaults write NSGlobalDomain AppleShowAllExtensions -bool true
run "показывать путь в Finder"     defaults write com.apple.finder ShowPathbar -bool true

# Удержание клавиши повторяет символ, а не открывает меню с ударениями
run "удержание клавиши = повтор" defaults write NSGlobalDomain ApplePressAndHoldEnabled -bool false
run "быстрый автоповтор"         defaults write NSGlobalDomain KeyRepeat -int 2
run "короткая задержка повтора"   defaults write NSGlobalDomain InitialKeyRepeat -int 15

run "перезапустить Finder" killall Finder

# ── 8. Настройки VS Code ────────────────────────────────────────────────────

step "Настройки VS Code"

VSCODE_USER="$HOME/Library/Application Support/Code/User"
VSCODE_SETTINGS="$VSCODE_USER/settings.json"
VSCODE_DEFAULTS="$(dirname "${BASH_SOURCE[0]}")/vscode-settings.json"

[[ -f "$VSCODE_DEFAULTS" ]] || die "Не найден $VSCODE_DEFAULTS"

if [[ "$DRY_RUN" == "1" ]]; then
  printf '  \033[36m→\033[0m записать %s\n' "$VSCODE_SETTINGS"
else
  mkdir -p "$VSCODE_USER"
  if [[ -f "$VSCODE_SETTINGS" ]]; then
    cp "$VSCODE_SETTINGS" "$VSCODE_SETTINGS.bak.$(date +%Y%m%d%H%M%S)"
    # мержим: наши ключи поверх существующих, чужие настройки не трогаем
    python3 "$(dirname "${BASH_SOURCE[0]}")/merge-json.py" "$VSCODE_SETTINGS" "$VSCODE_DEFAULTS"
    ok "настройки смержены (бэкап рядом)"
  else
    cp "$VSCODE_DEFAULTS" "$VSCODE_SETTINGS"
    ok "настройки записаны"
  fi
fi

# ── Итог ────────────────────────────────────────────────────────────────────

printf '\n\033[1mГотово.\033[0m\n'
printf 'Проверить результат:  bash provisioning/check-mac.sh\n'
printf 'Расширения VS Code:   bash provisioning/vscode-stage.sh 1\n\n'
printf 'Руками останется выдать разрешения Zoom (камера, микрофон, демонстрация\n'
printf 'экрана) — macOS не даёт сделать это скриптом. Подробности в README.\n'
