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


def test_stem_group_maps_to_one_student():
    # группа = точные словоформы одного ребёнка -> один номер
    text = "Мария пишет, а Маше помогает Матвей. Машу похвалили."
    stems = [["Мария", "Марии", "Маша", "Маше", "Машу", "Маши"], "Матве"]
    assert anonymize(text, stems) == (
        "Ученик 1 пишет, а Ученик 1 помогает Ученик 2. Ученик 1 похвалили."
    )


def test_exact_forms_do_not_eat_similar_words():
    # точные формы (включая «Маши») не трогают «машину»/«машина»
    text = "Маша запускает виртуальную машину, у Маши машина работает."
    assert anonymize(text, [["Маша", "Маши"]]) == (
        "Ученик 1 запускает виртуальную машину, у Ученик 1 машина работает."
    )
