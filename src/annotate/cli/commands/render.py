# annotate.cli.commands.render
from annotate.cli import session
from annotate.use_cases import UseCaseError


def cmd_render(tokens: list[str]) -> None:
    if session.state.open:
        game_id = session.require_open_session()
    elif tokens:
        game_id = tokens[0]
    else:
        session.err("Usage: render <game-id>")
        return
    if game_id is None:
        return
    config = session.get_config()
    try:
        output_path = session.get_service().render_pdf(
            game_id=game_id,
            diagram_size=config.diagram_size,
            page_size=config.page_size,
        )
    except (UseCaseError, ValueError) as exc:
        session.err(str(exc))
        return
    session.print(f"Rendered: {output_path}")
