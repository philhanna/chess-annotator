"""Command-line entry point for launching the annotate web application."""

from __future__ import annotations

import argparse
import webbrowser

from annotate.adapters.web_app import create_server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and return command-line arguments for ``chess-annotate``."""

    parser = argparse.ArgumentParser(
        prog="chess-annotate",
        description="Launch the local chess annotation web application.",
    )
    parser.add_argument(
        "--browser",
        help="Browser name to use instead of the system default (for example: firefox, microsoft-edge, chrome).",
    )
    return parser.parse_args(argv)


def open_browser(url: str, browser_name: str | None = None) -> None:
    """Open the annotate UI in the requested browser."""

    if browser_name:
        try:
            controller = webbrowser.get(browser_name)
        except webbrowser.Error as exc:
            raise SystemExit(f"Unable to locate browser '{browser_name}': {exc}") from exc
        controller.open(url)
        return

    webbrowser.open(url)


def main() -> None:
    """Launch the local web server and open the browser UI."""

    args = parse_args()
    server = create_server()
    host, port = server.server_address[:2]
    url = f"http://{host}:{port}/"

    try:
        open_browser(url, browser_name=args.browser)
        server.serve_forever()
    finally:
        server.server_close()
