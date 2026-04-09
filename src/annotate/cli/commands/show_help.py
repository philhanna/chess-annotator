from annotate.cli import session

_HELP_NO_SESSION = """\
Commands (no session open):
  import [file.pgn]         Import a game from a PGN file and open it
  open <game-id>            Open or resume a game
  list                      List games in the store
  copy <source> <new>       Save game as a new game id
  delete <game-id>          Delete a game
  render <game-id>          Render a game to output.pdf
  see <game-id>             Upload a game to Lichess and open the URL
  help                      Show this help
  quit                      Exit"""

_HELP_SESSION = """\
Commands (session open):
  list                      List segments for the open game
  <number>                  Select a segment by number
  view                      View the current segment
  split <move> [label]      Add a turning point
  merge <move>              Remove a turning point
  label <text>              Set the current segment label
  annotate                  Edit the current segment annotation in $EDITOR
  diagram [on|off]          Toggle or set the current segment diagram flag
  save                      Save the open game
  close                     Close the current game
  copy <new-game-id>        Save the current game as a new game id
  render                    Render the current game to output.pdf
  see                       Upload the current game to Lichess and open the URL
  json                      Print the working annotation JSON summary
  help                      Show this help
  quit                      Close the current game and exit"""


def cmd_help(_tokens: list[str]) -> None:
    session.print(_HELP_SESSION if session.state.open else _HELP_NO_SESSION)
