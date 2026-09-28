import json
from datetime import datetime, timedelta

import pytest

from courier.queue import BOXES, Queue, new_id


def test_new_id_is_sortable_and_unique():
    a, b = new_id(), new_id()
    assert a < b and len(a) == 30 and a[21] == "-"


def test_put_writes_files_before_json_and_returns_id(tmp_path):
    q = Queue(tmp_path)
    item_id = q.put("inbox", {"kind": "photo", "text": ""}, files={"photo.jpg": b"\xff\xd8"})
    assert (tmp_path / "inbox" / f"{item_id}.json").is_file()
    assert (tmp_path / "inbox" / item_id / "photo.jpg").read_bytes() == b"\xff\xd8"
    data = json.loads((tmp_path / "inbox" / f"{item_id}.json").read_text(encoding="utf-8"))
    assert data["id"] == item_id and data["files"] == ["photo.jpg"]


def test_items_ignores_dirs_without_json_and_sorts(tmp_path):
    q = Queue(tmp_path)
    second = q.put("outbox", {"to": "teacher", "text": "b"})
    first_dir = tmp_path / "outbox" / "00000000T000000000000-deadbeef"
    first_dir.mkdir()                                   # вложения без JSON — элемент ещё пишется
    assert [i.id for i in q.items("outbox")] == [second]


def test_move_renames_json_and_files_dir(tmp_path):
    q = Queue(tmp_path)
    item_id = q.put("outbox", {"to": "group", "text": "x"}, files={"a.txt": b"1"})
    q.move(item_id, "outbox", "sent")
    assert not (tmp_path / "outbox" / f"{item_id}.json").exists()
    assert (tmp_path / "sent" / item_id / "a.txt").is_file()
    assert q.load("sent", item_id).data["text"] == "x"


def test_move_over_existing_dir(tmp_path):
    q = Queue(tmp_path)
    item_id = q.put("outbox", {"to": "group", "text": "x"}, files={"a.txt": b"new"})
    stale = tmp_path / "sent" / item_id
    stale.mkdir()
    (stale / "old.txt").write_bytes(b"old")               # хвост прошлой попытки в целевом каталоге
    q.move(item_id, "outbox", "sent")
    assert (tmp_path / "sent" / item_id / "a.txt").read_bytes() == b"new"
    assert not (tmp_path / "sent" / item_id / "old.txt").exists()


def test_save_rewrites_json(tmp_path):
    q = Queue(tmp_path)
    item = q.load("outbox", q.put("outbox", {"to": "group", "text": "x", "attempts": 0}))
    item.data["attempts"] = 3
    q.save(item, "outbox")
    assert q.load("outbox", item.id).data["attempts"] == 3


def test_find_sent_by_message(tmp_path):
    q = Queue(tmp_path)
    item_id = q.put("sent", {"to": "teacher", "text": "x", "message_id": 4711})
    assert q.find_sent_by_message(4711).id == item_id
    assert q.find_sent_by_message(1) is None


def test_pull_marker(tmp_path):
    q = Queue(tmp_path)
    now = datetime(2026, 9, 28, 12, 0)
    assert q.last_pull_age(now) is None
    q.touch_pull()
    age = q.last_pull_age(datetime.now() + timedelta(seconds=5))
    assert 4 <= age <= 60


def test_sizes_and_boxes_created(tmp_path):
    q = Queue(tmp_path)
    assert all((tmp_path / b).is_dir() for b in BOXES)
    q.put("inbox", {"kind": "text", "text": "hi"})
    assert q.sizes() == {"outbox": 0, "sending": 0, "sent": 0, "inbox": 1, "failed": 0}


def test_move_unknown_box_raises(tmp_path):
    with pytest.raises(ValueError):
        Queue(tmp_path).move("x", "outbox", "nowhere")


@pytest.mark.parametrize("bad", ["../evil.py", "sub/evil.py", "..", ".", ""])
def test_put_rejects_traversal(tmp_path, bad):
    q = Queue(tmp_path)
    with pytest.raises(ValueError):
        q.put("inbox", {"kind": "document"}, files={bad: b"x"})
    assert not (tmp_path / "evil.py").exists() and q.sizes()["inbox"] == 0
