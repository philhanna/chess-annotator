"""FastAPI application factory for the annotate SPA."""

from __future__ import annotations

from pathlib import Path

from annotate.service import AnnotateSession


def frontend_root() -> Path:
    """Return the top-level frontend directory."""

    return Path(__file__).resolve().parents[3] / "frontend"


def create_session() -> AnnotateSession:
    """Create a session with the configured frontend root."""

    return AnnotateSession(frontend_root=frontend_root())


def create_app():
    """Create and return the FastAPI app.

    FastAPI is imported lazily so modules can still be imported in environments
    where the dependency has not been installed yet.
    """

    try:
        from fastapi import FastAPI
        from fastapi.responses import FileResponse
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised at runtime
        raise RuntimeError(
            "fastapi is required to run chess-annotate. Install project "
            "dependencies before launching the app."
        ) from exc

    session = create_session()
    app = FastAPI(title="chess-annotate")
    app.state.annotate_session = session

    @app.get("/api/session")
    def get_session() -> dict[str, object]:
        """Return the current high-level SPA session state."""

        return session.snapshot().__dict__

    @app.get("/")
    def index():
        """Serve the SPA entry point."""

        return FileResponse(session.frontend_root / "index.html")

    @app.get("/app.css")
    def app_css():
        """Serve the SPA stylesheet."""

        return FileResponse(session.frontend_root / "app.css")

    @app.get("/app.js")
    def app_js():
        """Serve the SPA JavaScript."""

        return FileResponse(session.frontend_root / "app.js")

    return app

