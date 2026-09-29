<#
Настройка Windows-компьютера ученика — скриптовая версия setup-windows.md.
Идемпотентно: каждый шаг сначала проверяет, потом пишет. Гонять можно сколько угодно.

Запуск — PowerShell «от имени администратора», под учёткой ученика (per-user
установки лягут в её профиль):

  irm https://raw.githubusercontent.com/DmitrTRC/Junior_IT/main/provisioning/setup-windows.ps1 | iex

Удалённый доступ (sshd + RDP) включается, если перед запуском задать публичный ключ:

  $env:JUNIOR_IT_SSH_KEY = 'ssh-ed25519 AAAA… mac->win'

Win11 Pro: RDP-хост включается тоже. Home — только sshd.
#>

$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$utf8 = New-Object Text.UTF8Encoding $false
$wingetArgs = @('--accept-source-agreements', '--accept-package-agreements', '--silent')
$gitBashGuid = '{2ece5bfe-50ed-5f3a-ab87-5cd4baafed2b}'   # профиль из фрагмента Git for Windows
$rawBase = 'https://raw.githubusercontent.com/DmitrTRC/Junior_IT/main/provisioning'

function Step($name) { Write-Host "== $name" -ForegroundColor Cyan }
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Write-Host 'Нужно окно «от имени администратора».' -ForegroundColor Red; return }
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Write-Host 'Нет winget — обновить «App Installer» из Microsoft Store и запустить снова.' -ForegroundColor Red; return
}

# ---------- 1. Пакеты ----------
Step 'winget: Git, Python, VS Code, Zoom, Tailscale'
# Профиль «Git Bash» для Windows Terminal (компонент windowsterminal) установщик Git по
# умолчанию не ставит — поэтому явный список компонентов; остальные — его же дефолт.
winget install Git.Git @wingetArgs --override '/VERYSILENT /NORESTART /COMPONENTS=ext,ext\shellhere,ext\guihere,gitlfs,assoc,assoc_sh,windowsterminal'
winget install Python.Python.3.13 @wingetArgs
winget install Microsoft.VisualStudioCode @wingetArgs
winget install Zoom.Zoom @wingetArgs
winget install Tailscale.Tailscale @wingetArgs
if (-not (Get-AppxPackage Microsoft.WindowsTerminal -ErrorAction SilentlyContinue)) {
  winget install Microsoft.WindowsTerminal @wingetArgs
}
Refresh-Path

# ---------- 2. Windows Terminal: Git Bash по умолчанию, шрифт 15 ----------
Step 'Windows Terminal'
$wtDir = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState"
$wt = "$wtDir\settings.json"
if (Test-Path $wt) {
  $cfg = Get-Content $wt -Raw | ConvertFrom-Json
  if ($cfg.defaultProfile -ne $gitBashGuid) {
    Copy-Item $wt "$wt.bak" -Force
    $cfg.defaultProfile = $gitBashGuid
    if (-not $cfg.profiles.defaults.PSObject.Properties['font']) {
      $cfg.profiles.defaults | Add-Member -NotePropertyName font -NotePropertyValue ([pscustomobject]@{ size = 15 })
    }
    [IO.File]::WriteAllText($wt, ($cfg | ConvertTo-Json -Depth 20), $utf8)
    'defaultProfile -> Git Bash (бэкап settings.json.bak)'
  } else { 'уже Git Bash' }
} else {
  # терминал ещё ни разу не открывали — минимальный файл, остальное WT дополнит сам
  New-Item -ItemType Directory -Force $wtDir | Out-Null
  [IO.File]::WriteAllText($wt, "{`n  `"defaultProfile`": `"$gitBashGuid`",`n  `"profiles`": { `"defaults`": { `"font`": { `"size`": 15 } } }`n}`n", $utf8)
  'settings.json создан'
}

# ---------- 3. bash: python3 как на маке ----------
Step 'bash profile'
$bp = "$env:USERPROFILE\.bash_profile"
if (-not (Test-Path $bp) -or -not (Select-String -Path $bp -SimpleMatch 'alias python3=python' -Quiet)) {
  # только LF: CRLF превращает алиас в "python\r"
  [IO.File]::AppendAllText($bp, "alias python3=python`n", $utf8)
  'alias python3=python'
} else { 'алиас уже есть' }

# ---------- 4. VS Code: настройки + расширения этапа 1 ----------
Step 'VS Code'
$vsDir = "$env:APPDATA\Code\User"
$vs = "$vsDir\settings.json"
if (-not (Test-Path $vs)) {
  $local = Join-Path $PSScriptRoot 'vscode-settings.json'
  $json = if ($PSScriptRoot -and (Test-Path $local)) { Get-Content $local -Raw } else { irm "$rawBase/vscode-settings.json" }
  $settings = $json | ConvertFrom-Json
  $settings | Add-Member -NotePropertyName 'terminal.integrated.defaultProfile.windows' -NotePropertyValue 'Git Bash'
  New-Item -ItemType Directory -Force $vsDir | Out-Null
  [IO.File]::WriteAllText($vs, ($settings | ConvertTo-Json), $utf8)
  'settings.json создан'
} else { 'settings.json уже есть — не трогаю' }
$have = & code --list-extensions 2>$null
foreach ($ext in 'formulahendry.code-runner', 'usernamehw.errorlens') {
  if ($have -contains $ext) { "$ext уже" } else { & code --install-extension $ext 2>&1 | Select-Object -Last 1 }
}

# ---------- 5. Рабочая папка, расширения файлов, кодировка ----------
Step 'папка курса, Проводник, PYTHONUTF8'
$course = "$env:USERPROFILE\code\junior_it"
if (-not (Test-Path $course)) { New-Item -ItemType Directory -Force $course | Out-Null; "создана $course" }
$adv = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'
if ((Get-ItemPropertyValue $adv HideFileExt) -ne 0) { Set-ItemProperty $adv HideFileExt 0; 'расширения файлов видны (после перезахода)' }
# без этого Python в pipe (Code Runner, ssh) пишет в cp1251 и кириллица превращается в кашу
if ([Environment]::GetEnvironmentVariable('PYTHONUTF8', 'User') -ne '1') { [Environment]::SetEnvironmentVariable('PYTHONUTF8', '1', 'User'); 'PYTHONUTF8=1' }

# ---------- 6. Удалённый доступ (по ключу) ----------
$key = $env:JUNIOR_IT_SSH_KEY
if ($key) {
  Step 'sshd + RDP'
  if (-not (Get-Service sshd -ErrorAction SilentlyContinue)) {
    # Add-WindowsCapability OpenSSH.Server качает с Windows Update и на части машин виснет — MSI из winget надёжнее
    winget install Microsoft.OpenSSH.Preview @wingetArgs
  }
  Set-Service sshd -StartupType Automatic; Start-Service sshd
  New-ItemProperty -Path HKLM:\SOFTWARE\OpenSSH -Name DefaultShell -Value "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force | Out-Null
  if (-not (Get-NetFirewallRule -Name OpenSSH-Server-In-TCP -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name OpenSSH-Server-In-TCP -DisplayName 'OpenSSH Server (sshd)' -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow | Out-Null
  }
  $ak = 'C:\ProgramData\ssh\administrators_authorized_keys'
  if (-not (Test-Path $ak) -or -not (Select-String -Path $ak -SimpleMatch $key -Quiet)) { Add-Content -Path $ak -Value $key -Encoding Ascii }
  icacls $ak /inheritance:r /grant 'Administrators:F' /grant 'SYSTEM:F' | Out-Null
  $ts = 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server'
  if ((Get-CimInstance Win32_OperatingSystem).Caption -match 'Pro|Enterprise|Education') {
    Set-ItemProperty $ts fDenyTSConnections 0
    Enable-NetFirewallRule -Group '@FirewallAPI.dll,-28752'
    'RDP включён'
  }
  # пока настраиваем удалённо, ноут не должен засыпать — иначе SSH отвечает минутами
  powercfg /change standby-timeout-ac 0 | Out-Null
  'sshd: ' + (Get-Service sshd).Status
}

# ---------- 7. Проверка (аналог check-mac.sh) ----------
Step 'проверка'
$bash = 'C:\Program Files\Git\bin\bash.exe'
'python:  ' + (& python --version 2>&1)
'python3: ' + (& $bash -l -i -c 'python3 --version' 2>&1 | Select-Object -Last 1)
'git:     ' + (& git --version 2>&1)
'code:    ' + (& code --version 2>&1 | Select-Object -First 1)
'bash:    ' + (& $bash -c 'echo $BASH_VERSION' 2>&1)
'nano:    ' + (& $bash -c 'nano --version | head -1' 2>&1)
'zoom:    ' + ((Test-Path "$env:ProgramFiles\Zoom\bin\Zoom.exe") -or (Test-Path "$env:APPDATA\Zoom\bin\Zoom.exe"))
'print:   ' + (& python -c "print('привет, курс')" 2>&1)
Write-Host 'Руками остаётся: git config user.name/email, вход в Tailscale и Zoom, шаринг экрана на пробу.' -ForegroundColor Yellow
