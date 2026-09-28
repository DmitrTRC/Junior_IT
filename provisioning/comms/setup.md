# Развёртывание comms на Маке

## 1. SSH-ключ к HP

```bash
ssh-keygen -t ed25519 -f ~/.ssh/junior_it_hp -N ""
```

Публичный ключ (`~/.ssh/junior_it_hp.pub`) — в `/srv/courier/.ssh/authorized_keys` на HP
(см. `provisioning/courier/setup.md`, шаг 2).

В `~/.ssh/config` — алиас:

```
Host hp
    HostName <IP или hostname HP>
    User courier
    IdentityFile ~/.ssh/junior_it_hp
```

Проверка:

```bash
ssh hp true
```

## 2. Конфиг

```bash
mkdir -p ~/.junior_it
cp provisioning/comms/comms.toml.example ~/.junior_it/comms.toml
```

Поправить `hp_host = "hp"` (алиас из шага 1 уже несёт `User courier`, повторять его
в `comms.toml` не нужно).

## 3. Автозапуск

Первый тик руками, до автозапуска — увидеть ошибки конфигурации сразу, а не в логе:

```bash
cd tools && .venv/bin/python -m comms.tick --once
```

Затем — в launchd:

```bash
cp provisioning/comms/com.juniorit.comms.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.juniorit.comms.plist
```

Живой ли тик — смотри лог `~/Library/Logs/junior-it-comms.log`, либо без обращения к
HP: `cd tools && .venv/bin/python -m comms.tick --dry-run` (очередь, ожидающие
кнопки, время последнего тика) и `tools/.venv/bin/python tools/comms/cli.py status`
(почтальон, очереди, люди без Telegram).

## 4. Коды регистрации

```bash
tools/.venv/bin/python tools/comms/cli.py code <student>
tools/.venv/bin/python tools/comms/cli.py code <student> --parent
```

Код уходит на HP следующим тиком и живёт в очереди, пока ученик или родитель не
пришлёт его боту в Telegram (`/start <код>`). Выдавать код лично, не через общий чат.

## 5. GitHub

Один раз — шаблон для домашек (`<owner>` — аккаунт Димаса, `DmitrTRC`):

```bash
gh repo create <owner>/junior-it-homework-template --private --add-readme --clone
cd junior-it-homework-template
mkdir hw
touch hw/.gitkeep
git add hw/.gitkeep
git commit -m "hw skeleton"
git push
gh api -X PATCH repos/<owner>/junior-it-homework-template -F is_template=true
```

На каждого ученика репозиторий заводит Димас у себя (`DmitrTRC`), а ученика
добавляет коллаборатором с правом push — так опрос не зависит от детских
аккаунтов. `<nick>` — ник ученика в репозиториях, `<student-login>` — его логин
на GitHub:

```bash
gh repo create DmitrTRC/jit-hw-<nick> --private --template DmitrTRC/junior-it-homework-template
gh api -X PUT repos/DmitrTRC/jit-hw-<nick>/collaborators/<student-login> -f permission=push
tools/.venv/bin/python tools/comms/cli.py github <student> DmitrTRC/jit-hw-<nick>
```

Порядок важен: ученик принимает приглашение (письмо от GitHub или
https://github.com/notifications) до первого опроса — иначе он не сможет
запушить домашку.

## 6. Проверка приёмки

- Пост одной кнопкой — черновик из `meta/drafts/` уходит в группу по кнопке «отправить».
- Коммит в `hw/<id>/` ученика → журнал обновляется за ≤ 5 минут (следующие 1–5 тиков,
  в зависимости от `github_poll_every`).
- Вопрос от ученика/родителя в Telegram → черновик ответа по кнопке «Claude, черновик»
  → ответ уходит по reply.
- Отключить HP от сети на 10 минут — тик должен пережить обрыв (лог `pull:`/`push:`
  с текстом ошибки, локальные элементы всё равно обрабатываются), после включения
  очереди досылаются сами.
- Страница домашки открывается на сайте курса (`pages_url` из `comms.toml`).
