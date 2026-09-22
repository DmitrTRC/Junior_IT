import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "group_status.py"


def _prepare(tmp_path, store_body):
    """Копия скрипта + фиктивный journal-пакет, чтобы не трогать реальный tools/journal."""
    shutil.copy(SCRIPT, tmp_path / "group_status.py")
    pkg = tmp_path / "journal"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "model.py").write_text("class JournalError(Exception):\n    pass\n", encoding="utf-8")
    (pkg / "store.py").write_text(store_body, encoding="utf-8")


def test_reraises_unrelated_import_error(tmp_path):
    _prepare(tmp_path, "raise ModuleNotFoundError(\"No module named 'something_else'\", name='something_else')\n")
    proc = subprocess.run([sys.executable, "group_status.py"], capture_output=True, text=True, cwd=str(tmp_path))
    assert proc.returncode != 0
    assert "something_else" in proc.stderr
    assert "tools/.venv" not in proc.stdout


def test_placeholder_when_yaml_missing(tmp_path):
    _prepare(tmp_path, "raise ModuleNotFoundError(\"No module named 'yaml'\", name='yaml')\n")
    proc = subprocess.run([sys.executable, "group_status.py"], capture_output=True, text=True, cwd=str(tmp_path))
    assert proc.returncode == 0
    assert "tools/.venv" in proc.stdout
