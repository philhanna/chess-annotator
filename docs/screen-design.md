# screen-design.md: Annotate SPA Screen Layout

This document describes the screen layout of the `chess-annotate` SPA based on
the UI ideas defined so far. It is intentionally partial. It captures only the
layout and behaviors that have already been described, and leaves later details
for future expansion.

## 1. Design Intent

The application should feel like a focused desktop-style workspace for chess
annotation. The screen is organized around two concurrent needs:

* seeing the current board position clearly, and
* scanning the game's move list efficiently while working through annotations.

The layout should favor long annotation sessions, allow the user to adjust pane
sizes, and keep the current position and move context visible at all times.

## 2. Overall Screen Structure

The SPA is divided into a left-hand side and a right-hand side.

* The split between the two sides is separated by a movable partition.
* The user can drag this partition to give more space either to the board view
  or to the move-and-annotation side.
* The application should preserve a stable layout while the user navigates
  through the game.
* A top-level action area should be present in the SPA for file and lifecycle
  actions.

Conceptually:

```text
+----------------------+------------------------------+
|                      |                              |
|      Left Pane       |          Right Pane          |
|                      |                              |
|   Current position   |   top and bottom sections    |
|      chessboard      |    separated by splitter     |
|                      |                              |
+----------------------+------------------------------+
```

### 2.1 Top-Level Actions

The SPA should provide a small set of top-level actions that remain available
regardless of which ply is currently selected.

The actions currently defined are:

* `Open`: uses the browser's open flow to select the input `.pgn` file.
* `Save`: uses the browser's save flow to write the current annotated game
  state to a chosen output `.pgn` file.
* `Close`: closes the application and shuts down the local backend process.

### 2.2 Save Behavior

Saving should be non-destructive with respect to the input file.

* In a given session, the application should not overwrite the `.pgn` file
  that was opened with `Open`.
* When the user activates `Save`, the browser save flow should require a new
  output file to be chosen.
* The save flow should therefore behave more like "Save As" than "save in
  place," even if the visible top-level action is labeled simply `Save`.
* A file produced by an earlier save may later be reopened in a new session and
  used as the starting point for further annotation.

This matches the intended workflow that the session's source PGN remains
untouched while the annotated result is written to a separate file, yet a
previously saved annotated file can still be reopened in a later session.

## 3. Left Pane

The left pane displays the chessboard for the current ply.
An implementation note: The board should be rendered as SVG generated on the
server side by the Python chess library.

### 3.1 Purpose

The left side is dedicated to visualizing the current position in the game.
When the user selects a move in the move list, the board updates to show the
position at that ply.

The board rendering should also provide lightweight visual move context:

* the currently selected move should be highlighted on the board when the
  selected ply is a real move, and
* a checked king should be highlighted when the current position is check.

### 3.2 Content

The pane contains:

* a diagram of the chessboard at the current ply.

At this stage, no additional controls or metadata are defined for the left
pane in this document.

### 3.3 Layout Notes

* The board should be the dominant element in the pane.
* The pane should be sized so the board remains easy to read during extended
  use.
* The existing requirement about avoiding visual "jitter" still applies, so
  the board container should remain stable as the position changes.

## 4. Right Pane

The right-hand side is divided vertically into a top half and a bottom half.

* These two sections are separated by a movable partition.
* The user can drag this partition to allocate more space to the move list or
  to the comment editor.

Conceptually:

```text
+----------------------------------+
|          Top Right Pane          |
|                                  |
|         move list view           |
+----------------------------------+
|        Bottom Right Pane         |
|                                  |
|        comment editor view       |
+----------------------------------+
```

## 5. Top Right Pane: Move List

The top half of the right-hand side contains the game's move list.

### 5.1 Two-Column Arrangement

The move list is presented in two columns:

* one column for White's moves,
* one column for Black's moves.

This arrangement is intended to make the game easier to scan visually than a
single long linear movetext display.

The move list should also include a dedicated zeroth-ply row representing the
initial position before White's first move. This row sits above the two
columns and can be selected like any other ply.

### 5.2 Row Structure

Each move row is organized around the move number and the move's annotation
status.

For each side's move entry, the display includes:

* the move number,
* an asterisk or similar compact marker indicating whether the user has marked
  that ply for a diagram,
* a truncated version of the comment for that ply, if a comment exists.

The comment preview is intentionally truncated because the move list is shown in
two columns and cannot accommodate full commentary text comfortably.

### 5.3 Purpose of Truncated Comments

The truncated comment text is meant to provide quick scanning context, not full
editing capability.

It helps the user answer questions such as:

* which moves already have notes,
* roughly what those notes are about,
* which moves may need further attention.

### 5.4 Diagram Marker

The move list should show a compact visual indicator when the user has marked a
move with the "diagram follows" flag.

At this stage, the indicator is not fully designed. The current concept is:

* an asterisk or similarly small symbol placed alongside the move entry.

The final symbol and styling can be refined later, but the move list should
make diagram-marked plies immediately visible when scanning the game.

### 5.5 Selected Ply

The interface has a notion of the currently selected move, more precisely the
currently selected ply.

This selected ply should be visually obvious in the move list.

* If the selected ply is a White move, the highlighted row appears in the White
  column.
* If the selected ply is a Black move, the highlighted row appears in the Black
  column.
* The highlight treatment should be strong enough that the user can identify
  the current ply at a glance while scanning the list.

Clicking on any move entry in either column makes that ply the currently
selected ply.

Clicking on the zeroth-ply row selects the initial position before the first
move.

When the selected ply changes:

* the highlight moves to the newly selected row,
* the board in the left pane updates to the corresponding position,
* any other annotation-related UI should follow the newly selected ply.

### 5.6 Move Navigation Controls

At the bottom of the move list in the top-right pane, there should be a compact
set of navigation controls for moving the selected ply backward and forward
through the game.

These controls are modeled after transport controls on audio or video devices.
The default concept is:

* `<<` to jump to the beginning of the game,
  meaning the zeroth ply,
* `<` to move back by one ply,
* `>` to move forward by one ply,
* `>>` to jump to the end of the game.

Another equivalent visual convention is acceptable if it is clearer, but the
behavior should remain the same.

These controls provide an alternative to clicking directly in the move list and
should always operate on the currently selected ply.

When the user activates one of these controls:

* the selected ply changes accordingly,
* the highlight in the move list updates,
* the left-pane board updates to the new current position.

The controls should remain close to the move list so they feel like part of the
same navigation surface.

## 6. Bottom Right Pane

The bottom half of the right-hand side is used for editing annotation details
for the currently selected ply, including both comment text and diagram
selection.

### 6.1 Purpose

This pane is where the user works with the full annotation state for the
selected move. It complements the move-list preview above:

* the top-right move list helps the user scan the game,
* the bottom-right pane shows the complete comment and diagram-toggle state for
  the selected ply.

### 6.2 Content

The pane always shows a view of the existing comment for the currently selected
move ply.

If the selected ply already has a comment:

* the full existing comment is shown in this pane.

If the selected ply has no comment:

* the pane still remains active for that ply, ready to display or edit comment
  content as the user works.

The pane is also where the user edits the comment text for the selected ply.

The pane should also include a checkbox that controls whether a diagram should
be generated for the selected ply.

* If the checkbox is checked, the selected ply is marked for diagram
  generation.
* If the checkbox is unchecked, the selected ply is not marked for diagram
  generation.

This checkbox is the editing control for the diagram marker whose summary is
shown in the move list.

For the zeroth ply, the comment editor remains active but the diagram checkbox
should be disabled, since diagram-after-this-ply semantics apply to actual
moves rather than the pre-game position.

### 6.3 Editing Controls

The comment editor should not use the `Enter` key to mean "done editing,"
because the user may want to enter multiple lines or blank lines.

Instead, the pane should provide explicit edit-completion controls:

* `Apply`: accepts the current edits for the selected ply.
* `Cancel`: discards the current in-progress edits for the selected ply and
  returns to the prior comment content.

These controls apply only to the selected ply's in-memory comment editing
session. They are distinct from the top-level `Save` action, which writes the
overall annotated PGN to a new file.

### 6.4 Relationship to Selection

The bottom-right pane is driven entirely by the currently selected ply.

Whenever the selected ply changes:

* the comment pane updates to show the comment associated with the new
  selection,
* the diagram checkbox updates to reflect whether the selected ply is currently
  marked for diagram generation,
* the pane therefore always stays synchronized with the move highlight in the
  top-right pane and the board position in the left pane.

### 6.5 Layout Notes

* The pane occupies the lower portion of the right side of the screen.
* It is separated from the move list by a movable partition.
* The user can resize the move-list area and the comment area according to the
  current task.

## 7. Interaction Summary

The screen layout described so far supports the following interaction pattern:

1. The user selects a move from the move list in the top-right pane.
2. The current board position updates in the left pane.
3. The bottom-right pane updates to show the existing comment for the selected
   ply.
4. The bottom-right pane also shows a checkbox for whether a diagram should be
   generated for the selected ply.
5. The user can edit the comment in the bottom-right pane, toggle the diagram
   checkbox, and use `Apply` or `Cancel` to finish or discard that edit
   session.
6. The user scans move numbers, diagram markers, and comment snippets in the
   move list to decide where to work next.
7. The user can also use transport-style controls at the bottom of the move
   list to jump to the beginning or end, or move one ply backward or forward.
8. The user can use the top-level actions to open a PGN, save annotated output
   to a new file, or close the application.
9. The user can resize both the main left-right split and the upper-lower split
   on the right side to suit his current task.

## 8. Open Items

The following screen-design topics are still intentionally unspecified:

* the exact appearance of the move rows,
* the exact symbol, styling, or color treatment for the diagram marker,
* the exact highlight styling for the selected ply,
* the truncation rules for comment previews,
* the exact placement and styling of the top-level action area,
* behavior on narrow screens.

These can be added as the screen design continues.
