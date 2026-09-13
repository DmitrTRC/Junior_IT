import json
from pathlib import Path

from validate_quizzes import validate

BANK_DIR = "textbook/quizzes"


def q(qid="07-1-01", qtype="single", **over):
    base = {
        "id": qid, "source": "7 кл, гл. 1, тест 1", "type": qtype,
        "q": "Вопрос?", "options": ["а", "б", "в"], "answer": 0,
        "why": "Потому.", "terms": [],
    }
    base.update(over)
    return base


def write_bank(root, files):
    d = root / BANK_DIR
    d.mkdir(parents=True)
    manifest = {"banks": [{
        "id": "07-1", "grade": 7, "chapter": 1, "title": "Глава 1",
        "files": sorted(files),
    }]}
    (d / "index.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    for name, questions in files.items():
        payload = {"grade": 7, "chapter": 1,
                   "paragraph": name.removeprefix("07-").removesuffix(".json"),
                   "title": "Параграф", "questions": questions}
        (d / name).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def three(prefix):
    return [q(f"{prefix}-{i}") for i in range(3)]


def test_valid_bank_passes(tmp_path):
    write_bank(tmp_path, {"07-1.1.json": three("07-1")})
    assert validate(tmp_path) == []


def test_empty_why_fails(tmp_path):
    bad = three("07-1")
    bad[0]["why"] = "  "
    write_bank(tmp_path, {"07-1.1.json": bad})
    assert any("why" in e for e in validate(tmp_path))


def test_answer_out_of_range_fails(tmp_path):
    bad = three("07-1")
    bad[1]["answer"] = 3
    write_bank(tmp_path, {"07-1.1.json": bad})
    assert any("answer" in e for e in validate(tmp_path))


def test_duplicate_ids_across_files_fail(tmp_path):
    write_bank(tmp_path, {"07-1.1.json": three("07-1"),
                          "07-1.2.json": three("07-1")})
    assert any("id" in e for e in validate(tmp_path))


def test_fewer_than_three_questions_fail(tmp_path):
    write_bank(tmp_path, {"07-1.1.json": three("07-1")[:2]})
    assert any("меньше 3" in e for e in validate(tmp_path))


def test_missing_file_from_manifest_fails(tmp_path):
    write_bank(tmp_path, {"07-1.1.json": three("07-1")})
    (tmp_path / BANK_DIR / "07-1.1.json").unlink()
    assert validate(tmp_path)


def test_order_answer_must_be_permutation(tmp_path):
    bad = three("07-1")
    bad[2] = q("07-1-2", "order", options=["а", "б", "в"], answer=[0, 0, 1])
    write_bank(tmp_path, {"07-1.1.json": bad})
    assert any("перестановк" in e for e in validate(tmp_path))


def test_match_answer_length_and_range(tmp_path):
    bad = three("07-1")
    bad[2] = q("07-1-2", "match",
               options={"left": ["а", "б"], "right": ["x", "y", "z"]},
               answer=[0, 5])
    write_bank(tmp_path, {"07-1.1.json": bad})
    assert validate(tmp_path)
