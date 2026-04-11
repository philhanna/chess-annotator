from annotate.cli import session


def cmd_diagram(_tokens: list[str]) -> None:
    session.err(
        "The 'diagram' command has been removed. "
        "Embed [[diagram <move><w|b> [white|black]]] tokens in annotation text instead."
    )
