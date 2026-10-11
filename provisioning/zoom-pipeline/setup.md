# Установка Zoom-пайплайна

Анализ использует Codex CLI с отдельным временным окружением без инструментов
и глобальных инструкций. Поддерживаемая конфигурация проверена на CLI 0.160.0.
После обновления CLI повторно проверить изоляцию до включения расписания.
Текущее состояние развёртывания — [maintenance](../../meta/maintenance.md).

## 1. Zoom-аккаунт

Settings → Recording:
- Включить Cloud recording
- Включить Audio transcript
- В повторяющейся встрече курса — Record automatically in the cloud

Плагинов и app в клиент не ставится.

## 2. Marketplace

marketplace.zoom.us → Develop → Build App → Server-to-Server OAuth

- Скопировать Account ID / Client ID / Client Secret
- Scopes → добавить `cloud_recording:read:list_user_recordings:admin`, `cloud_recording:read:recording:admin`, `cloud_recording:delete:recording:admin` (имена в консоли Zoom могут отличаться редакцией — брать read+delete на recording)
- Activate

## 3. Мак

```bash
mkdir -p ~/.junior_it
cp provisioning/zoom-pipeline/zoom.env.example ~/.junior_it/zoom.env
cp provisioning/zoom-pipeline/zoom-pipeline.toml.example ~/.junior_it/zoom-pipeline.toml
```

Отредактировать обе копии и заполнить секреты.

В `[analysis]` задать абсолютный путь `command` к Codex, `model` и
`reasoning_effort`. Авторизация берётся из `~/.codex/auth.json` (либо
`CODEX_HOME/auth.json`), без копирования токенов. `claude_cmd` не поддерживается.

**Внимание про стемы:** при редактировании `zoom-pipeline.toml` — стемы короче 4–5 букв съедают обычные слова («Вик» замажет «викторину», «Маш» — «машину»). Брать стем длиной с полное имя без окончания и проверять первый черновик глазами.

Смонтировать шару QNAP: Finder → Cmd-K → `smb://<nas>/backup`, галка «повторно подключать при входе»

```bash
cd tools && .venv/bin/pip install -r requirements.txt
```

## 4. Проверка руками

```bash
PYTHONPATH=tools tools/.venv/bin/python -m zoom_pipeline.pipeline --dry-run
```

Вывод: список записей и фаз.

Затем первый полный прогон (первый запуск mlx-whisper скачает модель, это долго):

```bash
PYTHONPATH=tools tools/.venv/bin/python -m zoom_pipeline.pipeline --once
```

## 5. Автозапуск

```bash
cp provisioning/zoom-pipeline/com.juniorit.zoom-pipeline.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.juniorit.zoom-pipeline.plist
```

Лог: `~/Library/Logs/junior-it-zoom.log`

## 6. Ошибки анализа и ручное возобновление

Состояние v2 содержит отдельные фазу обработки и историю анализа. Временная
ошибка допускает три попытки всего: немедленно, через час после ошибки, затем
через четыре часа. Поздний срок восстановления сервиса имеет приоритет.
Блокировка аккаунта останавливает движок для всех записей. Неизвестная ошибка,
невалидный ответ или прерванный процесс блокируют запись. Старые `transcribed`
без истории попыток получают `legacy_untracked` и требуют явного возобновления.
Повреждённый JSON останавливает процесс: восстановить из сохранённой копии,
не удалять состояние для повторного старта.

Команды изменения состояния работают без Zoom и без вызова модели:

```bash
PYTHONPATH=tools tools/.venv/bin/python -m zoom_pipeline.pipeline --resume-engine
PYTHONPATH=tools tools/.venv/bin/python -m zoom_pipeline.pipeline --resume-analysis '<UUID>'
```

Первая снимает только общую блокировку; вторая сбрасывает счётчик выбранной
записи и начинает новый цикл. Восстановить авторизацию до выполнения этих команд.

Отдельный анализ локального транскрипта, без Zoom, скачивания и retention:

```bash
PYTHONPATH=tools tools/.venv/bin/python -m zoom_pipeline.pipeline --analyze-only '<UUID>'
```

Для старого состояния без времени встречи используется `0000` в имени черновика;
без сохранённых данных доступа сообщение содержит отметку о недоступной ссылке.
Успешно проанализированная запись повторного запроса не вызывает.

Для остановки и возврата расписания (UID на этом Mac — 501):

```bash
launchctl disable gui/501/com.juniorit.zoom-pipeline
launchctl bootout gui/501/com.juniorit.zoom-pipeline
# После успешного пробного анализа:
launchctl enable gui/501/com.juniorit.zoom-pipeline
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.juniorit.zoom-pipeline.plist
```

Не включать расписание до подтверждения формата ответа, сохранённого состояния
и отсутствия инструментов в фактическом запросе CLI. `--ephemeral` исключает
сохранение чата; Markdown принимается только с шестью непустыми разделами.
