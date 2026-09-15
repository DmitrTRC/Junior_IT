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
