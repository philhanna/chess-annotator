from pathlib import Path

from annotate.adapters import web_app


def test_frontend_root_points_to_top_level_frontend_dir() -> None:
    root = web_app.frontend_root()

    assert root == Path(__file__).resolve().parents[1] / "frontend"


def test_create_session_uses_frontend_root() -> None:
    session = web_app.create_session()

    assert session.frontend_root == web_app.frontend_root()


def test_asset_content_type_for_css() -> None:
    content_type = web_app.asset_content_type(Path("frontend/app.css"))

    assert content_type == "text/css"


def test_require_string_accepts_string_payload() -> None:
    assert web_app.require_string({"name": "demo"}, "name") == "demo"


def test_require_int_accepts_integer_payload() -> None:
    assert web_app.require_int({"ply": 12}, "ply") == 12
