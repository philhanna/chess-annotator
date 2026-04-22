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

## 3. Left Pane

The left pane displays the chessboard for the current ply.

### 3.1 Purpose

The left side is dedicated to visualizing the current position in the game.
When the user selects a move in the move list, the board updates to show the
position at that ply.

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
  to whatever lower panel content is later defined.

Conceptually:

```text
+----------------------------------+
|          Top Right Pane          |
|                                  |
|         move list view           |
+----------------------------------+
|        Bottom Right Pane         |
|                                  |
|      content to be defined       |
+----------------------------------+
```

This document only defines the top half so far.

## 5. Top Right Pane: Move List

The top half of the right-hand side contains the game's move list.

### 5.1 Two-Column Arrangement

The move list is presented in two columns:

* one column for White's moves,
* one column for Black's moves.

This arrangement is intended to make the game easier to scan visually than a
single long linear movetext display.

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

The bottom half of the right-hand side exists in the layout, but its contents
have not yet been defined in this document.

For now, the only requirement is structural:

* it occupies the lower portion of the right pane,
* it is separated from the move list by a movable partition,
* its detailed content will be specified later.

## 7. Interaction Summary

The screen layout described so far supports the following interaction pattern:

1. The user selects a move from the move list in the top-right pane.
2. The current board position updates in the left pane.
3. The user scans move numbers, diagram markers, and comment snippets in the
   move list to decide where to work next.
4. The user can also use transport-style controls at the bottom of the move
   list to jump to the beginning or end, or move one ply backward or forward.
5. The user can resize both the main left-right split and the upper-lower split
   on the right side to suit his current task.

## 8. Open Items

The following screen-design topics are still intentionally unspecified:

* the content of the bottom-right pane,
* the exact appearance of the move rows,
* the exact symbol, styling, or color treatment for the diagram marker,
* the exact highlight styling for the selected ply,
* the truncation rules for comment previews,
* placement of file, save, game-selection, or close controls,
* behavior on narrow screens.

These can be added as the screen design continues.
