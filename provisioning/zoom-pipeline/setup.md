# Установка Zoom-пайплайна

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

Смонтировать шару QNAP: Finder → Cmd-K → `smb://<nas>/backup`, галка «повторно подключать при входе»

```bash
cd tools && .venv/bin/pip install -r requirements.txt
```

**Внимание про стемы:** стемы короче 4–5 букв съедают обычные слова («Вик» замажет «викторину», «Маш» — «машину»). Брать стем длиной с полное имя без окончания и проверять первый черновик глазами.

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
