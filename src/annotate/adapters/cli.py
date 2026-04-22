"""Command-line entry point for launching the annotate web application."""

from __future__ import annotations

import argparse
import webbrowser

from annotate.adapters.web_app import create_server


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
    server = create_server()
    host, port = server.server_address[:2]
    webbrowser.open(f"http://{host}:{port}/")

    try:
        server.serve_forever()
    finally:
        server.server_close()
