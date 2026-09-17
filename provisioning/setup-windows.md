# Настройка Windows-компьютера ученика

План для созвона «настраиваем машину» (~30–40 минут). Цель — та же
среда, что у мак-учеников: терминал, Python, git, VS Code. Маршрут —
нативный Windows: надёжно, без перезагрузок и BIOS-сюрпризов. WSL2
сознательно НЕ ставим (см. внизу, почему).

Все команды — в PowerShell «от имени администратора» только там, где
указано; остальное — обычное окно.

## 0. Разведка (5 минут)

```powershell
winget --version
Get-ComputerInfo -Property OsName, OsVersion, CsSystemType
```

- `winget` есть на Windows 10 2004+ и любой Windows 11. Если нет —
  обновить «App Installer» из Microsoft Store, это быстрее ручных
  инсталляторов.
- Заодно: сколько свободного места (`Get-PSDrive C`), не school-managed
  ли учётка (админ-права нужны).

## 1. Терминал

Windows Terminal: на Win11 уже стоит; на Win10 —

```powershell
winget install Microsoft.WindowsTerminal
```

Работаем в PowerShell внутри Windows Terminal. Хорошая новость для
шпаргалок курса: `pwd`, `ls`, `cd`, `mkdir`, `rm`, `cat` в PowerShell
работают как алиасы — devops-шпаргалка почти не меняется.

## 2. Python

```powershell
winget install Python.Python.3.13
```

Закрыть и открыть терминал заново, проверить: `python --version`.

⚠️ Главное отличие от мака: команда — **`python`**, не `python3`
(и REPL выходит по `exit()` так же). Если `python` открывает Microsoft
Store — выключить оба «псевдонима выполнения приложений» python в
Settings → Apps → Advanced app settings → App execution aliases.

## 3. Git

```powershell
winget install Git.Git
```

Новый терминал, проверить `git --version`, затем как на маке:

```powershell
git config --global user.name "Имя"
git config --global user.email "почта-от-github"
```

## 4. VS Code

```powershell
winget install Microsoft.VisualStudioCode
```

Расширения — тот же набор, что ставит `vscode-stage.sh` на маке
(этап 1 из provisioning/README.md; Python/Pylance — когда дорастём,
как у всех). Настройки из `provisioning/vscode-settings.json` можно
перенести руками через Ctrl+Shift+P → «Open User Settings (JSON)».

## 5. Рабочая папка курса

```powershell
mkdir ~\code\junior_it
cd ~\code\junior_it
```

Путь в объяснениях: `C:\Users\<имя>\code\junior_it` — то же самое,
что `~/code/junior_it` на маке, тильда работает и в PowerShell.

## 6. Контрольный чек (аналог check-mac.sh)

Все команды из обычного нового окна терминала:

```powershell
winget --version
python --version
git --version
code --version
python -c "print('привет, курс')"
```

Пять зелёных строк — машина готова. Если что-то не находится —
сначала НОВОЕ окно терминала (PATH подхватывается при старте), потом
уже разбирательства.

## 7. Zoom (раз уж настраиваем)

Zoom-клиент с zoom.us (не из браузера), вход, тест звука/камеры,
шаринг экрана на пробу — чтобы на занятии это не съело ни минуты.

---

## Отличия для шпаргалок (держать в голове на занятиях)

| На маке | На Windows у Маши |
|---|---|
| `python3` | `python` |
| zsh, приглашение `%` | PowerShell, приглашение `>` |
| `open .` | `explorer .` |
| `/Users/имя/...` | `C:\Users\имя\...` (но `~` работает) |
| `clear` | `clear` работает (алиас `cls`) |

Остальное из devops-01 (pwd/ls/cd/mkdir/rm, стрелка вверх, Tab) —
без изменений.

## Почему не WSL2 (пока)

WSL дал бы «настоящий» Linux-терминал, но требует включённую
виртуализацию (иногда — поход в BIOS), перезагрузку, гигабайты и
объяснение ребёнку двух файловых систем. После занятия, наполовину
съеденного техпроблемами, приоритет — надёжность. Вернуться к WSL2
можно, когда трек devops дойдёт до Linux-специфики; переход безболезнен,
навыки терминала переносятся один в один.
