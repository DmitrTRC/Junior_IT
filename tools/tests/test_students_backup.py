import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "students_backup.sh"


def _run(env_extra, tmp_path):
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(tmp_path), **env_extra}
    return subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env)


def test_skips_when_share_not_mounted(tmp_path):
    src = tmp_path / "students"
    src.mkdir()
    proc = _run({"JUNIOR_IT_STUDENTS": str(src), "STUDENTS_BACKUP_SHARE": str(tmp_path / "nope")}, tmp_path)
    assert proc.returncode == 0 and "не смонтирована" in proc.stdout


def test_syncs_and_deletes_stale(tmp_path):
    src, share = tmp_path / "students", tmp_path / "share"
    (src / "journal").mkdir(parents=True)
    (src / "roster.yml").write_text("students: []\n", encoding="utf-8")
    (src / "journal" / "2026-09-20.yml").write_text("date: 2026-09-20\n", encoding="utf-8")
    dest = share / "JuniorIT" / "students"
    dest.mkdir(parents=True)
    (dest / "stale.yml").write_text("x", encoding="utf-8")
    proc = _run({"JUNIOR_IT_STUDENTS": str(src), "STUDENTS_BACKUP_SHARE": str(share)}, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert (dest / "roster.yml").exists() and (dest / "journal" / "2026-09-20.yml").exists()
    assert not (dest / "stale.yml").exists()
    assert "ok 2 файлов" in proc.stdout
