import requests
import webbrowser

def import_pgn_to_lichess(pgn: str, api_token: str = None, move: int = None) -> str:
    """
    Imports a PGN to Lichess and returns the game URL.
    Optionally jump to a specific move number (full moves, not plies).
    """
    headers = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    response = requests.post(
        "https://lichess.org/api/import",
        data={"pgn": pgn},
        headers=headers,
    )
    response.raise_for_status()
    url = response.url
    
    if move is not None:
        url = f"{url}#{move}"  # move is a ply count (half-moves)

    return url

pgn = """[Event "?"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0"""

# Jump to after White's 2nd move (ply 3)
url = import_pgn_to_lichess(pgn, move=3)
print(url)
webbrowser.open(url)