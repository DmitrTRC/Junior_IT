import json

from comms.queue import new_id, read_items, remove_item, write_item


def test_write_and_read(tmp_path):
    box = tmp_path / "outbox"
    item_id = write_item(box, {"to": "group", "text": "x"}, files={"a.py": b"1"})
    assert len(item_id) == 30 and (box / item_id / "a.py").read_bytes() == b"1"
    data = json.loads((box / f"{item_id}.json").read_text(encoding="utf-8"))
    assert data["files"] == ["a.py"] and data["id"] == item_id
    items = read_items(box)
    assert [i.id for i in items] == [item_id] and items[0].files_dir == box / item_id
    remove_item(box, item_id)
    assert read_items(box) == [] and not (box / item_id).exists()


def test_read_skips_dirs_without_json(tmp_path):
    box = tmp_path / "inbox"
    (box / "00000000T000000000000-deadbeef").mkdir(parents=True)
    assert read_items(box) == [] and new_id() > "2026"
