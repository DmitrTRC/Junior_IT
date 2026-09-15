from zoom_pipeline.anonymize import anonymize


def test_replaces_declensions_case_insensitive():
    text = "Настя пишет код. Скажи Насте. НАСТЮ похвалили."
    assert anonymize(text, ["Наст"]) == (
        "Ученик 1 пишет код. Скажи Ученик 1. Ученик 1 похвалили."
    )


def test_numbers_stems_in_order():
    text = "Вика помогла Маше."
    assert anonymize(text, ["Вик", "Маш"]) == "Ученик 1 помогла Ученик 2."


def test_does_not_touch_other_words():
    # стем должен матчиться только с начала слова
    text = "Полынастил доски."  # «наст» внутри слова
    assert anonymize(text, ["Наст"]) == "Полынастил доски."


def test_empty_stems_noop():
    assert anonymize("Привет всем", []) == "Привет всем"
