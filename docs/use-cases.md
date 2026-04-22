# use-cases.md: Annotate Use Cases

This document translates the requirements and design for `chess-annotate` into
concrete user-facing workflows. It is intended to clarify how the application
should behave from the user's point of view, especially around session flow,
multi-game PGN files, saving, and resuming work.

## 1. Primary Actor

The primary actor is a single local user who wants to annotate his own chess
games for study and later rendering.

## 2. Scope

These use cases cover the `chess-annotate` application only. They assume:

* The application is launched locally via `chess-annotate`.
* The UI runs in the user's browser.
* Persistence is file-based only; there is no database.
* Imported PGN data is valid.

## 3. Goals

The user wants to:

* open a PGN file from the UI,
* choose a game from that file,
* navigate through the game,
* add or edit move comments,
* mark moves with NAG `$220` for later diagram rendering,
* preserve existing comments unless he explicitly chooses to clear them,
* save progress and come back later,
* switch to another game without restarting the app.

## 4. Use Cases

### UC-1: Launch the annotator

**Goal**: Start the application and reach a ready-to-use UI.

**Preconditions**:

* `chess-annotate` is installed and runnable.

**Main flow**:

1. The user runs `chess-annotate`.
2. The backend starts a local web server.
3. The application opens the default browser to the annotator UI.
4. The UI appears in an initial state with no game loaded yet.

**Success outcome**:

* The user can open a PGN file from within the UI.

### UC-2: Open a PGN file that contains one game

**Goal**: Load a PGN and begin annotating its game.

**Preconditions**:

* The application is already running.
* The user has a PGN file on disk.

**Main flow**:

1. The user chooses the UI action to open a PGN file.
2. The application reads and parses the file.
3. The application detects that the file contains one game.
4. The game becomes the active game.
5. The move list, board, comments, and NAG state become available in the UI.

**Success outcome**:

* The user is ready to navigate and annotate the game.

### UC-3: Open a PGN file that contains multiple games

**Goal**: Load a multi-game PGN and select the desired game to annotate.

**Preconditions**:

* The application is already running.
* The selected PGN file contains multiple games.

**Main flow**:

1. The user opens the PGN file from the UI.
2. The backend parses all games in the file.
3. The application derives summary labels from available headers such as
   players, event, round, date, and result.
4. The UI presents the games as a selectable list.
5. The user chooses one game.
6. That game becomes the active game and is shown in the board and move list.

**Success outcome**:

* The user can smoothly choose one game from a tournament or study export
  without splitting the PGN beforehand.

### UC-4: Navigate through a game

**Goal**: Inspect positions and choose the move to annotate.

**Preconditions**:

* An active game is loaded.

**Main flow**:

1. The user clicks a move in the move list.
2. The application updates the current position.
3. The board pane redraws the corresponding position.
4. The comment editor and NAG controls reflect the selected move's current
   annotation state.

**Success outcome**:

* The user can move through the game and focus annotation on a specific ply.

### UC-5: Add or edit commentary for a move

**Goal**: Record strategic or narrative notes for a selected move.

**Preconditions**:

* An active game is loaded.
* A move is selected.

**Main flow**:

1. The user selects a move.
2. The user types or edits text in the comment area.
3. The application updates the in-memory comment for that move.
4. The edited text remains visible while the user continues working.

**Success outcome**:

* The move has updated commentary ready to be saved into PGN comment syntax.

### UC-6: Mark a move for a diagram

**Goal**: Flag a move so the renderer can later insert a board diagram.

**Preconditions**:

* An active game is loaded.
* A move is selected.

**Main flow**:

1. The user selects a move.
2. The user toggles the "Diagram Follows" control.
3. The application adds or removes NAG `$220` from the selected move.
4. The UI reflects the updated state.

**Success outcome**:

* The move is correctly marked or unmarked for downstream rendering.

### UC-7: Continue working with existing comments preserved

**Goal**: Annotate a game that already has comments without losing prior work.

**Preconditions**:

* The opened PGN contains comments.

**Main flow**:

1. The user opens the PGN file.
2. The application preserves the comments during import.
3. The user selects moves and sees existing comments in the editor.
4. The user leaves some comments unchanged and edits others.

**Success outcome**:

* Existing commentary remains part of the game unless the user explicitly
  changes it.

### UC-8: Clear existing comments for a game before re-annotating

**Goal**: Start a fresh annotation pass on a game that already contains
comments.

**Preconditions**:

* A game is loaded.
* The game already contains comments.

**Main flow**:

1. The user chooses the UI action to clear existing comments for the current
   game.
2. The application removes `game.comment` and all move comments from that game
   in memory.
3. NAGs remain intact.
4. The user proceeds to annotate from a clean comment state.

**Success outcome**:

* The game is ready for a fresh commentary pass without requiring external PGN
  cleanup.

### UC-9: Save work on the current game

**Goal**: Persist annotations to disk so they are not lost.

**Preconditions**:

* A PGN file is open.
* The user has made or reviewed changes.

**Main flow**:

1. The user clicks **Save**.
2. The application exports the PGN collection in strict export format.
3. The current game's updated comments and NAGs are written.
4. Other games in the same file are also written back in their original order.
5. The UI shows a success notification.

**Success outcome**:

* The PGN file on disk now contains the user's saved annotation work.

### UC-10: Stop and resume annotation later

**Goal**: Work on annotation over multiple sittings.

**Preconditions**:

* The user has previously saved a PGN file with annotations.

**Main flow**:

1. The user saves his work.
2. The user closes the application.
3. At a later time, the user runs `chess-annotate` again.
4. The user reopens the same PGN file from the UI.
5. The user selects the game he was working on.
6. The application loads the previously saved comments and NAGs.
7. The user continues annotating.

**Success outcome**:

* Annotation is naturally resumable without any separate project database or
  session file.

### UC-11: Switch to a different game in the same PGN file

**Goal**: Move from one game to another without restarting the app.

**Preconditions**:

* A multi-game PGN file is open.

**Main flow**:

1. The user finishes a stretch of work on one game.
2. The user selects another game from the game list.
3. The application makes the new game active.
4. The board, move list, comments, and NAG controls update to reflect the new
   game.

**Success outcome**:

* The user can annotate multiple tournament games in one session.

### UC-12: Close the application cleanly

**Goal**: End the session in the intended desktop-style way.

**Preconditions**:

* The application is running.

**Main flow**:

1. The user clicks **Close** in the SPA.
2. The frontend sends the shutdown request to the backend.
3. The backend terminates the local server and exits the CLI process.

**Success outcome**:

* The session ends cleanly.

## 5. Key Alternate and Edge Cases

### A-1: The user launches the app but does not open a file immediately

The application should remain usable in an idle state and clearly prompt for
opening a PGN file.

### A-2: The PGN file has sparse or duplicated headers

The application should still present each game as a distinct selectable item,
even if some labels are less descriptive.

### A-3: The user saves one game from a multi-game file

Saving should preserve the non-selected games, their order, and their headers.

### A-4: The user wants to preserve comments in some games but clear them in another

Comment clearing should apply only to the currently selected game, not to the
entire PGN file.

### A-5: The user adds both a diagram marker and a comment to a move

The exported movetext must place NAG `$220` immediately after the move, with
the brace comment following it.

## 6. Summary

The central usage pattern for `chess-annotate` is not a one-shot CLI transform.
It is a local desktop-style annotation workspace in which the user opens PGN
files from the UI, works across one or more games, saves progress to disk, and
comes back later without losing context.
