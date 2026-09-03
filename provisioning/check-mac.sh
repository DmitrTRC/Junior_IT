#!/usr/bin/env bash
# Отчёт о состоянии учебного Mac: что установлено, что настроено, что работает.
# Ничего не меняет — только читает и проверяет.
#
# Запуск: bash provisioning/check-mac.sh
set -uo pipefail   # без -e: упавшая проверка не должна ронять отчёт

export LC_ALL="${LC_ALL:-en_US.UTF-8}"

PASS=0; FAIL=0; TODO=0

# %-26s в printf считает БАЙТЫ, а кириллица — по два на букву, колонки разъезжаются.
# ${#s} считает СИМВОЛЫ при UTF-8 локали — добиваем ширину сами.
pad() {
  local s="$1" w="$2" n
  n=$(( w - ${#s} )); (( n < 0 )) && n=0
  printf '%s%*s' "$s" "$n" ""
}

hdr()  { printf '\n\033[1m%s\033[0m\n' "$1"; }
good() { PASS=$((PASS+1)); printf '  \033[32m✓\033[0m %s %s\n' "$(pad "$1" 26)" "${2:-}"; }
bad()  { FAIL=$((FAIL+1)); printf '  \033[31m✗\033[0m %s %s\n' "$(pad "$1" 26)" "${2:-нет}"; }
todo() { TODO=$((TODO+1)); printf '  \033[33m□\033[0m %s\n' "$1"; }

# подхватываем brew, если он есть, но не в PATH этой сессии
for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do
  [[ -x "$p" ]] && eval "$("$p" shellenv)" && break
done

# tool <имя> <команда> <аргумент версии>
tool() {
  local label="$1" cmd="$2" verflag="${3:---version}"
  if command -v "$cmd" >/dev/null 2>&1; then
    good "$label" "$("$cmd" "$verflag" 2>&1 | head -1)"
  else
    bad "$label"
  fi
}

# defaults_is <домен> <ключ> <ожидаемое> <подпись>
defaults_is() {
  local domain="$1" key="$2" want="$3" label="$4" got
  got="$(defaults read "$domain" "$key" 2>/dev/null || echo "—")"
  if [[ "$got" == "$want" ]]; then good "$label" "$got"; else bad "$label" "сейчас: $got, надо: $want"; fi
}

app() {
  local label="$1" path="$2"
  if [[ -d "$path" ]]; then good "$label"; else bad "$label"; fi
}

printf '\033[1mJunior_IT · проверка учебной машины\033[0m\n'
printf 'macOS %s · %s · %s · %s\n' \
  "$(sw_vers -productVersion)" "$(uname -m)" "$(whoami)" "$(date '+%Y-%m-%d %H:%M')"

hdr "Тулчейн"
if xcode-select -p >/dev/null 2>&1; then
  good "Xcode CLT" "$(xcode-select -p)"
else
  bad "Xcode CLT" "нет — C/C++ не соберётся"
fi
tool "clang"   clang   --version
tool "Homebrew" brew   --version
tool "git"     git     --version
tool "python3" python3 --version
tool "uv"      uv      --version
tool "node"    node    --version
tool "npm"     npm     --version
tool "tsc"     tsc     --version
tool "cmake"   cmake   --version
tool "ninja"   ninja   --version

hdr "Приложения"
app "VS Code"      "/Applications/Visual Studio Code.app"
app "Google Chrome" "/Applications/Google Chrome.app"
app "Zoom"         "/Applications/zoom.us.app"
app "Tailscale"    "/Applications/Tailscale.app"

hdr "Настройки macOS"
defaults_is NSGlobalDomain NSAutomaticQuoteSubstitutionEnabled 0 "смарт-кавычки выкл"
defaults_is NSGlobalDomain NSAutomaticDashSubstitutionEnabled  0 "смарт-тире выкл"
defaults_is NSGlobalDomain NSAutomaticCapitalizationEnabled    0 "автозаглавные выкл"
defaults_is NSGlobalDomain AppleShowAllExtensions              1 "расширения видны"
defaults_is com.apple.finder ShowPathbar                       1 "путь в Finder"

hdr "VS Code"
VSCODE_SETTINGS="$HOME/Library/Application Support/Code/User/settings.json"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$VSCODE_SETTINGS" ]]; then
  # settings.json — это JSONC, с комментариями; читаем тем же парсером, что и ставим
  fs="$(python3 - "$HERE" "$VSCODE_SETTINGS" <<'PYEOF'
import sys
sys.path.insert(0, sys.argv[1])
import jsonc
try:
    print(jsonc.load(sys.argv[2]).get("editor.fontSize", "не задан"))
except Exception as exc:
    print(f"файл битый: {exc}")
PYEOF
)"
  good "settings.json" "editor.fontSize = $fs"
else
  bad "settings.json"
fi

if command -v code >/dev/null 2>&1; then
  ext_list="$(code --list-extensions 2>/dev/null)"
  ext_n="$(printf '%s\n' "$ext_list" | grep -c . || true)"
  if [[ "$ext_n" -eq 0 ]]; then
    good "расширения" "нет — так и задумано на старте"
  else
    good "расширения" "штук: $ext_n"
    for e in formulahendry.code-runner usernamehw.errorlens ritwickdey.LiveServer \
             esbenp.prettier-vscode ms-python.python ms-vscode.cpptools; do
      grep -qix "$e" <<<"$ext_list" && printf '      \033[90m· %s\033[0m\n' "$e"
    done
  fi
else
  bad "команда code" "не в PATH — VS Code → ⇧⌘P → Shell Command: Install 'code' command"
fi

hdr "Живая проверка языков"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

printf 'int main(void){return 0;}\n' > "$TMP/a.c"
if clang -o "$TMP/a" "$TMP/a.c" 2>/dev/null && "$TMP/a"; then good "C собирается"; else bad "C собирается"; fi

printf '#include <iostream>\nint main(){std::cout<<"";}\n' > "$TMP/b.cpp"
if clang++ -std=c++20 -o "$TMP/b" "$TMP/b.cpp" 2>/dev/null && "$TMP/b"; then good "C++20 собирается"; else bad "C++20 собирается"; fi

if python3 -c "print('')" >/dev/null 2>&1; then good "Python запускается"; else bad "Python запускается"; fi
if command -v node >/dev/null 2>&1 && node -e "0" >/dev/null 2>&1; then good "JS запускается"; else bad "JS запускается"; fi

printf 'const n: number = 1; if (n) {}\n' > "$TMP/c.ts"
if command -v tsc >/dev/null 2>&1 && tsc --noEmit "$TMP/c.ts" 2>/dev/null; then good "TS проверяется"; else bad "TS проверяется"; fi

hdr "Диск"
df -h / | awk 'NR==2 {printf "  свободно %s из %s\n", $4, $2}'

hdr "Выдаётся только руками (macOS не даёт скриптом)"
todo "Zoom → Камера, Микрофон, Демонстрация экрана — Настройки → Конфиденциальность"
todo "Tailscale → войти в аккаунт, включить, проверить имя устройства"
todo "Общий доступ → Удалённый вход (SSH), если нужен удалённый доступ"
todo "Детский Apple ID в семейной группе родителя"

printf '\n\033[1mИтого: \033[32m%d ок\033[0m, \033[31m%d проблем\033[0m, \033[33m%d вручную\033[0m\n\n' "$PASS" "$FAIL" "$TODO"
[[ "$FAIL" -eq 0 ]]
