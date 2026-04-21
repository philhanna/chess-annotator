# annotate.md: Requirements Specification (v1.7)

## 1. Project Overview
The `annotate` project is a local-only Python application that utilizes a web browser as its graphical user interface. It is designed for personal chess study, allowing a user to load a PGN file, navigate moves, and persist annotations (NAGs and commentary) directly to the file system.

## 2. Technical Architecture
* **Pattern**: Hexagonal (Ports and Adapters). 
* **Source Structure**: `src/annotate`
* **CLI**: `chess-annotate`
* **Interface**: The CLI launches a local web server and automatically opens the default system browser to the application URL.

## 3. User Interface (SPA)
* **Technology**: Vanilla JavaScript, HTML, CSS. No frameworks.
* **Layout**:
    * **Move List**: A scrollable list of plies. Clicking a move updates the Board Pane.
    * **Board Pane**: Displays an SVG rendering of the current position. 
* **Visual Continuity**: To prevent "jitter," the SVG container must have fixed dimensions. The frontend will replace the SVG content in-place to ensure the UI does not "jump."
* **Annotation Controls**:
    * A persistent text area for entering/editing move commentary.
    * A toggle/button for the $220 NAG ("Diagram Follows").
* **Lifecycle Controls**: A **"Close"** button in the SPA is the standard and primary method for terminating the session.

## 4. Functional Requirements

### 4.1 CLI & Lifecycle
* **Execution**: `chess-annotate <input.pgn> [-o <output.pgn>]`
* **Startup Logic**: 
    * **Data Sanitization**: The tool reads the source PGN and **strips all existing brace comments** `{ ... }`. 
    * **NAG Preservation**: Existing Numeric Annotation Glyphs (e.g., $1, $18) must be **preserved** and remain in the game data.
    * **Safety Check**: If the output file already exists, the CLI must issue a warning to the terminal before proceeding.
* **Termination**: Clicking the "Close" button in the SPA triggers the backend to shut down the web server and exit the CLI process.

### 4.2 Persistence & "Desktop-Style" Saving
* **State Management**: The Python backend maintains the game state (sanitized of comments) in memory.
* **Save Trigger**:
    * **State Management**: The SPA includes a **"Save"** button.
    * **Feedback**: Upon a successful write, the UI provides a "File Saved" notification.
* **No Database**: All persistence is handled via PGN files.

### 4.3 Export Standards
* **Compliance**: Adherence to 1994 PGN Export Format (7-bit ASCII, 80-char line limit).
* **NAG $220**: Placed **immediately after** the move ply (e.g., `12. Nf3 $220`).
* **Comments**: New strategic commentary is embedded within the PGN move text using braces `{ ... }`. If both a NAG and a comment exist for a move, the comment follows the NAG.

### 4.4 Data Integrity
* **Validation**: The application assumes the input PGN represents a valid chess game. 

### 4.5 Integration
* The generated PGN is intended for the `src/render` package. The $220 NAG specifically signals the renderer to generate a board diagram for that position.