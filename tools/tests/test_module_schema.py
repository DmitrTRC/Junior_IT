from module_schema import check_fields


def valid_module():
    return {
        "id": "python/m-04-branching",
        "title": "Ветвление (branching): if / elif / else",
        "track": "python",
        "level": "core",
        "minutes": 25,
        "textbook": ["8:3.5", "8:5.4"],
        "terms": [{"ru": "ветвление", "en": "branching"}],
    }


def test_valid_module_has_no_errors():
    assert check_fields(valid_module()) == []


def test_missing_required_field_is_reported():
    data = valid_module()
    del data["minutes"]
    errors = check_fields(data)
    assert any("minutes" in e for e in errors)


def test_unknown_track_is_reported():
    data = valid_module()
    data["track"] = "informatika"
    errors = check_fields(data)
    assert any("informatika" in e for e in errors)


def test_unknown_level_is_reported():
    data = valid_module()
    data["level"] = "hard"
    errors = check_fields(data)
    assert any("hard" in e for e in errors)


def test_minutes_must_be_positive_int():
    data = valid_module()
    data["minutes"] = 0
    assert check_fields(data) != []
    data["minutes"] = "25"
    assert check_fields(data) != []


def test_textbook_reference_format_is_checked():
    data = valid_module()
    data["textbook"] = ["8-3.5"]
    errors = check_fields(data)
    assert any("8-3.5" in e for e in errors)


def test_term_without_english_is_reported():
    data = valid_module()
    data["terms"] = [{"ru": "ветвление"}]
    errors = check_fields(data)
    assert any("en" in e for e in errors)


def test_non_dict_input_is_reported():
    assert check_fields("не словарь") != []
