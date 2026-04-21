# design.md: Detailed Design Document (v1.0)

This document provides a detailed technical design for the **chess-annotate** application, implementing the requirements specified in `requirements.md` and adhering to the PGN standards defined in `pgn-spec.txt`.

## 1. Architectural Strategy: Hexagonal (Ports & Adapters)
The application is structured to decouple the core chess annotation logic from external interfaces like the filesystem and the web-based UI.

* **Domain Core**: Manages the chess game state, move navigation, and annotation logic using `python-chess`.
* **Driving Adapters (Input)**:
    * **CLI Adapter**: Handles command-line arguments, file loading, and process lifecycle.
    * **Web Adapter**: A local REST API (using `FastAPI`) that serves game data to the SPA.
* **Driven Adapters (Output)**:
    * **PGN Persistence Adapter**: Manages reading and writing `.pgn` files in strict export format.
    * **View Adapter**: Generates SVG board representations via `chess.svg`.

## 2. Component Design

### 2.1 Backend (Python)
The backend leverages the `python-chess` library for all move validation and PGN manipulation.

#### 2.1.1 PGN Sanitization & Ingestion
* Upon loading the input file, the `chess.pgn.read_game` function is used to parse the game.
* **Comment Stripping**: The system iterates through the game tree and clears `game.comment` and `node.comment` attributes for every node.
* **NAG Preservation**: Existing NAGs are maintained within the `node.nags` set during this process.

#### 2.1.2 The "chess-annotate" Service
* **State Management**: Maintains a `chess.pgn.Game` object in memory.
* **SVG Generation**: Uses `chess.svg.board()` with a fixed `size` parameter to ensure consistent dimensions for the frontend.
* **Annotation Logic**: 
    * **NAG $220**: Adds `220` to the `node.nags` set of the selected move.
    * **Comment**: Sets the `node.comment` string for the selected move.

#### 2.1.3 Export Logic
* The persistence adapter uses `chess.pgn.FileExporter`.
* **Compliance**: Configured to enforce 80-character line limits and 7-bit ASCII encoding.
* **Placement**: Ensures the $220 NAG immediately follows the move, with the brace comment following the NAG.

### 2.2 Frontend (Vanilla JS SPA)
The frontend is a single-page application with no external dependencies.

* **Board Rendering**: The SVG received from the server is injected into a persistent `<div>` container. To achieve "zero jitter," the container uses `display: grid` or absolute positioning to prevent layout shifts.
* **Move List**: Renders the game tree as a selectable list of SAN move strings.
* **Communication**: Uses the `fetch` API for RESTful communication with the backend.

## 3. Application Lifecycle
1.  **CLI Invocation**: User runs `chess-annotate game.pgn`.
2.  **Startup**: CLI warns if the output file exists, sanitizes the input game, and starts the local server.
3.  **UI Launch**: CLI uses the `webbrowser` module to open the SPA.
4.  **Interaction**: User navigates moves, toggles $220, and writes comments.
5.  **Commitment**: User clicks **"Save"**, sending the in-memory game to the PGN Persistence Adapter.
6.  **Shutdown**: User clicks **"Close"**, which sends a `POST /shutdown` request to the backend, terminating the Python process.

## 4. PGN Export Specifications (Contextual Compliance)
The application will strictly enforce the following from `pgn-spec.txt`:
* **Character Set**: ISO 8859/1 subset (7-bit ASCII).
* **Line Wraps**: Newlines inserted to ensure no line exceeds 80 characters.
* **Tags**: Includes the Seven Tag Roster (STR) at the top of the file.

---
