# Настройка Windows-компьютера ученика

План для созвона «настраиваем машину» (~30–40 минут). Цель — та же
среда, что у мак-учеников: терминал, Python, git, VS Code. Маршрут —
нативный Windows, оболочка — **Git Bash** внутри Windows Terminal:
те же `bash`, `~` и `$`, что на маке, без виртуализации, перезагрузок
и BIOS-сюрпризов. WSL2 сознательно НЕ ставим (см. внизу, почему).

PowerShell нужен дважды — на разведке и на установке Git. Дальше всё
в Git Bash, обычное окно; «от имени администратора» — только где указано.

**Скриптом:** шаги 1–5 и 7 делает `setup-windows.ps1` — та же логика, идемпотентно,
как `setup-mac.sh`. В PowerShell «от имени администратора» под учёткой ученика:

```powershell
irm https://raw.githubusercontent.com/DmitrTRC/Junior_IT/main/provisioning/setup-windows.ps1 | iex
```

Ниже — те же шаги руками: чтобы понимать, что скрипт сделал, и чинить, если нет.

## −1. До созвона: Windows 11

Windows 10 без обновлений безопасности с 14.10.2025 (платный ESU —
до 13.10.2026). Ноут ребёнка на ней не оставляем.

Проверить, что машина тянет 11: `tpm.msc` → «TPM готов к использованию»,
версия 2.0; `msinfo32` → режим BIOS: UEFI. Если TPM «не найден» —
включить в BIOS (на ThinkPad: Security → Security Chip). Процессор —
Intel 8-го поколения / Ryzen 2000 и новее.

Апгрейд: Параметры → Обновление и безопасность → Центр обновления —
предложение «Обновить до Windows 11», либо Installation Assistant с
microsoft.com/software-download/windows11. Лицензия переезжает сама.
Это 40–60 минут с перезагрузками — родитель запускает заранее, в созвон
это не влезает.

Бонус: на Win11 `winget` и Windows Terminal уже в системе.

## 0. Разведка (5 минут, PowerShell)

```powershell
winget --version
Get-ComputerInfo -Property OsName, OsVersion, CsSystemType
Get-PSDrive C
```

- `winver` — должно быть Windows 11. Если `winget` нет — обновить
  «App Installer» из Microsoft Store.
- Заодно: свободное место, не school-managed ли учётка (нужны
  админ-права), редакция Pro или Home (`winver`; влияет на раздел про
  удалённый доступ).

## 1. Git и Git Bash (PowerShell)

```powershell
winget install Git.Git --override "/VERYSILENT /NORESTART /COMPONENTS=ext,ext\shellhere,ext\guihere,gitlfs,assoc,assoc_sh,windowsterminal"
```

`--override` нужен ради последнего компонента: профиль «Git Bash» в
Windows Terminal установщик по умолчанию не ставит (проверено по
`install.iss` git-for-windows). Остальные компоненты — его же дефолт.

Дальше Windows Terminal → Параметры → Запуск → Профиль по умолчанию:
**Git Bash**. Закрыть, открыть — приглашение `$`. Если «Git Bash» в
списке нет — Добавить профиль, командная строка
`"C:\Program Files\Git\bin\bash.exe" -i -l`, начальный каталог
`%USERPROFILE%`.

⚠️ Git Bash запускать **только через Windows Terminal**. Отдельное окно
«Git Bash» из меню Пуск — это mintty, в нём Python не показывает `>>>`
(лечится `winpty python`, но проще туда не попадать).

Затем в Git Bash, как на маке:

```bash
git --version
git config --global user.name "Имя"
git config --global user.email "почта-от-github"
```

## 2. Python

```bash
winget install Python.Python.3.13
```

Новое окно терминала, проверить: `python --version`.

Команда на Windows — **`python`**, не `python3`. Чтобы шпаргалки курса
работали буква в букву, добавляем псевдоним:

```bash
echo 'alias python3=python' >> ~/.bash_profile
```

Новое окно — `python3 --version` работает. REPL выходит по `exit()`
так же.

И переменная окружения `PYTHONUTF8=1` (Параметры → Система → О системе →
Дополнительные параметры → Переменные среды, для пользователя): без неё Python,
когда его вывод идёт не в консоль, а в трубу (Code Runner в VS Code, ssh), пишет
в cp1251 и кириллица в `print` превращается в кашу.

Если `python` открывает Microsoft Store — выключить оба «псевдонима
выполнения приложений» python в Параметры → Приложения → Дополнительные
параметры приложений → Псевдонимы выполнения приложений.

## 3. VS Code

```bash
winget install Microsoft.VisualStudioCode
```

Расширения — тот же набор, что ставит `vscode-stage.sh` на маке
(этап 1 из provisioning/README.md; Python/Pylance — когда дорастём,
как у всех). Настройки из `provisioning/vscode-settings.json` перенести
руками через Ctrl+Shift+P → «Open User Settings (JSON)», и туда же —
чтобы встроенный терминал, когда до него дойдём, был тем же bash:

```json
"terminal.integrated.defaultProfile.windows": "Git Bash"
```

## 4. Рабочая папка курса

```bash
mkdir -p ~/code/junior_it
cd ~/code/junior_it
pwd
```

`pwd` покажет `/c/Users/<имя>/code/junior_it`. Проводник ту же папку
покажет как `C:\Users\<имя>\code\junior_it` — одна папка, два
написания. `~` — то же, что на маке.

## 5. Контрольный чек (аналог check-mac.sh)

Все команды из нового окна Git Bash:

```bash
echo $BASH_VERSION
winget --version
python --version
python3 --version
git --version
code --version
python -c "print('привет, курс')"
```

Семь зелёных строк — машина готова. Если что-то не находится —
сначала НОВОЕ окно терминала (PATH подхватывается при старте), потом
уже разбирательства.

## 6. Zoom (раз уж настраиваем)

Zoom-клиент с zoom.us (не из браузера), вход, тест звука/камеры,
шаринг экрана на пробу — чтобы на занятии это не съело ни минуты.

## 7. Удалённый доступ (по желанию)

Чтобы следующую техпроблему чинить самому, а не через шаринг экрана —
аналог Tailscale + SSH с мака.

```bash
winget install Tailscale.Tailscale
```

Войти своим аккаунтом, назвать устройство понятно (например
`student-dell`).

SSH-сервер, как на маке: скрипт ставит его, если перед запуском задать
`$env:JUNIOR_IT_SSH_KEY = 'ssh-ed25519 …'` — ключ ложится в
`C:\ProgramData\ssh\administrators_authorized_keys`, оболочка по SSH — PowerShell.
Штатный `Add-WindowsCapability OpenSSH.Server` качает с Windows Update и на части
машин виснет, поэтому берётся MSI `Microsoft.OpenSSH.Preview` из winget. Пока
настраиваешь удалённо — ноут не должен спать: со стандартным таймаутом он уходит
в standby и SSH отвечает минутами (скрипт выключает сон от сети).

- **Pro:** Параметры → Система → Удалённый рабочий стол → включить.
  С мака — «Windows App» из App Store, адрес — имя машины из Tailscale.
- **Home:** RDP-хоста нет. Остаётся удалённое управление в Zoom
  («Запросить управление») — уже в стеке, ничего ставить не надо.

Родителю сказать, что доступ есть и зачем — как и с маком.

## 8. Outline

Клиент — `Outline-Client.exe` с getoutline.org, тихая установка `Outline-Client.exe /S`
(под админом ложится в `Program Files (x86)\Outline`). Ключ `ss://…` — **отдельный на
ученика** в Outline Manager, как и на маке: отзывается независимо. Клиент подхватывает
ключ из буфера обмена при запуске; файл с ключом после этого удалить. В автозапуск не
ставить — для курса VPN почти не нужен.

---

## Отличия для шпаргалок (держать в голове на занятиях)

С Git Bash разница с маком ужалась до трёх строк:

| На маке | На Windows (Git Bash) |
|---|---|
| zsh, приглашение `%` | bash, приглашение `$` |
| `open .` | `explorer .` |
| `/Users/имя/...` | `/c/Users/имя/...` (в Проводнике — `C:\Users\имя\...`) |

`python3`, `pwd`/`ls`/`cd`/`mkdir`/`rm`, `clear`, `~`, стрелка вверх,
Tab — как на маке.

## Почему не WSL2 (пока)

WSL дал бы «настоящий» Linux, но требует включённую виртуализацию
(иногда — поход в BIOS), перезагрузку, гигабайты и объяснение ребёнку
двух файловых систем. Git Bash даёт те же команды и тот же `~` без
всего этого. Вернуться к WSL2 можно, когда курсу понадобится сам Linux
(ядро, права, процессы) — переход безболезнен, навыки терминала
переносятся один в один.
