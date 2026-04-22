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
