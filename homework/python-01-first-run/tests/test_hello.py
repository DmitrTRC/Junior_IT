"""Автопроверка python-01: hello.py печатает три строки, broken.py починен."""
import subprocess
import sys
from pathlib import Path

HW = Path(__file__).resolve().parents[1]


def run(name):
    return subprocess.run([sys.executable, str(HW / name)], capture_output=True, text=True, timeout=10)


def test_hello_prints_three_lines():
    result = run("hello.py")
    assert result.returncode == 0, result.stderr
    assert len([line for line in result.stdout.splitlines() if line.strip()]) == 3


def test_broken_runs_clean():
    result = run("broken.py")
    assert result.returncode == 0 and "Traceback" not in result.stderr
