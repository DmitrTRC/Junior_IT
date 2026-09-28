import pytest
import yaml

from comms.identity import Identity, IdentityError


def test_ensure_creates_ids_and_codes(tmp_path):
    ident = Identity(tmp_path / "comms.yml")
    alice = ident.ensure("alice")
    assert alice.comms_id.startswith("s-") and len(alice.comms_id) == 6 and alice.code is None
    code = ident.new_code(alice)
    assert len(code) == 6 and code[3] == "-" and ident.by_student("alice").code == code
    parent = ident.ensure("alice", role="parent")
    assert parent.comms_id.startswith("p-") and ident.ensure("alice") is alice
    saved = yaml.safe_load((tmp_path / "comms.yml").read_text(encoding="utf-8"))
    assert saved["people"][0]["student"] == "alice" and saved["people"][1]["role"] == "parent"


def test_bind_and_github(tmp_path):
    ident = Identity(tmp_path / "comms.yml")
    alice = ident.ensure("alice")
    ident.new_code(alice)
    assert ident.bind(alice.comms_id, 777).telegram_id == 777 and alice.code is None
    assert ident.bind("s-nope", 1) is None
    ident.set_github("alice", "owner/jit-hw-alice")
    again = Identity(tmp_path / "comms.yml")
    assert again.by_comms_id(alice.comms_id).github == "owner/jit-hw-alice"
    assert again.by_student("alice", role="parent") is None


def test_corrupt_yaml_raises_identity_error(tmp_path):
    path = tmp_path / "comms.yml"
    path.write_text("people: [unclosed", encoding="utf-8")
    with pytest.raises(IdentityError):
        Identity(path)


def test_non_mapping_person_raises(tmp_path):
    path = tmp_path / "comms.yml"
    path.write_text(yaml.safe_dump({"people": ["just a string"]}, allow_unicode=True), encoding="utf-8")
    with pytest.raises(IdentityError):
        Identity(path)
