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
