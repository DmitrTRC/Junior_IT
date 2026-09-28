import json

from comms import cli
from comms.identity import Identity
from comms.queue import read_items


def test_code_creates_person_and_control_item(tmp_path, journal_root, capsys):
    local = tmp_path / "comms"
    rc = cli.run(["code", "alice"], students_root=journal_root, local_dir=local)
    assert rc == 0
    code = capsys.readouterr().out.strip().split()[-1]
    person = Identity(journal_root / "comms.yml").by_student("alice")
    assert person.code == code
    control = read_items(local / "outbox-staging")[0].data
    assert control["action"] == "add_code" and control["code"] == code and control["comms_id"] == person.comms_id


def test_code_parent_and_unknown_student(tmp_path, journal_root):
    local = tmp_path / "comms"
    assert cli.run(["code", "alice", "--parent"], students_root=journal_root, local_dir=local) == 0
    assert Identity(journal_root / "comms.yml").by_student("alice", role="parent").code
    assert cli.run(["code", "zed"], students_root=journal_root, local_dir=local) == 2


def test_github_and_status(tmp_path, journal_root, capsys):
    local = tmp_path / "comms"
    assert cli.run(["github", "alice", "o/r"], students_root=journal_root, local_dir=local) == 0
    assert Identity(journal_root / "comms.yml").by_student("alice").github == "o/r"
    (local).mkdir(exist_ok=True)
    (local / "status.json").write_text(json.dumps({"online": True, "sizes": {"outbox": 0, "inbox": 2, "failed": 0}}), encoding="utf-8")
    assert cli.run(["status"], students_root=journal_root, local_dir=local) == 0
    assert "входящих 2" in capsys.readouterr().out
