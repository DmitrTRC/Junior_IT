import json

from courier.registry import Registry


def test_bind_consumes_code_and_records_id(tmp_path):
    reg = Registry(tmp_path / "registry.json")
    reg.add_code("KX7-42", "s-7f3a")
    assert reg.bind("KX7-42", 123) == "s-7f3a"
    assert reg.who(123) == "s-7f3a" and reg.telegram_id_of("s-7f3a") == 123
    assert reg.bind("KX7-42", 999) is None                # код одноразовый
    saved = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
    assert saved == {"codes": {}, "ids": {"123": "s-7f3a"}}


def test_unknown_code_and_id(tmp_path):
    reg = Registry(tmp_path / "registry.json")
    assert reg.bind("nope", 1) is None and reg.who(1) is None and reg.telegram_id_of("x") is None


def test_rebind_same_person_new_phone(tmp_path):
    reg = Registry(tmp_path / "registry.json")
    reg.add_code("A", "s-1")
    reg.bind("A", 10)
    reg.add_code("B", "s-1")
    assert reg.bind("B", 20) == "s-1"
    assert reg.who(10) is None and reg.who(20) == "s-1"   # старый телефон отвязан


def test_load_existing(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text('{"codes": {"C": "s-2"}, "ids": {"5": "s-1"}}', encoding="utf-8")
    reg = Registry(path)
    assert reg.who(5) == "s-1" and reg.codes == {"C": "s-2"}
