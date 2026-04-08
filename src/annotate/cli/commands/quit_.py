# annotate.cli.commands.quit_
import sys

from annotate.cli import session


def cmd_quit(_tokens: list[str]) -> None:
    if session.state.open:
        if not session.do_close():
            return
    sys.exit(0)
