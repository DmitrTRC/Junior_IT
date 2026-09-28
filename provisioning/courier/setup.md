# Развёртывание courier на HP

## 1. Базовая система

Debian 12 netinst на HP Elite 800, hostname `hp`, статический IP по DHCP-резервации
на роутере.

```bash
apt install git rsync openssh-server curl
```

## 2. Пользователь courier

```bash
useradd -r -m -d /srv/courier -s /bin/bash courier
mkdir -p /srv/courier/queue
```

SSH-ключ с Мака — единственный в `authorized_keys`, вход по паролю выключен:

```bash
mkdir -p /srv/courier/.ssh
echo "<публичный ключ Мака>" > /srv/courier/.ssh/authorized_keys
chown -R courier:courier /srv/courier/.ssh
chmod 700 /srv/courier/.ssh
chmod 600 /srv/courier/.ssh/authorized_keys
```

В `/etc/ssh/sshd_config` — `PasswordAuthentication no`, затем `systemctl restart sshd`.

## 3. Python 3.12 и код

Под пользователем `courier`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
uv venv /srv/courier/venv --python 3.12
git clone <URL репозитория> /srv/courier/src
/srv/courier/venv/bin/pip install /srv/courier/src/courier
```

## 4. shadowsocks-rust (обход блокировок Telegram)

Скачать релиз `sslocal` (shadowsocks-rust) с GitHub, положить в `/usr/local/bin`,
сделать исполняемым.

`/srv/courier/sslocal.json` собрать из Outline-ключа вида
`ss://<base64(method:password)>@<host>:<port>`:

```json
{
  "server": "<host из ss-ключа>",
  "server_port": <port из ss-ключа>,
  "method": "<method из ss-ключа>",
  "password": "<password из ss-ключа>",
  "local_address": "127.0.0.1",
  "local_port": 1080
}
```

Проверка после запуска `sslocal` (см. шаг 6):

```bash
curl --max-time 30 --socks5-hostname 127.0.0.1:1080 https://api.telegram.org
```

Ожидаемый ответ — JSON с `"ok":false` (Telegram отвечает без указания метода в пути,
это и значит, что туннель работает).

## 5. Конфиг и секреты

```bash
cp /srv/courier/src/courier/courier.toml.example /srv/courier/courier.toml
cp /srv/courier/src/courier/courier.env.example /srv/courier/courier.env
chmod 600 /srv/courier/courier.env
```

`group_chat_id` — добавить бота в группу курса, вызвать `getUpdates`, взять `chat.id`
(отрицательное число).

`teacher_telegram_id` — Димасу написать боту `/start` без кода, вызвать `getUpdates`,
взять `from.id`.

Заполнить `/srv/courier/courier.toml` (адреса очереди, `group_chat_id`,
`teacher_telegram_id`, `proxy = "socks5://127.0.0.1:1080"`) и
`/srv/courier/courier.env` (`BOT_TOKEN` от BotFather).

## 6. Автозапуск

```bash
cp /srv/courier/src/courier/systemd/sslocal.service /etc/systemd/system/
cp /srv/courier/src/courier/systemd/courier.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now sslocal courier
journalctl -u courier -f
```

Проверка: Димасу приходит heartbeat; тестовый аккаунт шлёт боту `/start <код>` и
получает подтверждение регистрации.

## 7. Проверка обрыва сети

```bash
ip link set <интерфейс> down
```

Подождать 3 минуты, затем:

```bash
ip link set <интерфейс> up
```

После восстановления связи в личку Димасу должно прийти «Был в отключке».
