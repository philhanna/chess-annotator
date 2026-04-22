# design.md: Detailed Design Document (v1.1)

This document provides a detailed technical design for the **chess-annotate** application, implementing the requirements specified in `requirements.md` and adhering to the PGN standards defined in `pgn-spec.txt`.

## 1. Architectural Strategy: Hexagonal (Ports & Adapters)
The application is structured to decouple the core chess annotation logic from external interfaces like the filesystem and the web-based UI.

* **Domain Core**: Manages the chess game state, move navigation, and annotation logic using `python-chess`.
* **Driving Adapters (Input)**:
    * **CLI Adapter**: Handles process lifecycle, chooses a local port automatically, and launches the local application shell.
    * **Web Adapter**: A local REST API (using `FastAPI`) that serves game data to the SPA.
* **Driven Adapters (Output)**:
    * **PGN Persistence Adapter**: Manages reading and writing `.pgn` files in strict export format, including files that contain multiple games.
    * **View Adapter**: Generates SVG board representations via `chess.svg`.

## 2. Component Design

### 2.1 Backend (Python)
The backend leverages the `python-chess` library for all move validation and PGN manipulation.

#### 2.1.1 PGN Ingestion
* When the user opens a file in the browser UI, the backend parses the entire PGN file into an in-memory collection of `chess.pgn.Game` objects.
* The backend derives a lightweight summary for each game from its headers so the frontend can render a game picker.
* **Default Preservation**: Existing comments and existing NAGs are preserved when the file is loaded.
* **Optional Comment Reset**: If the user chooses to clear comments for the current game, the system iterates through that game tree and clears `game.comment` and `node.comment` attributes for that game only.

#### 2.1.2 The "chess-annotate" Service
* **State Management**: Maintains:
    * the path of the currently opened PGN file,
    * an ordered collection of `chess.pgn.Game` objects for that file, and
    * the identifier or index of the currently selected game.
* **SVG Generation**: Uses `chess.svg.board()` with a fixed `size` parameter to ensure consistent dimensions for the frontend.
* **Annotation Logic**: 
    * **NAG $220**: Adds `220` to the `node.nags` set of the selected move.
    * **Comment**: Sets the `node.comment` string for the selected move.
* **Game Switching**: Exposes operations to list available games and switch the active game without restarting the process.

#### 2.1.3 Export Logic
* The persistence adapter uses `chess.pgn.FileExporter`.
* **Compliance**: Configured to enforce 80-character line limits and 7-bit ASCII encoding.
* **Placement**: Ensures the $220 NAG immediately follows the move, with the brace comment following the NAG.
* **Browser-Controlled Save**: Save is initiated from the browser UI rather than from a CLI file argument or backend-native file chooser.
* **Multi-Game Save**: Saving rewrites the full PGN file in original game order, exporting all games and substituting the modified representation of the currently edited game.
* **Session Save Rule**: The file opened in the current session is treated as the source document and is not overwritten directly by `Save`; the user saves to a newly chosen file instead.
* **Reopen Later**: A file produced by a prior save may later be reopened in a new application session and then serves as that session's source document.
* **Comment Preservation**: Because comments are preserved in memory by default, unmodified comments remain in the exported PGN unless the user explicitly clears them.

### 2.2 Frontend (Vanilla JS SPA)
The frontend is a single-page application with no external dependencies.

* **Board Rendering**: The SVG received from the server is injected into a persistent `<div>` container. To achieve "zero jitter," the container uses `display: grid` or absolute positioning to prevent layout shifts.
* **File / Game Selection**: Provides browser-controlled controls to open a PGN file, show all games contained in that file, and switch the active game.
* **Move List**: Renders the game tree as a selectable list of SAN move strings.
* **Communication**: Uses the `fetch` API for RESTful communication with the backend.
* **Save UX**: Indicates which file and game are active, and confirms when a save completes.

## 3. Application Lifecycle
1.  **CLI Invocation**: User runs `chess-annotate`.
2.  **Startup**: CLI chooses an available local port, starts the local server, and opens the SPA.
3.  **Open File**: User chooses a `.pgn` file via the browser UI.
4.  **Game Selection**: Backend parses all games in the file and the UI presents them for selection.
5.  **Interaction**: User selects a game, navigates moves, toggles $220, writes comments, and may optionally clear existing comments for that game.
6.  **Commitment**: User clicks **"Save"**, chooses a new output file through the browser save flow, and sends the updated in-memory PGN collection to the PGN Persistence Adapter.
7.  **Continuation**: User may switch to another game in the same file, open a different PGN file, or close the app and resume later by reopening a previously saved annotated file.
8.  **Shutdown**: User clicks **"Close"**, which sends a `POST /shutdown` request to the backend, terminating the Python process.

The CLI intentionally remains a thin launcher rather than a workflow surface.
Document-oriented actions such as `Open` and `Save` are controlled by the
browser UI.

## 4. PGN Export Specifications (Contextual Compliance)
The application will strictly enforce the following from `pgn-spec.txt`:
* **Character Set**: ISO 8859/1 subset (7-bit ASCII).
* **Line Wraps**: Newlines inserted to ensure no line exceeds 80 characters.
* **Tags**: Includes the Seven Tag Roster (STR) at the top of the file.

---
