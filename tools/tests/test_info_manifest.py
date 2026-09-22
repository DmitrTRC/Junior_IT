import sys
from pathlib import Path

import pytest

ENGINE = Path.home() / ".local" / "lib" / "terminal-commander" / "cockpit"
MANIFEST = Path(__file__).resolve().parents[2] / ".zellij" / "info.yml"


def test_info_manifest_loads_in_engine():
    if not (ENGINE / "cockpit" / "info" / "manifest.py").exists():
        pytest.skip("движок info-панели не задеплоен")
    sys.path.insert(0, str(ENGINE))
    from cockpit.info.manifest import load_info_manifest
    manifest = load_info_manifest(MANIFEST)
    assert manifest.warnings == []
    assert [b.id for b in manifest.placed()] == ["lesson", "students", "clock", "homework", "readiness", "course", "git"]
    for box in manifest.placed():
        if box.type == "command":
            assert box.run.startswith("tools/.venv/bin/python tools/info/cli.py ")
