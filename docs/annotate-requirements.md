# annotate.md: Requirements Specification (v1.8)

## 1. Project Overview
The `annotate` project is a local-only Python application that utilizes a web browser as its graphical user interface. It is designed for personal chess study, allowing a user to open a PGN file, choose a game from that file, navigate moves, and persist annotations (NAGs and commentary) directly to the file system over multiple sessions.

## 2. Technical Architecture
* **Pattern**: Hexagonal (Ports and Adapters). 
* **Source Structure**: `src/annotate`
* **CLI**: `chess-annotate`
* **Interface**: The CLI launches a local web server and automatically opens the default system browser to the application URL.

## 3. User Interface (SPA)
* **Technology**: Vanilla JavaScript, HTML, CSS. No frameworks.
* **Layout**:
    * **Library / Session Controls**: UI controls for opening a PGN file, choosing a game within that file, and switching to another game without restarting the application.
    * **Move List**: A scrollable list of plies. Clicking a move updates the Board Pane.
    * **Board Pane**: Displays an SVG rendering of the current position. 
* **Visual Continuity**: To prevent "jitter," the SVG container must have fixed dimensions. The frontend will replace the SVG content in-place to ensure the UI does not "jump."
* **Annotation Controls**:
    * A persistent text area for entering/editing move commentary.
    * A toggle/button for the $220 NAG ("Diagram Follows").
    * A user-visible option to clear existing comments for the current game before saving, rather than doing so automatically at load time.
* **Lifecycle Controls**: A **"Close"** button in the SPA is the standard and primary method for terminating the session.

## 4. Functional Requirements

### 4.1 CLI & Lifecycle
* **Execution**: `chess-annotate`
* **Startup Logic**: 
    * **Server Startup**: The CLI starts the local server and opens the browser UI without requiring a PGN path on the command line.
    * **Port Selection**: The application chooses its local port automatically.
    * **Initial State**: The application may launch with no game loaded. Opening a PGN file is a normal first action in the UI.
    * **Minimal CLI Surface**: The CLI is intentionally minimal and does not expose workflow options for opening files, saving files, selecting games, or controlling annotation behavior.
* **Termination**: Clicking the "Close" button in the SPA triggers the backend to shut down the web server and exit the CLI process.

### 4.2 Persistence & "Desktop-Style" Saving
* **State Management**: The Python backend maintains the currently loaded PGN collection and the currently selected game in memory.
* **Multi-Game PGN Support**:
    * A single `.pgn` file may contain multiple games.
    * The UI must present the games as a selectable list using identifying metadata where available (for example, players, event, round, date, result).
    * The user must be able to switch between games in the same file without restarting the CLI.
* **Resume Workflow**:
    * Saving writes annotations back to disk so the user can stop and continue later.
    * After reopening the application, the user can reopen a previously saved annotated PGN file and continue annotating from that point.
* **Save Trigger**:
    * **State Management**: The SPA includes a **"Save"** button.
    * **Feedback**: Upon a successful write, the UI provides a "File Saved" notification.
    * **Browser-Controlled File Selection**: The browser UI controls both opening and saving. `Open` is initiated from the browser, and `Save` is initiated from the browser's save flow.
    * **Scope**: Save behavior must be explicit about whether it writes the selected game only or rewrites the entire PGN file containing all games. The preferred behavior is to preserve the full file and update only the selected game content within it.
    * **Non-Destructive Session Save**: During a given annotation session, the file opened via `Open` must not be overwritten directly. Saving should write to a user-selected output file.
    * **Continuation by Reopen**: A file produced by an earlier save may later be reopened in a new invocation of the application and used as the starting point for additional annotation.
* **No Database**: All persistence is handled via PGN files.

### 4.3 Export Standards
* **Compliance**: Adherence to 1994 PGN Export Format (7-bit ASCII, 80-char line limit).
* **NAG $220**: Placed **immediately after** the move ply (e.g., `12. Nf3 $220`).
* **Comments**:
    * Strategic commentary is embedded within the PGN move text using braces `{ ... }`.
    * If both a NAG and a comment exist for a move, the comment follows the NAG.
    * Existing comments in an imported PGN are preserved by default.
    * The application may provide an explicit user action to clear existing comments for the selected game when the user wants a clean annotation pass.

### 4.4 Data Integrity
* **Validation**:
    * The application assumes imported PGN data represents valid chess games.
    * If a PGN file contains multiple games, the application must preserve the order and headers of the non-selected games when saving changes to one game.

### 4.5 Integration
* The generated PGN is intended for the `src/render` package. The $220 NAG specifically signals the renderer to generate a board diagram for that position.
