# Chess Annotator Implementation Plan

This plan turns [`docs/design.md`](/home/saspeh/dev/python/chess-annotator/docs/design.md) and the defined use cases into an ordered implementation roadmap. It is written against the current repository state on April 7, 2026, where the codebase already contains domain logic for segment splitting/merging, PGN parsing, PDF rendering, and a draft API, but does not yet implement the design's file layout, per-game session model, or the full set of game-management and review flows.

## Goals

- Align the codebase with Design 2.0 as the new source of truth
- Implement all sixteen use cases with clear boundaries between domain, ports, and adapters
- Preserve the existing strengths of the project: `python-chess` integration, PDF rendering, and testable core logic
- Leave the system usable from both CLI and future API layers

## Current State Summary

The current code appears to represent an earlier model:

- `Annotation` is a single aggregate containing PGN plus segment data
- `AnnotationRepository` is keyed by numeric `annotation_id`
- Working copies exist conceptually, but not in the `annotated.pgn` / `annotation.json` paired-file structure from the new design
- Segment operations exist in `src/annotate/use_cases/interactors.py`
- `docs/openapi.yaml` already tracks the newer design more closely than the current code

Because of that mismatch, the work should begin with a focused persistence and application-model refactor before expanding UI behavior.

## Delivery Strategy

Implement in seven phases. Each phase should leave the codebase passing tests and in a runnable state.

### Phase 1: Lock the design into the domain model

Purpose: establish the core vocabulary and invariants from Design 2.0.

Work:

- Replace the old `Annotation`-centric model with a game/session model that matches the design:
  - game identity by author-supplied `game_id`
  - annotated PGN as source of truth for turning points only
  - `annotation.json` as source of truth for segment content
- Introduce explicit domain types for:
  - `GameId`
  - `TurningPoint`
  - `SegmentContent`
  - `SegmentView` or equivalent derived read model
  - `GameState` / `SessionState`
- Keep segment derivation as pure domain logic:
  - ordered turning points
  - contiguous non-overlapping segments
  - first turning point always at ply 1
  - final segment ends at last ply
- Define helpers for:
  - ply <-> move/color conversion
  - segment range derivation
  - locating a segment by turning-point ply
  - extracting move lists for a segment

Tests:

- domain tests for turning-point ordering and validation
- segment derivation tests from PGN length and turning-point lists
- tests proving PGN markers and JSON keys must stay in sync logically

### Phase 2: Build the new persistence layer

Purpose: implement the file layout and session semantics described in section 4 of the design.

Work:

- Introduce a new `GameRepository` port matching the design instead of the current numeric `AnnotationRepository`
- Implement `PGNFileGameRepository` around the required layout:
  - `<store_root>/<game-id>/annotated.pgn`
  - `<store_root>/<game-id>/annotation.json`
  - optional `.work` copies
  - optional `output.pdf`
- Make the repository responsible for:
  - import from raw PGN with comments/NAGs stripped
  - read/write of main files and work files as a unit
  - listing games and session status
  - save, close, resume, delete, and save-as file operations
  - validation that `[%tp]` markers exactly match JSON segment keys
- Add migration glue or a temporary compatibility layer only if needed; otherwise prefer a clean cut to the new storage model

Tests:

- repository tests using temp directories
- open/save/close/resume behavior tests
- tests for unsaved-work detection
- tests for sync failures between PGN and JSON

### Phase 3: Implement the use-case interactors

Purpose: cover the full use-case set behind stable application services.

Work:

- Define one interactor per use case or a small cohesive service group, covering:
  - UC-001 to UC-005 game management
  - UC-006 to UC-010 segment authoring
  - UC-011 to UC-012 session control
  - UC-013 PDF rendering
  - UC-014 Lichess upload
  - UC-015 list segments
  - UC-016 view segment
- Keep interactors thin:
  - enforce preconditions
  - orchestrate repository and adapter calls
  - return explicit result objects rather than printing
- Reuse existing split/merge logic by adapting it to the new model instead of duplicating rules
- Add conflict/error types for common alternate flows:
  - game not found
  - session not open
  - turning point already exists
  - overwrite required
  - upload/render failure

Tests:

- interactor tests for each main flow
- targeted alternate-flow tests from the use-case documents
- regression tests for split/merge semantics already covered today

### Phase 4: Add output adapters

Purpose: complete the side-effectful output paths while keeping them behind ports.

Work:

- Keep the existing document rendering adapter, but adapt it to read the new game model
- Define or finalize the `DocumentRenderer` port around the derived segment view model
- Add a `LichessUploader` port and concrete adapter for UC-014
  - upload current working PGN when a session is open
  - upload saved `annotated.pgn` otherwise
  - return analysis URL only
- Decide whether upload should strip `[%tp]` markers before submission or preserve them; document the choice and test it
- Cache or regenerate `output.pdf` on demand per design

Tests:

- adapter-level test doubles for interactor coverage
- smoke test for PDF render on the new model
- contract tests for Lichess request/response handling

### Phase 5: Build the CLI around the interactors

Purpose: make the system usable end-to-end from the terminal and line up commands with the use cases.

Work:

- Refactor `src/annotate/cli/annotate.py` and related CLI modules to call the new interactors
- Support command flows for:
  - import/list/open/save/close/save-as/delete
  - split/merge/label/comment/diagram
  - list-segments/view-segment
  - render/upload
- Make session-sensitive commands fail clearly when no session is open
- Standardize move/ply input parsing so users can work in move-plus-color notation while the core stores plies
- Revisit editor-launch behavior for annotation text editing under the new model

Tests:

- CLI integration tests for representative happy paths
- CLI tests for session errors and overwrite prompts

### Phase 6: Reconcile API and documentation

Purpose: keep the external contract aligned with the implementation.

Work:

- Update `docs/openapi.yaml` to match any implementation decisions made during Phases 1-5
- Ensure the API resource model reflects actual result objects and error cases
- Update `README.md`, sample config, and any architecture notes to remove the old numeric-id/repository language
- Add a short persistence-format note describing:
  - `[%tp]` encoding
  - `annotation.json` schema
  - `.work` lifecycle

Tests:

- schema lint or validation check for `docs/openapi.yaml` if tooling is available
- doc review to ensure examples use `game_id`, not `annotation_id`

### Phase 7: Hardening and polish

Purpose: make the system resilient enough for daily use.

Work:

- Add end-to-end tests covering a full author workflow:
  - import game
  - open session
  - split into segments
  - add labels/annotations
  - list and view segments
  - save
  - render PDF
  - upload to Lichess
- Verify crash-resume behavior with existing `.work` files
- Improve error messages around invalid plies, malformed PGN, and corrupted storage
- Consider lightweight logging around file and network operations

Tests:

- end-to-end workflow tests in a temp store
- failure-path tests for malformed PGN and broken JSON

## Recommended Implementation Order by Use Case

This order minimizes rework:

1. UC-001 Import game
2. UC-003 Open session
3. UC-011 Save session
4. UC-012 Close session
5. UC-002 List games
6. UC-006 Add turning point
7. UC-007 Remove turning point
8. UC-008 Set label
9. UC-009 Set annotation text
10. UC-010 Toggle diagram
11. UC-015 List segments
12. UC-016 View segment
13. UC-013 Render PDF
14. UC-014 Upload to Lichess
15. UC-004 Save As
16. UC-005 Delete game

Rationale:

- import/open/save/close establish the persistence and session backbone
- segment editing must exist before segment review
- render and upload depend on reliable state loading
- save-as and delete are lower-risk once the repository model is stable

## Suggested Code Structure Changes

Target structure:

- `src/annotate/domain/`
  - pure models, invariants, segment derivation, move/ply helpers
- `src/annotate/use_cases/`
  - one module per use-case family
- `src/annotate/ports/`
  - `game_repository.py`
  - `document_renderer.py`
  - `diagram_renderer.py`
  - `lichess_uploader.py`
  - `editor_launcher.py`
- `src/annotate/adapters/`
  - `pgn_file_game_repository.py`
  - `python_chess_*`
  - `markdown_html_pdf_renderer.py`
  - `lichess_api_uploader.py`
- `tests/`
  - `domain/`
  - `use_cases/`
  - `adapters/`
  - `smoke/`
  - `e2e/`

## Key Design Decisions to Resolve Early

These should be settled before Phase 2 is far along:

- Whether to replace the current model in one pass or keep a short-lived compatibility layer
- Exact JSON schema for `annotation.json`, including whether ply keys are stored as strings only
- How unsaved changes are detected on close:
  - byte comparison of main vs `.work` files
  - parsed structural comparison
- Whether Lichess uploads include or strip `[%tp]` comments
- Whether PDF rendering should read from working state automatically when a session is open, matching upload behavior

## Definition of Done

The implementation is complete when:

- all sixteen use cases are implemented through interactors
- the repository uses the design's paired-file game directory layout
- session open/save/close/resume behavior matches the design exactly
- segment list and view flows work from derived segment data
- PDF rendering and Lichess upload operate on the correct current state
- CLI and docs use `game_id` language consistently
- automated tests cover domain rules, repository behavior, use cases, and one end-to-end workflow

## Recommended First Milestone

The best first milestone is a vertical slice for UC-001, UC-003, UC-011, UC-012, UC-015, and UC-016 on the new persistence model. That slice proves the hardest architectural change first: storing and reloading a game as `annotated.pgn` plus `annotation.json`, editing it through `.work` files, and presenting derived segment information back to the user.
