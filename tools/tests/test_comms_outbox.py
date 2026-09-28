from comms.outbox import Outbox, esc
from comms.queue import read_items


def test_outbox_items(tmp_path):
    box = Outbox(tmp_path / "staging")
    t = box.teacher("черновик", buttons=[("отправить", "send:1"), ("нет", "discard:1")], files={"a.py": b"1"})
    g = box.group("всем")
    p = box.person("s-1", "тебе")
    c = box.control_add_code("KX7-42", "s-1")
    items = {i.id: i.data for i in read_items(tmp_path / "staging")}
    assert items[t]["to"] == "teacher" and items[t]["buttons"] == [{"label": "отправить", "data": "send:1"},
                                                                   {"label": "нет", "data": "discard:1"}]
    assert items[t]["files"] == ["a.py"] and items[t]["parse_mode"] == "HTML"
    assert items[g]["to"] == "group" and items[p]["to"] == "s-1" and items[p]["buttons"] == []
    assert items[c] == {**items[c], "to": "courier", "action": "add_code", "code": "KX7-42", "comms_id": "s-1"}
    assert esc("a < b & c") == "a &lt; b &amp; c"


def test_teacher_with_self_buttons(tmp_path):
    box = Outbox(tmp_path / "staging")
    item_id = box.teacher_with_self_buttons("x", [("ок", "send:{id}"), ("нет", "discard:{id}")], files={"a": b"1"})
    data = read_items(tmp_path / "staging")[0].data
    assert data["id"] == item_id and data["buttons"][0]["data"] == f"send:{item_id}" and data["files"] == ["a"]
