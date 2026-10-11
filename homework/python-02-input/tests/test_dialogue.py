"""Teacher checks: DIALOGUE_PATH points to the student's dialogue.py."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def dialogue_path():
    candidate = os.environ.get("DIALOGUE_PATH")
    if not candidate:
        pytest.skip("Set DIALOGUE_PATH to the solution file")
    path = Path(candidate).expanduser().resolve()
    assert path.is_file(), f"Solution file not found: {path}"
    return path


def run_dialogue(path, nickname, genre):
    result = subprocess.run(
        [sys.executable, str(path)],
        input=f"{nickname}\n{genre}\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=path.parent,
        timeout=5,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert result.returncode == 0, result.stderr
    assert nickname in result.stdout, "The output must include the entered nickname"
    assert genre in result.stdout, "The output must include the entered genre"
    return result.stdout


def test_answers_change_between_runs(dialogue_path):
    first = run_dialogue(dialogue_path, "Falcon_73", "Mystery_19")
    second = run_dialogue(dialogue_path, "Orchid_46", "Adventure_82")
    assert "Orchid_46" not in first and "Adventure_82" not in first
    assert "Falcon_73" not in second and "Mystery_19" not in second


def test_unicode_and_spaces_are_preserved(dialogue_path):
    run_dialogue(dialogue_path, "Лунный лис", "научная фантастика")


def test_digit_and_punctuation_answers_are_text(dialogue_path):
    run_dialogue(dialogue_path, "0042", "игры / истории!")
