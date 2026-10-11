import fcntl
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

PHASES = ("downloaded", "backed_up", "transcribed", "analyzed", "cloud_deleted")
ANALYSIS_STATUSES = {"pending", "running", "retry_wait", "blocked", "exhausted", "succeeded"}


class StateError(RuntimeError):
    """State is invalid or an operation cannot safely proceed."""


def _analysis(status="pending", code=None):
    return dict(status=status, attempts=0, next_attempt_at=None, last_error_code=code)


def _utc(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise StateError("Analysis clock must be timezone-aware")
    return value.astimezone(timezone.utc)


def _timestamp(value):
    if not isinstance(value, str):
        raise StateError("Invalid analysis timestamp")
    try:
        return _utc(datetime.fromisoformat(value))
    except ValueError as exc:
        raise StateError("Invalid analysis timestamp") from exc


def _code(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value):
        raise StateError("Expected a normalized error code")
    return value


class State:
    def __init__(self, path, entries, analysis_block=None):
        self._path = Path(path)
        self._entries = entries
        self._analysis_block = analysis_block

    @classmethod
    def load(cls, path):
        path = Path(path)
        if not path.exists():
            return cls(path, {})
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise StateError("Cannot read pipeline state") from exc
        if not isinstance(raw, dict):
            raise StateError("State must be an object")
        legacy = "version" not in raw
        block = None
        if legacy:
            entries = raw
        else:
            if type(raw.get("version")) is not int or raw["version"] != 2 or set(raw) != {"version", "entries", "analysis_block"}:
                raise StateError("Unsupported state envelope")
            entries = raw["entries"]
            block = raw["analysis_block"]
            if block is not None:
                _code(block)
        if not isinstance(entries, dict):
            raise StateError("State entries must be an object")
        for uuid, entry in entries.items():
            if not uuid or not isinstance(entry, dict) or entry.get("phase") not in PHASES:
                raise StateError("Invalid state entry")
            for key in ("date", "topic", "share_url", "passcode", "start_time"):
                if key in entry and not isinstance(entry[key], str):
                    raise StateError("Invalid entry metadata")
            if legacy:
                entry.pop("analysis", None)
                if entry["phase"] == "transcribed":
                    entry["analysis"] = _analysis("blocked", "legacy_untracked")
            elif entry["phase"] == "transcribed" and "analysis" not in entry:
                raise StateError("Transcribed entry has no analysis history")
            if "analysis" in entry:
                cls._validate_analysis(entry["analysis"])
        return cls(path, entries, block)

    @staticmethod
    def _validate_analysis(analysis):
        if not isinstance(analysis, dict) or set(analysis) != {"status", "attempts", "next_attempt_at", "last_error_code"}:
            raise StateError("Invalid analysis history")
        status = analysis["status"]
        attempts = analysis["attempts"]
        if not isinstance(status, str) or status not in ANALYSIS_STATUSES or type(attempts) is not int or not 0 <= attempts <= 3:
            raise StateError("Invalid analysis status or attempts")
        deadline = analysis["next_attempt_at"]
        code = analysis["last_error_code"]
        if code is not None:
            _code(code)
        if status == "retry_wait":
            _timestamp(deadline)
            if attempts not in (1, 2) or code is None:
                raise StateError("Invalid retry history")
        elif deadline is not None:
            raise StateError("Unexpected retry deadline")
        if status == "pending" and (attempts != 0 or code is not None):
            raise StateError("Invalid pending history")
        if status in {"running", "succeeded"} and (attempts == 0 or code is not None):
            raise StateError("Invalid attempt history")
        if status in {"blocked", "exhausted"} and code is None:
            raise StateError("Missing failure code")
        if status == "exhausted" and attempts != 3:
            raise StateError("Invalid exhausted history")

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=self._path.name + ".", suffix=".tmp", dir=self._path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(dict(version=2, entries=self._entries, analysis_block=self._analysis_block),
                          stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self._path)
            directory = os.open(self._path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    @contextmanager
    def locked(self):
        """Hold a nonblocking process lock; caller must reload state after acquiring."""
        with self.locked_path(self._path):
            yield self

    @staticmethod
    @contextmanager
    def locked_path(path):
        """Lock before loading state, including missing or corrupt state files."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise StateError("Pipeline state is locked by another process") from exc
            yield
        finally:
            os.close(descriptor)

    @property
    def engine_block(self):
        """Normalized global blocking error code, or None when the engine is enabled."""
        return self._analysis_block

    def phase(self, uuid):
        return self._entries.get(uuid, {}).get("phase", "new")

    def meta(self, uuid):
        entry = self._entries.get(uuid, {})
        result = {"date": entry.get("date", ""), "topic": entry.get("topic", "")}
        result.update({key: entry[key] for key in ("share_url", "passcode", "start_time") if key in entry})
        return result

    def advance(self, uuid, phase, *, date="", topic="", share_url="", passcode="", start_time=""):
        if phase not in PHASES:
            raise StateError("Invalid pipeline phase")
        entry = self._entries.setdefault(uuid, {})
        entry["phase"] = phase
        for key, value in (("date", date), ("topic", topic), ("share_url", share_url), ("passcode", passcode), ("start_time", start_time)):
            if value and not entry.get(key):
                entry[key] = value
        if phase == "transcribed" and "analysis" not in entry:
            entry["analysis"] = _analysis()
        self._save()

    def uuids_in_phase(self, phase):
        return [u for u, e in self._entries.items() if e.get("phase") == phase]

    def analysis(self, uuid):
        """Return a snapshot; entries without analysis history return an empty dict."""
        return dict(self._entries.get(uuid, {}).get("analysis", {}))

    def analysis_allowed(self, uuid, now):
        now = _utc(now)
        analysis = self.analysis(uuid)
        if self.engine_block or self.phase(uuid) != "transcribed" or not analysis or analysis["attempts"] >= 3:
            return False
        return analysis["status"] == "pending" or (analysis["status"] == "retry_wait" and now >= _timestamp(analysis["next_attempt_at"]))

    def begin_analysis(self, uuid, now):
        if not self.analysis_allowed(uuid, now):
            raise StateError("Analysis is not allowed")
        analysis = self._entries[uuid]["analysis"]
        analysis.update(status="running", attempts=analysis["attempts"] + 1,
                        next_attempt_at=None, last_error_code=None)
        self._save()

    def _running(self, uuid):
        if self.phase(uuid) != "transcribed" or self.analysis(uuid).get("status") != "running":
            raise StateError("Analysis is not running")
        return self._entries[uuid]["analysis"]

    def fail_analysis(self, uuid, code, now, retryable=False, global_block=False, retry_at=None):
        now = _utc(now)
        code = _code(code)
        if retry_at is not None:
            retry_at = _utc(retry_at)
        analysis = self._running(uuid)
        status, deadline = "blocked", None
        if global_block:
            self._analysis_block = code
        elif retryable:
            if analysis["attempts"] >= 3:
                status = "exhausted"
            else:
                status = "retry_wait"
                deadline = now + timedelta(hours=(1, 4)[analysis["attempts"] - 1])
                if retry_at is not None:
                    deadline = max(deadline, retry_at)
        analysis.update(status=status, next_attempt_at=deadline.isoformat() if deadline else None,
                        last_error_code=code)
        self._save()

    def complete_analysis(self, uuid):
        analysis = self._running(uuid)
        analysis.update(status="succeeded", next_attempt_at=None, last_error_code=None)
        self._entries[uuid]["phase"] = "analyzed"
        self._save()

    def resume_analysis(self, uuid):
        if self.phase(uuid) != "transcribed":
            raise StateError("Only transcribed entries can resume analysis")
        self._entries[uuid]["analysis"] = _analysis()
        self._save()

    def resume_engine(self):
        self._analysis_block = None
        self._save()

    def recover_interrupted(self):
        changed = False
        for entry in self._entries.values():
            analysis = entry.get("analysis", {})
            if analysis.get("status") == "running":
                analysis.update(status="blocked", next_attempt_at=None, last_error_code="interrupted")
                changed = True
        if changed:
            self._save()
