from app.core.sanitize import clean_text, escape_like


def test_clean_text_strips_tags_controls_and_extra_spaces():
    assert clean_text("<script>alert(1)</script>  Hi\x00   there ") == "alert(1) Hi there"


def test_clean_text_single_line_by_default():
    assert clean_text("a\nb") == "a b"
    assert clean_text("a\nb", multiline=True) == "a\nb"


def test_escape_like():
    assert escape_like("50%_off") == "50\\%\\_off"
