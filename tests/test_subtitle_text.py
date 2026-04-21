# tests.test_subtitle_text
from annotate.domain.game_headers import GameHeaders
from annotate.domain.render_model import subtitle_text


def test_subtitle_event_and_date():
    headers = GameHeaders(
        white="",
        black="",
        event="World Championship",
        date="2026.03.30",
        opening="",
    )
    assert subtitle_text(headers) == "World Championship, 30 Mar 2026"


def test_subtitle_event_only():
    headers = GameHeaders(
        white="",
        black="",
        event="Blitz Open",
        date="????.??.??",
        opening="",
    )
    assert subtitle_text(headers) == "Blitz Open"


def test_subtitle_date_only():
    headers = GameHeaders(
        white="",
        black="",
        event="",
        date="2026.??.??",
        opening="",
    )
    assert subtitle_text(headers) == "2026"


def test_subtitle_neither():
    headers = GameHeaders(
        white="",
        black="",
        event="",
        date="????.??.??",
        opening="",
    )
    assert subtitle_text(headers) is None
