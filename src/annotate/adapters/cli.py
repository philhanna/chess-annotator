"""Command-line entry point for launching the annotate web application."""

from __future__ import annotations

import argparse
import sys
import webbrowser

import uvicorn

from annotate.adapters.web_app import create_app


def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments for ``chess-annotate``."""

    parser = argparse.ArgumentParser(
        prog="chess-annotate",
        description="Launch the local chess annotation web application.",
    )
    return parser.parse_args()


def main() -> None:
    """Launch the local web server and open the browser UI."""

    parse_args()

    try:
        app = create_app()
    except RuntimeError as exc:
        print(f"chess-annotate: {exc}", file=sys.stderr)
        sys.exit(1)

    config = uvicorn.Config(app=app, host="127.0.0.1", port=0, log_level="info")
    server = uvicorn.Server(config)

    original_started = server.started

    def open_browser_once() -> None:
        if server.started and not original_started:
            sock = next(iter(server.servers)).sockets[0]
            host, port = sock.getsockname()[:2]
            webbrowser.open(f"http://{host}:{port}/")

    original_startup = server.startup

    async def startup_with_browser(sockets=None):
        await original_startup(sockets=sockets)
        open_browser_once()

    server.startup = startup_with_browser
    server.run()

