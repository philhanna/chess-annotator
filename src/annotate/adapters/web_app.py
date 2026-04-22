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

        if self.path == "/api/game-view":
            try:
                self._send_json(self.server.annotate_session.current_view())
            except ValueError as exc:
                self._send_json_error(HTTPStatus.BAD_REQUEST, str(exc))
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

        if self.path == "/api/open":
            payload = self._read_json()
            if payload is None:
                return
            try:
                display_name = require_string(payload, "display_name")
                pgn_text = require_string(payload, "pgn_text")
                self._send_json(
                    self.server.annotate_session.open_pgn(
                        display_name=display_name,
                        pgn_text=pgn_text,
                    )
                )
            except ValueError as exc:
                self._send_json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        if self.path == "/api/select-game":
            payload = self._read_json()
            if payload is None:
                return
            try:
                self._send_json(
                    self.server.annotate_session.select_game(
                        require_int(payload, "game_index")
                    )
                )
            except ValueError as exc:
                self._send_json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        if self.path == "/api/select-ply":
            payload = self._read_json()
            if payload is None:
                return
            try:
                self._send_json(
                    self.server.annotate_session.select_ply(
                        require_int(payload, "ply")
                    )
                )
            except ValueError as exc:
                self._send_json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

        if self.path == "/api/navigate":
            payload = self._read_json()
            if payload is None:
                return
            try:
                self._send_json(
                    self.server.annotate_session.navigate(
                        require_string(payload, "action")
                    )
                )
            except ValueError as exc:
                self._send_json_error(HTTPStatus.BAD_REQUEST, str(exc))
            return

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

    def _send_json_error(self, status: HTTPStatus, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(status)
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

    def _read_json(self) -> dict[str, object] | None:
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self._send_json_error(HTTPStatus.BAD_REQUEST, "missing Content-Length")
            return None

        try:
            raw_length = int(content_length)
        except ValueError:
            self._send_json_error(HTTPStatus.BAD_REQUEST, "invalid Content-Length")
            return None

        body = self.rfile.read(raw_length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json_error(HTTPStatus.BAD_REQUEST, "invalid JSON body")
            return None

        if not isinstance(payload, dict):
            self._send_json_error(HTTPStatus.BAD_REQUEST, "JSON body must be an object")
            return None

        return payload


def require_string(payload: dict[str, object], key: str) -> str:
    """Return a required string from a decoded JSON payload."""

    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"expected string field: {key}")
    return value


def require_int(payload: dict[str, object], key: str) -> int:
    """Return a required int from a decoded JSON payload."""

    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"expected integer field: {key}")
    return value


def create_server(host: str = "127.0.0.1", port: int = 0) -> AnnotateHTTPServer:
    """Create the annotate HTTP server bound to the given address."""

    return AnnotateHTTPServer((host, port), session=create_session())
