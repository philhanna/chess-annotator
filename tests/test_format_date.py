# tests.test_format_date
from annotate.domain.render_model import format_date


def test_format_date_full():
    assert format_date("2026.03.30") == "30 Mar 2026"


def test_format_date_no_day():
    assert format_date("2026.03.??") == "Mar 2026"


def test_format_date_year_only():
    assert format_date("2026.??.??") == "2026"


def test_format_date_all_missing():
    assert format_date("????.??.??") == ""
