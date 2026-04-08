from annotate.cli import session


def cmd_close(_tokens: list[str]) -> None:
    session.do_close()
