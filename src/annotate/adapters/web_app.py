"""Standard-library HTTP server for the annotate SPA."""

from __future__ import annotations

import json
import mimetypes
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from annotate.service import AnnotateSession


def frontend_root() -> Path:
    """Return the top-level frontend directory."""

    return Path(__file__).resolve().parents[3] / "frontend"


def create_session() -> AnnotateSession:
    """Create a session with the configured frontend root."""

    return AnnotateSession(frontend_root=frontend_root())


def asset_content_type(path: Path) -> str:
    """Return the best-effort content type for a frontend asset."""

    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


class AnnotateHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying annotate session state."""

    def __init__(
        self,
        server_address: tuple[str, int],
        session: AnnotateSession,
    ) -> None:
        super().__init__(server_address, AnnotateRequestHandler)
        self.annotate_session = session


class AnnotateRequestHandler(BaseHTTPRequestHandler):
    """Request handler for the initial annotate SPA routes."""

    server: AnnotateHTTPServer

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        """Serve JSON session data and static SPA assets."""

        if self.path == "/api/session":
            self._send_json(self.server.annotate_session.snapshot().__dict__)
            return

        if self.path == "/":
            self._send_asset("index.html")
            return

        if self.path in {"/app.css", "/app.js"}:
            self._send_asset(self.path.lstrip("/"))
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        """Handle simple POST routes for the SPA."""

        if self.path == "/api/close":
            self._send_json({"status": "closing"})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        """Silence default request logging for the local app."""

    def _send_json(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_asset(self, relative_name: str) -> None:
        path = self.server.annotate_session.frontend_root / relative_name
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", asset_content_type(path))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(host: str = "127.0.0.1", port: int = 0) -> AnnotateHTTPServer:
    """Create the annotate HTTP server bound to the given address."""

    return AnnotateHTTPServer((host, port), session=create_session())
