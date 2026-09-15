# Zoom-пайплайн — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Автоматический контур записей Zoom: обнаружить новую облачную
запись → скачать → бэкап на QNAP → локальная транскрипция → анализ против
плана занятия → черновики (постмортем, рекомендации, сообщение в MAX).

**Architecture:** Python-пакет `tools/zoom_pipeline/` с чистыми модулями
(config, anonymize, zoom_api, state) и оркестратором `pipeline.py`,
запускаемым launchd-агентом раз в час. Все внешние действия (rsync,
mlx_whisper, claude -p, osascript) — через инъецируемый runner, поэтому
тестируются без сети и субпроцессов. Фазы записи хранятся в state-файле —
тик идемпотентен, сбой любой фазы повторяется следующим тиком.

**Tech Stack:** Python 3.11+ (`tools/.venv`, pytest там же), `requests`
(добавляется в tools/requirements.txt), stdlib `tomllib`; внешние бинари:
`rsync`, `uvx` + `mlx-whisper`, `claude`, `osascript`.

**Spec:** `docs/superpowers/specs/2026-09-15-zoom-pipeline-design.md` —
читать до начала. Плюс правила коммуникации: сообщение в MAX не содержит
слов «контроль», «проверки», «дружина» (жёсткие запреты CLAUDE.md).

## Global Constraints

- Секреты только в `~/.junior_it/zoom.env` (ZOOM_ACCOUNT_ID,
  ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET); в репо — только `*.example` с
  плейсхолдерами. Ни одного секрета в коде, тестах, коммитах.
- Конфиг — `~/.junior_it/zoom-pipeline.toml`; state —
  `~/.junior_it/zoom-state.json`. В репо не попадают.
- Все сетевые вызовы и субпроцессы — с таймаутами (API 30 c, download
  30 мин, rsync 30 мин, whisper 60 мин, claude 15 мин, osascript 10 c).
  Ретраев внутри тика нет — ретрай = следующий тик.
- Медиа наружу не уходит; в Claude API — только обезличенный транскрипт
  (имена детей → «Ученик N» ДО отправки).
- Пайплайн ничего не коммитит в git и не постит в MAX.
- Идентификаторы английские, лог-сообщения русские, без эмодзи.
- Тесты: `cd tools && .venv/bin/python -m pytest tests/test_zoom_*.py`.
  Сеть, диск вне tmp_path и субпроцессы в тестах мокаются всегда.
- Коммит после каждой задачи; git push не делать.

## Файловая карта

```
tools/zoom_pipeline/
├── __init__.py          пустой
├── config.py            Config + load_config (toml + env)
├── anonymize.py         замена имён по стемам (чистая)
├── zoom_api.py          S2S OAuth, list/download/delete
├── state.py             фазы записей, json-персист
├── phases.py            download/backup/transcribe/analyze/retention/notify
├── pipeline.py          tick() + CLI (--once, --dry-run)
└── analysis_prompt.md   шаблон промпта анализа
provisioning/zoom-pipeline/
├── com.juniorit.zoom-pipeline.plist
├── zoom.env.example
├── zoom-pipeline.toml.example
└── setup.md             настройка Zoom-аккаунта и установка агента
tools/tests/
├── test_zoom_config.py
├── test_zoom_anonymize.py
├── test_zoom_api.py
├── test_zoom_state.py
└── test_zoom_pipeline.py
```

---

### Task 1: config и anonymize

**Files:**
- Create: `tools/zoom_pipeline/__init__.py` (пустой)
- Create: `tools/zoom_pipeline/config.py`
- Create: `tools/zoom_pipeline/anonymize.py`
- Modify: `tools/requirements.txt` (добавить строку `requests`)
- Test: `tools/tests/test_zoom_config.py`, `tools/tests/test_zoom_anonymize.py`

**Interfaces:**
- Produces:
  - `Config` (frozen dataclass): `repo_root: Path`, `recordings_dir: Path`
    (= repo_root/"recordings"), `drafts_dir: Path` (= repo_root/"meta/drafts"),
    `backup_dir: Path`, `state_path: Path`, `retention_days: int`,
    `student_stems: list[str]`, `whisper_cmd: list[str]`,
    `claude_cmd: list[str]`, `zoom_account_id/zoom_client_id/zoom_client_secret: str`.
  - `load_config(toml_path: Path, env_path: Path) -> Config` — бросает
    `ConfigError` (наследник Exception, определить здесь же) с русским
    текстом при отсутствии файла/ключа.
  - `anonymize(text: str, stems: list[str]) -> str` — i-й стем (1-based) →
    «Ученик i», регистронезависимо, стем + хвост словоформы.

- [ ] **Step 1: Написать падающие тесты**

`tools/tests/test_zoom_anonymize.py`:

```python
from zoom_pipeline.anonymize import anonymize


def test_replaces_declensions_case_insensitive():
    text = "Настя пишет код. Скажи Насте. НАСТЮ похвалили."
    assert anonymize(text, ["Наст"]) == (
        "Ученик 1 пишет код. Скажи Ученик 1. Ученик 1 похвалили."
    )


def test_numbers_stems_in_order():
    text = "Вика помогла Маше."
    assert anonymize(text, ["Вик", "Маш"]) == "Ученик 1 помогла Ученик 2."


def test_does_not_touch_other_words():
    # стем должен матчиться только с начала слова
    text = "Полынастил доски."  # «наст» внутри слова
    assert anonymize(text, ["Наст"]) == "Полынастил доски."


def test_empty_stems_noop():
    assert anonymize("Привет всем", []) == "Привет всем"
```

`tools/tests/test_zoom_config.py`:

```python
import pytest

from zoom_pipeline.config import ConfigError, load_config


def write_files(tmp_path, toml_text=None, env_text=None):
    toml_path = tmp_path / "zoom-pipeline.toml"
    env_path = tmp_path / "zoom.env"
    toml_path.write_text(toml_text if toml_text is not None else (
        f'repo_root = "{tmp_path}/repo"\n'
        'backup_dir = "/Volumes/backup/JuniorIT/recordings"\n'
        'retention_days = 30\n'
        'student_stems = ["Наст"]\n'
    ), encoding="utf-8")
    env_path.write_text(env_text if env_text is not None else (
        "ZOOM_ACCOUNT_ID=acc\nZOOM_CLIENT_ID=cid\nZOOM_CLIENT_SECRET=sec\n"
    ), encoding="utf-8")
    return toml_path, env_path


def test_loads_and_derives_paths(tmp_path):
    toml_path, env_path = write_files(tmp_path)
    cfg = load_config(toml_path, env_path)
    assert cfg.recordings_dir == tmp_path / "repo" / "recordings"
    assert cfg.drafts_dir == tmp_path / "repo" / "meta" / "drafts"
    assert cfg.retention_days == 30
    assert cfg.zoom_client_secret == "sec"
    assert cfg.whisper_cmd[0] == "uvx"
    assert cfg.state_path.name == "zoom-state.json"


def test_missing_env_key_raises(tmp_path):
    toml_path, env_path = write_files(tmp_path, env_text="ZOOM_ACCOUNT_ID=acc\n")
    with pytest.raises(ConfigError):
        load_config(toml_path, env_path)


def test_missing_toml_raises(tmp_path):
    _, env_path = write_files(tmp_path)
    with pytest.raises(ConfigError):
        load_config(tmp_path / "нет.toml", env_path)
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd tools && .venv/bin/python -m pytest tests/test_zoom_anonymize.py tests/test_zoom_config.py -v`
Expected: FAIL — `ModuleNotFoundError: zoom_pipeline`

- [ ] **Step 3: Реализация**

`tools/zoom_pipeline/anonymize.py`:

```python
import re


def anonymize(text, stems):
    """Имена детей -> «Ученик N». Стем матчится с начала слова."""
    result = text
    for i, stem in enumerate(stems, start=1):
        pattern = re.compile(rf"\b{re.escape(stem)}\w*", re.IGNORECASE)
        result = pattern.sub(f"Ученик {i}", result)
    return result
```

`tools/zoom_pipeline/config.py`:

```python
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

API_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 1800
RSYNC_TIMEOUT = 1800
WHISPER_TIMEOUT = 3600
CLAUDE_TIMEOUT = 900
NOTIFY_TIMEOUT = 10

ENV_KEYS = ("ZOOM_ACCOUNT_ID", "ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    repo_root: Path
    backup_dir: Path
    retention_days: int
    student_stems: list[str]
    zoom_account_id: str
    zoom_client_id: str
    zoom_client_secret: str
    state_path: Path
    whisper_cmd: list[str] = field(default_factory=lambda: [
        "uvx", "mlx_whisper", "--model",
        "mlx-community/whisper-large-v3-mlx", "--language", "ru",
        "--output-format", "txt",
    ])
    claude_cmd: list[str] = field(default_factory=lambda: [
        "claude", "-p", "--model", "sonnet",
    ])

    @property
    def recordings_dir(self):
        return self.repo_root / "recordings"

    @property
    def drafts_dir(self):
        return self.repo_root / "meta" / "drafts"

    @property
    def playground_dir(self):
        return self.repo_root / "playground"


def _read_env(env_path):
    if not env_path.is_file():
        raise ConfigError(f"нет файла секретов: {env_path}")
    values = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    missing = [k for k in ENV_KEYS if not values.get(k)]
    if missing:
        raise ConfigError(f"в {env_path} нет ключей: {', '.join(missing)}")
    return values


def load_config(toml_path, env_path):
    if not toml_path.is_file():
        raise ConfigError(f"нет конфига: {toml_path}")
    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)
    try:
        repo_root = Path(data["repo_root"])
        backup_dir = Path(data["backup_dir"])
        retention_days = int(data["retention_days"])
        student_stems = list(data["student_stems"])
    except KeyError as exc:
        raise ConfigError(f"в {toml_path} нет ключа {exc}") from exc
    env = _read_env(env_path)
    return Config(
        repo_root=repo_root,
        backup_dir=backup_dir,
        retention_days=retention_days,
        student_stems=student_stems,
        zoom_account_id=env["ZOOM_ACCOUNT_ID"],
        zoom_client_id=env["ZOOM_CLIENT_ID"],
        zoom_client_secret=env["ZOOM_CLIENT_SECRET"],
        state_path=env_path.parent / "zoom-state.json",
    )
```

В `tools/requirements.txt` добавить строку `requests` (понадобится в
Task 2; ставится сразу: `cd tools && .venv/bin/pip install requests`).

- [ ] **Step 4: Прогнать тесты**

Run: `cd tools && .venv/bin/python -m pytest tests/test_zoom_anonymize.py tests/test_zoom_config.py -v`
Expected: PASS (7 тестов)

- [ ] **Step 5: Полный прогон tools и коммит**

Run: `cd tools && .venv/bin/python -m pytest`
Expected: PASS (старые 77 + новые)

```bash
git add tools/zoom_pipeline/ tools/tests/test_zoom_config.py tools/tests/test_zoom_anonymize.py tools/requirements.txt
git commit -m "zoom: конфиг и обезличивание транскрипта"
```

---

### Task 2: zoom_api — OAuth, список, скачивание, удаление

**Files:**
- Create: `tools/zoom_pipeline/zoom_api.py`
- Test: `tools/tests/test_zoom_api.py`

**Interfaces:**
- Consumes: `Config` (Task 1) — поля zoom_*.
- Produces:
  - `@dataclass RecFile: file_type: str, extension: str, download_url: str`
  - `@dataclass Meeting: uuid: str, topic: str, start_time: str (ISO),
    share_url: str, passcode: str, files: list[RecFile]`
  - `class ZoomApi(account_id, client_id, client_secret, http=requests)`:
    - `.list_recordings(from_date: str) -> list[Meeting]`
    - `.download(url: str, dest: Path) -> None` (стрим в файл, Bearer)
    - `.delete_recording(uuid: str) -> None` (uuid двойное URL-кодирование)
    - `ZoomApiError` при не-2xx.

- [ ] **Step 1: Написать падающие тесты**

`tools/tests/test_zoom_api.py`:

```python
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from zoom_pipeline.zoom_api import ZoomApi, ZoomApiError

LIST_RESPONSE = {
    "meetings": [{
        "uuid": "aBc//12+3==",
        "topic": "Занятие: Python",
        "start_time": "2026-09-16T17:00:00Z",
        "share_url": "https://zoom.us/rec/share/xyz",
        "recording_play_passcode": "p@ss",
        "recording_files": [
            {"file_type": "MP4", "file_extension": "MP4",
             "download_url": "https://zoom.us/rec/download/v1"},
            {"file_type": "M4A", "file_extension": "M4A",
             "download_url": "https://zoom.us/rec/download/a1"},
        ],
    }],
}


class FakeResponse:
    def __init__(self, status_code=200, payload=None, chunks=None):
        self.status_code = status_code
        self._payload = payload
        self._chunks = chunks or []

    def json(self):
        return self._payload

    def iter_content(self, chunk_size):
        return iter(self._chunks)


class FakeHttp:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)


TOKEN = FakeResponse(payload={"access_token": "tkn", "expires_in": 3600})


def make_api(*responses):
    http = FakeHttp([TOKEN, *responses])
    return ZoomApi("acc", "cid", "sec", http=http), http


def test_list_recordings_parses_meetings():
    api, http = make_api(FakeResponse(payload=LIST_RESPONSE))
    meetings = api.list_recordings("2026-09-09")
    assert len(meetings) == 1
    m = meetings[0]
    assert m.uuid == "aBc//12+3=="
    assert m.passcode == "p@ss"
    assert {f.file_type for f in m.files} == {"MP4", "M4A"}
    # токен запрошен один раз, Basic-авторизация
    token_call = http.calls[0]
    assert token_call[0] == "POST" and "oauth/token" in token_call[1]


def test_download_streams_to_file(tmp_path):
    api, _ = make_api(FakeResponse(chunks=[b"ab", b"cd"]))
    dest = tmp_path / "rec.m4a"
    api.download("https://zoom.us/rec/download/a1", dest)
    assert dest.read_bytes() == b"abcd"


def test_delete_double_encodes_uuid():
    api, http = make_api(FakeResponse(status_code=204, payload={}))
    api.delete_recording("aBc//12+3==")
    method, url, _ = http.calls[-1]
    assert method == "DELETE"
    assert "aBc%252F%252F12%252B3%253D%253D" in url


def test_non_2xx_raises():
    api, _ = make_api(FakeResponse(status_code=401, payload={}))
    with pytest.raises(ZoomApiError):
        api.list_recordings("2026-09-09")
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd tools && .venv/bin/python -m pytest tests/test_zoom_api.py -v`
Expected: FAIL — `ModuleNotFoundError: zoom_pipeline.zoom_api`

- [ ] **Step 3: Реализация `tools/zoom_pipeline/zoom_api.py`**

```python
import time
from dataclasses import dataclass
from urllib.parse import quote

import requests

from zoom_pipeline.config import API_TIMEOUT, DOWNLOAD_TIMEOUT

BASE = "https://api.zoom.us/v2"


class ZoomApiError(Exception):
    pass


@dataclass(frozen=True)
class RecFile:
    file_type: str
    extension: str
    download_url: str


@dataclass(frozen=True)
class Meeting:
    uuid: str
    topic: str
    start_time: str
    share_url: str
    passcode: str
    files: list


def _check(response, what):
    if response.status_code // 100 != 2:
        raise ZoomApiError(f"{what}: HTTP {response.status_code}")
    return response


class ZoomApi:
    def __init__(self, account_id, client_id, client_secret, http=requests):
        self._account_id = account_id
        self._auth = (client_id, client_secret)
        self._http = http
        self._token_value = None
        self._token_expires = 0.0

    def _token(self):
        if self._token_value and time.monotonic() < self._token_expires:
            return self._token_value
        response = _check(self._http.post(
            "https://zoom.us/oauth/token",
            params={"grant_type": "account_credentials",
                    "account_id": self._account_id},
            auth=self._auth, timeout=API_TIMEOUT,
        ), "получение токена")
        payload = response.json()
        self._token_value = payload["access_token"]
        self._token_expires = time.monotonic() + payload["expires_in"] - 60
        return self._token_value

    def _headers(self):
        return {"Authorization": f"Bearer {self._token()}"}

    def list_recordings(self, from_date):
        response = _check(self._http.get(
            f"{BASE}/users/me/recordings",
            params={"from": from_date, "page_size": 100},
            headers=self._headers(), timeout=API_TIMEOUT,
        ), "список записей")
        meetings = []
        for m in response.json().get("meetings", []):
            files = [RecFile(f.get("file_type", ""),
                             f.get("file_extension", "").lower(),
                             f.get("download_url", ""))
                     for f in m.get("recording_files", [])
                     if f.get("download_url")]
            meetings.append(Meeting(
                uuid=m["uuid"], topic=m.get("topic", ""),
                start_time=m.get("start_time", ""),
                share_url=m.get("share_url", ""),
                passcode=m.get("recording_play_passcode",
                               m.get("password", "")),
                files=files,
            ))
        return meetings

    def download(self, url, dest):
        response = _check(self._http.get(
            url, headers=self._headers(), stream=True,
            timeout=DOWNLOAD_TIMEOUT,
        ), "скачивание записи")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as fh:
            for chunk in response.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
        tmp.replace(dest)

    def delete_recording(self, uuid):
        encoded = quote(quote(uuid, safe=""), safe="")
        _check(self._http.delete(
            f"{BASE}/meetings/{encoded}/recordings",
            params={"action": "trash"},
            headers=self._headers(), timeout=API_TIMEOUT,
        ), "удаление записи из облака")
```

Нюанс для реализатора: в `download` тест не проверяет `.part`-переименование
явно — оно проверяется косвенно (итоговый файл существует с полным
содержимым). Не убирать: атомарность против недокачанных файлов.

- [ ] **Step 4: Прогнать тесты**

Run: `cd tools && .venv/bin/python -m pytest tests/test_zoom_api.py -v`
Expected: PASS (4 теста)

- [ ] **Step 5: Commit**

```bash
git add tools/zoom_pipeline/zoom_api.py tools/tests/test_zoom_api.py
git commit -m "zoom: клиент Cloud Recording API — токен, список, скачивание, удаление"
```

---

### Task 3: state — фазы записей

**Files:**
- Create: `tools/zoom_pipeline/state.py`
- Test: `tools/tests/test_zoom_state.py`

**Interfaces:**
- Produces:
  - `PHASES = ("downloaded", "backed_up", "transcribed", "analyzed", "cloud_deleted")`
  - `class State`:
    - `State.load(path: Path) -> State` (нет файла/битый JSON → пустой)
    - `.phase(uuid) -> str` — текущая фаза или `"new"`
    - `.advance(uuid, phase, *, date="", topic="")` — ставит фазу
      (date/topic сохраняются при первом advance) и сразу пишет файл
    - `.uuids_in_phase(phase) -> list[str]`
    - `.meta(uuid) -> dict` (date, topic)

- [ ] **Step 1: Написать падающие тесты**

`tools/tests/test_zoom_state.py`:

```python
from zoom_pipeline.state import PHASES, State


def test_unknown_uuid_is_new(tmp_path):
    state = State.load(tmp_path / "s.json")
    assert state.phase("x") == "new"


def test_advance_persists_and_reloads(tmp_path):
    path = tmp_path / "s.json"
    state = State.load(path)
    state.advance("u1", "downloaded", date="2026-09-16", topic="Python")
    reloaded = State.load(path)
    assert reloaded.phase("u1") == "downloaded"
    assert reloaded.meta("u1")["topic"] == "Python"


def test_broken_json_starts_clean(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("{оборвано", encoding="utf-8")
    assert State.load(path).phase("u1") == "new"


def test_uuids_in_phase(tmp_path):
    state = State.load(tmp_path / "s.json")
    state.advance("u1", "backed_up", date="2026-09-16")
    state.advance("u2", "analyzed", date="2026-09-13")
    assert state.uuids_in_phase("backed_up") == ["u1"]
    assert PHASES[-1] == "cloud_deleted"
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd tools && .venv/bin/python -m pytest tests/test_zoom_state.py -v`
Expected: FAIL — `ModuleNotFoundError: zoom_pipeline.state`

- [ ] **Step 3: Реализация `tools/zoom_pipeline/state.py`**

```python
import json
from pathlib import Path

PHASES = ("downloaded", "backed_up", "transcribed", "analyzed", "cloud_deleted")


class State:
    def __init__(self, path, entries):
        self._path = Path(path)
        self._entries = entries

    @classmethod
    def load(cls, path):
        path = Path(path)
        entries = {}
        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    entries = raw
            except json.JSONDecodeError:
                entries = {}  # битый state не повод падать: начнём заново
        return cls(path, entries)

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._entries, ensure_ascii=False, indent=2),
            encoding="utf-8")

    def phase(self, uuid):
        return self._entries.get(uuid, {}).get("phase", "new")

    def meta(self, uuid):
        entry = self._entries.get(uuid, {})
        return {"date": entry.get("date", ""), "topic": entry.get("topic", "")}

    def advance(self, uuid, phase, *, date="", topic=""):
        entry = self._entries.setdefault(uuid, {})
        entry["phase"] = phase
        if date and not entry.get("date"):
            entry["date"] = date
        if topic and not entry.get("topic"):
            entry["topic"] = topic
        self._save()

    def uuids_in_phase(self, phase):
        return [u for u, e in self._entries.items() if e.get("phase") == phase]
```

- [ ] **Step 4: Прогнать тесты**

Run: `cd tools && .venv/bin/python -m pytest tests/test_zoom_state.py -v`
Expected: PASS (4 теста)

- [ ] **Step 5: Commit**

```bash
git add tools/zoom_pipeline/state.py tools/tests/test_zoom_state.py
git commit -m "zoom: state-машина фаз записи"
```

---

### Task 4: phases и pipeline — оркестратор с инъекцией

**Files:**
- Create: `tools/zoom_pipeline/phases.py`
- Create: `tools/zoom_pipeline/pipeline.py`
- Create: `tools/zoom_pipeline/analysis_prompt.md`
- Test: `tools/tests/test_zoom_pipeline.py`

**Interfaces:**
- Consumes: `Config` (T1), `ZoomApi`/`Meeting` (T2), `State`/`PHASES` (T3),
  `anonymize` (T1).
- Produces:
  - `run_tick(cfg, api, state, runner, today: date, log) -> None`
  - `runner(cmd: list[str], *, timeout: int, stdin_text: str | None = None)
    -> subprocess.CompletedProcess` — единственная точка запуска
    субпроцессов; в тестах подменяется.
  - CLI: `python -m zoom_pipeline.pipeline [--once] [--dry-run]`
    (без аргументов = `--once`).

Фазовая логика тика для каждой встречи из `list_recordings(за 7 дней)`:

| фаза | действие | следующая |
|---|---|---|
| new | скачать mp4+m4a+vtt в `recordings/<date>/` | downloaded |
| downloaded | rsync в `backup_dir` (если смонтирован) | backed_up |
| backed_up | whisper по m4a → `transcript.txt` (нет m4a или whisper упал, но есть vtt → взять vtt с пометкой) | transcribed |
| transcribed | anonymize → prompt → `claude -p` → `meta/drafts/lesson-<date>-analysis.md` → уведомление | analyzed |

Retention: после обхода встреч — `uuids_in_phase("analyzed")` с датой
старше `retention_days` → `api.delete_recording` → `cloud_deleted`.
Ошибка любой фазы: лог + `continue` — фаза не продвигается, следующий тик
повторит. `--dry-run`: вместо действий печатает «сделал бы X» и не пишет
state.

- [ ] **Step 1: Написать падающие тесты**

`tools/tests/test_zoom_pipeline.py`:

```python
import subprocess
from datetime import date
from pathlib import Path

from zoom_pipeline.config import Config
from zoom_pipeline.phases import run_tick
from zoom_pipeline.state import State
from zoom_pipeline.zoom_api import Meeting, RecFile


def make_cfg(tmp_path):
    return Config(
        repo_root=tmp_path / "repo",
        backup_dir=tmp_path / "nas",
        retention_days=30,
        student_stems=["Наст"],
        zoom_account_id="a", zoom_client_id="c", zoom_client_secret="s",
        state_path=tmp_path / "state.json",
    )


def meeting(uuid="u1", start="2026-09-16T17:00:00Z"):
    return Meeting(
        uuid=uuid, topic="Занятие", start_time=start,
        share_url="https://zoom.us/rec/share/x", passcode="pc",
        files=[RecFile("MP4", "mp4", "https://dl/v"),
               RecFile("M4A", "m4a", "https://dl/a")],
    )


class FakeApi:
    def __init__(self, meetings):
        self.meetings = meetings
        self.downloaded = []
        self.deleted = []

    def list_recordings(self, from_date):
        return self.meetings

    def download(self, url, dest):
        self.downloaded.append(url)
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(b"data")

    def delete_recording(self, uuid):
        self.deleted.append(uuid)


def ok_runner(calls):
    def runner(cmd, *, timeout, stdin_text=None):
        calls.append(cmd)
        if cmd[0] == "uvx":
            # mlx_whisper пишет <аудио>.txt в --output-dir — эмулируем
            out_dir = Path(cmd[cmd.index("--output-dir") + 1])
            audio = Path(cmd[-1])
            (out_dir / (audio.stem + ".txt")).write_text(
                "Настя молодец", encoding="utf-8")
        # claude -p печатает markdown анализа в stdout
        out = "# Анализ\n" if cmd[0] == "claude" else ""
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
    return runner


def failing_rsync_runner(calls):
    def runner(cmd, *, timeout, stdin_text=None):
        calls.append(cmd)
        code = 23 if cmd[0] == "rsync" else 0
        return subprocess.CompletedProcess(cmd, code, stdout="", stderr="нет шары")
    return runner


def run(cfg, api, runner_fn, today=date(2026, 9, 16)):
    state = State.load(cfg.state_path)
    logs = []
    run_tick(cfg, api, state, runner_fn, today, log=logs.append)
    return state, logs


def test_full_pass_reaches_analyzed(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.backup_dir.mkdir(parents=True)  # «шара смонтирована»
    api = FakeApi([meeting()])
    calls = []
    state, _ = run(cfg, api, ok_runner(calls))
    assert state.phase("u1") == "analyzed"
    assert len(api.downloaded) == 2
    assert any(c[0] == "rsync" for c in calls)
    assert any(c[0] == "uvx" for c in calls)
    assert any(c[0] == "claude" for c in calls)
    draft = cfg.drafts_dir / "lesson-2026-09-16-analysis.md"
    assert draft.is_file()
    assert "Анализ" in draft.read_text(encoding="utf-8")


def test_backup_failure_stalls_phase(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.backup_dir.mkdir(parents=True)
    api = FakeApi([meeting()])
    calls = []
    state, logs = run(cfg, api, failing_rsync_runner(calls))
    assert state.phase("u1") == "downloaded"
    assert not any(c[0] == "uvx" for c in calls)  # дальше бэкапа не пошли
    assert any("rsync" in line for line in logs)


def test_unmounted_share_stalls_phase(tmp_path):
    cfg = make_cfg(tmp_path)  # backup_dir не существует = не смонтирован
    api = FakeApi([meeting()])
    state, logs = run(cfg, api, ok_runner([]))
    assert state.phase("u1") == "downloaded"


def test_second_tick_is_idempotent(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.backup_dir.mkdir(parents=True)
    api = FakeApi([meeting()])
    run(cfg, api, ok_runner([]))
    api.downloaded.clear()
    state, _ = run(cfg, api, ok_runner([]))
    assert state.phase("u1") == "analyzed"
    assert api.downloaded == []  # повторно не качали


def test_retention_deletes_old_backed_up(tmp_path):
    cfg = make_cfg(tmp_path)
    api = FakeApi([])
    state = State.load(cfg.state_path)
    state.advance("old", "analyzed", date="2026-08-01")
    state.advance("fresh", "analyzed", date="2026-09-10")
    run_tick(cfg, api, state, ok_runner([]), date(2026, 9, 16), log=lambda s: None)
    assert api.deleted == ["old"]
    assert state.phase("old") == "cloud_deleted"
    assert state.phase("fresh") == "analyzed"
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd tools && .venv/bin/python -m pytest tests/test_zoom_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: zoom_pipeline.phases`

- [ ] **Step 3: Реализация**

`tools/zoom_pipeline/analysis_prompt.md` (шаблон, подставляется через
`str.format`; фигурные скобки в тексте — только плейсхолдеры):

```markdown
Ты — ассистент преподавателя курса Junior_IT (углублённая информатика,
7–8 класс, мини-группа 2–3 ребёнка, занятие 75 минут). Ниже — обезличенный
транскрипт занятия (имена детей заменены на «Ученик N») и план занятия
session.yml (если он пуст — анализируй без сверки с планом и отметь это).

Дата занятия: {date}. Тема: {topic}.
Ссылка на запись: {share_url} · код доступа: {passcode}

Собери markdown-документ со строго этими разделами:

## Фактические тайминги
Блоки занятия из session.yml против того, что слышно в транскрипте:
когда реально начался и кончился каждый блок, где ушли от плана.

## Где буксовали
Моменты непонимания, повторные объяснения, паузы. Цитаты короткие.

## Cutting plan
Сработал ли план отсечения из session.yml: что резали, что стоило.

## Рекомендации к следующему занятию
3–7 конкретных пунктов: что повторить, что перестроить, где замедлиться.

## Черновик постмортема
По форме постмортемов курса: что сработало / что нет / открытые вопросы.

## Сообщение в MAX
Короткое тёплое сообщение родителям и ученикам: чем занимались, что
получилось, ссылка на запись и код доступа. К родителям — на «вы».
Запрещённые слова: «контроль», «проверка», «инспекция», «дружина»,
«отряд». Без эмодзи не обязательно — 1–2 уместны.

Верни ТОЛЬКО содержимое markdown-файла, без преамбулы.

=== session.yml ===
{session_yaml}

=== Транскрипт ===
{transcript}
```

`tools/zoom_pipeline/phases.py`:

```python
import subprocess
from datetime import date, timedelta
from importlib import resources

from zoom_pipeline.anonymize import anonymize
from zoom_pipeline.config import (CLAUDE_TIMEOUT, NOTIFY_TIMEOUT,
                                  RSYNC_TIMEOUT, WHISPER_TIMEOUT)


def default_runner(cmd, *, timeout, stdin_text=None):
    return subprocess.run(cmd, input=stdin_text, capture_output=True,
                          text=True, timeout=timeout)


def _meeting_date(meeting):
    return meeting.start_time[:10]


def _meeting_dir(cfg, meeting):
    return cfg.recordings_dir / _meeting_date(meeting)


def _download(cfg, api, meeting):
    target = _meeting_dir(cfg, meeting)
    for f in meeting.files:
        name = f"{meeting.uuid.replace('/', '_')}.{f.extension or f.file_type.lower()}"
        api.download(f.download_url, target / name)
    return target


def _backup(cfg, meeting, runner, log):
    if not cfg.backup_dir.is_dir():
        log(f"бэкап: шара не смонтирована ({cfg.backup_dir}), отложено")
        return False
    src = str(_meeting_dir(cfg, meeting))
    result = runner(["rsync", "-a", src, str(cfg.backup_dir) + "/"],
                    timeout=RSYNC_TIMEOUT)
    if result.returncode != 0:
        log(f"бэкап: rsync упал ({result.returncode}): {result.stderr.strip()}")
        return False
    return True

def _find_file(meeting_dir, *suffixes):
    for suffix in suffixes:
        found = sorted(meeting_dir.glob(f"*.{suffix}"))
        if found:
            return found[0]
    return None


def _transcribe(cfg, meeting, runner, log):
    meeting_dir = _meeting_dir(cfg, meeting)
    transcript = meeting_dir / "transcript.txt"
    audio = _find_file(meeting_dir, "m4a", "mp4")
    if audio is not None:
        result = runner([*cfg.whisper_cmd, "--output-dir", str(meeting_dir),
                         str(audio)], timeout=WHISPER_TIMEOUT)
        produced = audio.with_suffix(".txt")
        if result.returncode == 0 and produced.is_file():
            produced.replace(transcript)
            return transcript
        log(f"whisper упал ({result.returncode}), пробую облачный vtt")
    vtt = _find_file(meeting_dir, "vtt", "transcript")
    if vtt is not None:
        transcript.write_text(
            "[транскрипт из облака Zoom — точность ниже]\n" +
            vtt.read_text(encoding="utf-8"), encoding="utf-8")
        return transcript
    log("транскрибировать нечем: нет ни аудио с рабочим whisper, ни vtt")
    return None


def _session_yaml(cfg, meeting):
    path = cfg.playground_dir / _meeting_date(meeting) / "session.yml"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return "(session.yml на эту дату не найден)"


def _analyze(cfg, meeting, transcript_path, runner, log):
    template = (resources.files("zoom_pipeline") / "analysis_prompt.md") \
        .read_text(encoding="utf-8")
    prompt = template.format(
        date=_meeting_date(meeting), topic=meeting.topic,
        share_url=meeting.share_url, passcode=meeting.passcode,
        session_yaml=_session_yaml(cfg, meeting),
        transcript=anonymize(
            transcript_path.read_text(encoding="utf-8"), cfg.student_stems),
    )
    result = runner(cfg.claude_cmd, timeout=CLAUDE_TIMEOUT, stdin_text=prompt)
    if result.returncode != 0 or not result.stdout.strip():
        log(f"анализ: claude -p упал ({result.returncode})")
        return None
    cfg.drafts_dir.mkdir(parents=True, exist_ok=True)
    draft = cfg.drafts_dir / f"lesson-{_meeting_date(meeting)}-analysis.md"
    draft.write_text(result.stdout, encoding="utf-8")
    return draft


def _notify(draft, runner):
    runner(["osascript", "-e",
            f'display notification "{draft.name}" with title "Zoom-пайплайн: анализ готов"'],
           timeout=NOTIFY_TIMEOUT)


def _retention(cfg, api, state, today, log):
    for uuid in list(state.uuids_in_phase("analyzed")):
        meta = state.meta(uuid)
        if not meta["date"]:
            continue
        recorded = date.fromisoformat(meta["date"])
        if today - recorded >= timedelta(days=cfg.retention_days):
            try:
                api.delete_recording(uuid)
            except Exception as exc:
                log(f"retention: не удалилось {uuid}: {exc}")
                continue
            state.advance(uuid, "cloud_deleted")
            log(f"retention: запись {meta['date']} удалена из облака")


def run_tick(cfg, api, state, runner, today, log):
    since = (today - timedelta(days=7)).isoformat()
    try:
        meetings = api.list_recordings(since)
    except Exception as exc:
        log(f"опрос записей не удался: {exc}")
        return
    for meeting in meetings:
        try:
            _process(cfg, api, state, runner, meeting, log)
        except Exception as exc:
            log(f"встреча {meeting.uuid}: {exc}")
    _retention(cfg, api, state, today, log)


def _process(cfg, api, state, runner, meeting, log):
    phase = state.phase(meeting.uuid)
    day, topic = _meeting_date(meeting), meeting.topic
    if phase == "new":
        _download(cfg, api, meeting)
        state.advance(meeting.uuid, "downloaded", date=day, topic=topic)
        phase = "downloaded"
    if phase == "downloaded":
        if not _backup(cfg, meeting, runner, log):
            return
        state.advance(meeting.uuid, "backed_up", date=day, topic=topic)
        phase = "backed_up"
    if phase == "backed_up":
        transcript = _transcribe(cfg, meeting, runner, log)
        if transcript is None:
            return
        state.advance(meeting.uuid, "transcribed", date=day, topic=topic)
        phase = "transcribed"
    if phase == "transcribed":
        transcript = _meeting_dir(cfg, meeting) / "transcript.txt"
        draft = _analyze(cfg, meeting, transcript, runner, log)
        if draft is None:
            return
        state.advance(meeting.uuid, "analyzed", date=day, topic=topic)
        _notify(draft, runner)
```

`tools/zoom_pipeline/pipeline.py`:

```python
import argparse
import sys
from datetime import date
from pathlib import Path

from zoom_pipeline.config import load_config
from zoom_pipeline.phases import default_runner, run_tick
from zoom_pipeline.state import State
from zoom_pipeline.zoom_api import ZoomApi

CONFIG_DIR = Path.home() / ".junior_it"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zoom-пайплайн Junior_IT")
    parser.add_argument("--once", action="store_true",
                        help="один тик (поведение по умолчанию)")
    parser.add_argument("--dry-run", action="store_true",
                        help="показать план действий, ничего не делая")
    args = parser.parse_args(argv)

    cfg = load_config(CONFIG_DIR / "zoom-pipeline.toml",
                      CONFIG_DIR / "zoom.env")
    api = ZoomApi(cfg.zoom_account_id, cfg.zoom_client_id,
                  cfg.zoom_client_secret)
    state = State.load(cfg.state_path)

    def log(message):
        print(message, file=sys.stderr)

    if args.dry_run:
        since_meetings = api.list_recordings(
            (date.today()).replace(day=1).isoformat())
        for m in since_meetings:
            print(f"{m.start_time[:10]} · {m.topic} · фаза: {state.phase(m.uuid)}")
        return 0

    run_tick(cfg, api, state, default_runner, date.today(), log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Уточнение к dry-run: показывает записи с начала месяца и их фазы, ничего
не скачивая и не меняя state — этого достаточно для ручной проверки
«пайплайн видит записи и понимает, где остановился».

- [ ] **Step 4: Прогнать тесты**

Run: `cd tools && .venv/bin/python -m pytest tests/test_zoom_pipeline.py -v`
Expected: PASS (6 тестов)

- [ ] **Step 5: Полный прогон tools и коммит**

Run: `cd tools && .venv/bin/python -m pytest`
Expected: PASS

```bash
git add tools/zoom_pipeline/ tools/tests/test_zoom_pipeline.py
git commit -m "zoom: оркестратор фаз, промпт анализа, CLI"
```

---

### Task 5: provisioning, gitignore и инструкция запуска

**Files:**
- Create: `provisioning/zoom-pipeline/com.juniorit.zoom-pipeline.plist`
- Create: `provisioning/zoom-pipeline/zoom.env.example`
- Create: `provisioning/zoom-pipeline/zoom-pipeline.toml.example`
- Create: `provisioning/zoom-pipeline/setup.md`
- Modify: `.gitignore` (добавить `meta/drafts/`)

**Interfaces:**
- Consumes: CLI из Task 4 (`tools/.venv/bin/python -m zoom_pipeline.pipeline`).

- [ ] **Step 1: Файлы provisioning**

`com.juniorit.zoom-pipeline.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.juniorit.zoom-pipeline</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/dmitrymorozov/Projects/Junior_IT/tools/.venv/bin/python</string>
    <string>-m</string>
    <string>zoom_pipeline.pipeline</string>
    <string>--once</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/Users/dmitrymorozov/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>PYTHONPATH</key>
    <string>/Users/dmitrymorozov/Projects/Junior_IT/tools</string>
  </dict>
  <key>WorkingDirectory</key>
  <string>/Users/dmitrymorozov/Projects/Junior_IT/tools</string>
  <key>StartInterval</key>
  <integer>3600</integer>
  <key>RunAtLoad</key>
  <false/>
  <key>StandardOutPath</key>
  <string>/Users/dmitrymorozov/Library/Logs/junior-it-zoom.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/dmitrymorozov/Library/Logs/junior-it-zoom.log</string>
</dict>
</plist>
```

`zoom.env.example`:

```
# ~/.junior_it/zoom.env — секреты Server-to-Server OAuth app
ZOOM_ACCOUNT_ID=your-account-id
ZOOM_CLIENT_ID=your-client-id
ZOOM_CLIENT_SECRET=your-client-secret
```

`zoom-pipeline.toml.example`:

```toml
# ~/.junior_it/zoom-pipeline.toml
repo_root = "/Users/dmitrymorozov/Projects/Junior_IT"
backup_dir = "/Volumes/backup/JuniorIT/recordings"
retention_days = 30
# стемы имён учеников: «Наст» накрывает Настя/Насте/Настю
student_stems = ["Наст"]
```

`setup.md` — разделы (короткие, командный стиль):

1. **Zoom-аккаунт:** Settings → Recording: включить Cloud recording и
   Audio transcript; в повторяющейся встрече курса — Record automatically
   in the cloud. Плагинов и app в клиент не ставится.
2. **Marketplace:** marketplace.zoom.us → Develop → Build App →
   Server-to-Server OAuth; скопировать Account ID / Client ID /
   Client Secret; Scopes → добавить `cloud_recording:read:list_user_recordings:admin`,
   `cloud_recording:read:recording:admin`, `cloud_recording:delete:recording:admin`
   (имена в консоли Zoom могут отличаться редакцией — брать read+delete
   на recording); Activate.
3. **Мак:** `mkdir -p ~/.junior_it`, скопировать оба example-файла без
   суффикса, заполнить; смонтировать шару QNAP (Finder → Cmd-K →
   `smb://<nas>/backup`, галка «повторно подключать при входе»);
   `cd tools && .venv/bin/pip install -r requirements.txt`.
4. **Проверка руками:** `PYTHONPATH=tools tools/.venv/bin/python -m
   zoom_pipeline.pipeline --dry-run` — список записей и фаз; затем
   `--once` — первый полный прогон (первый запуск mlx-whisper скачает
   модель, это долго).
5. **Автозапуск:** `cp provisioning/zoom-pipeline/com.juniorit.zoom-pipeline.plist
   ~/Library/LaunchAgents/ && launchctl load
   ~/Library/LaunchAgents/com.juniorit.zoom-pipeline.plist`. Лог:
   `~/Library/Logs/junior-it-zoom.log`.

- [ ] **Step 2: .gitignore**

Добавить строку `meta/drafts/` (черновики содержат ссылки с passcode).
Проверить: `git status` не показывает `meta/drafts/`, если создать там
пробный файл (удалить после проверки).

- [ ] **Step 3: Проверка plist**

Run: `plutil -lint provisioning/zoom-pipeline/com.juniorit.zoom-pipeline.plist`
Expected: `OK`

- [ ] **Step 4: Полный прогон tools**

Run: `cd tools && .venv/bin/python -m pytest`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add provisioning/zoom-pipeline/ .gitignore
git commit -m "zoom: launchd-агент, примеры конфигов, инструкция запуска"
```

---

### Task 6: приёмка с Димасом (ручной чекпоинт, не субагентный)

Кода нет — только прогон по `setup.md` на живом аккаунте:

- [ ] Димас создаёт S2S OAuth app и заполняет `~/.junior_it/zoom.env`.
- [ ] `--dry-run` показывает реальные записи аккаунта.
- [ ] `--once` на последней записи проходит все фазы: файлы в
  `recordings/<дата>/`, копия на NAS, `transcript.txt`, черновик в
  `meta/drafts/`, macOS-уведомление.
- [ ] Черновик читается: тайминги осмысленны, сообщение в MAX без
  запрещённой лексики, имена детей не просочились (grep по именам).
- [ ] `launchctl load`, через час в логе — штатный тик.

Retention проверяется жизнью через 30 дней — не блокирует приёмку.
