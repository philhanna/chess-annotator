const statusBar = document.getElementById("status-bar");
const documentMeta = document.getElementById("document-meta");
const openButton = document.getElementById("open-button");
const closeButton = document.getElementById("close-button");
const saveButton = document.getElementById("save-button");
const openFileInput = document.getElementById("open-file-input");
const boardPane = document.getElementById("board-pane");
const movesPane = document.getElementById("moves-pane");
const workspace = document.querySelector(".workspace");
const rightPane = document.querySelector(".right-pane");
const mainSplitter = document.getElementById("main-splitter");
const rightSplitter = document.getElementById("right-splitter");
const gameSelect = document.getElementById("game-select");
const boardFlipButton = document.getElementById("board-flip-button");
const commentEditor = document.getElementById("comment-editor");
const diagramCheckbox = document.getElementById("diagram-checkbox");
const clearCommentsButton = document.getElementById("clear-comments-button");
const applyButton = document.getElementById("apply-button");
const cancelButton = document.getElementById("cancel-button");
const navButtons = Array.from(document.querySelectorAll(".nav-button"));

const editorDraft = {
  comment: "",
  diagram: false,
  dirty: false,
};

let currentSession = {
  status: "idle",
  unsaved_changes: false,
};
let appClosed = false;

const layoutStorageKeys = {
  workspaceLeft: "annotate.workspace.left",
  rightTop: "annotate.right.top",
};

function setStatus(message) {
  statusBar.textContent = message;
}

function renderClosedState() {
  appClosed = true;
  documentMeta.textContent = "Application closed";
  boardPane.innerHTML = '<div class="board-placeholder">The annotate server has shut down.</div>';
  movesPane.innerHTML = '<div class="moves-placeholder">This browser tab can now be closed.</div>';
  gameSelect.innerHTML = "<option>Application closed</option>";
  gameSelect.disabled = true;
  openButton.disabled = true;
  saveButton.disabled = true;
  boardFlipButton.disabled = true;
  boardFlipButton.setAttribute("aria-pressed", "false");
  closeButton.disabled = true;
  commentEditor.value = "";
  commentEditor.disabled = true;
  diagramCheckbox.checked = false;
  diagramCheckbox.disabled = true;
  clearCommentsButton.disabled = true;
  applyButton.disabled = true;
  cancelButton.disabled = true;
  navButtons.forEach((button) => {
    button.disabled = true;
  });
  setStatus("Application closed. You may close this browser tab.");
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function setCssVariable(name, value) {
  document.documentElement.style.setProperty(name, value);
}

function loadPersistedLayout() {
  const savedLeft = window.localStorage.getItem(layoutStorageKeys.workspaceLeft);
  const savedTop = window.localStorage.getItem(layoutStorageKeys.rightTop);

  if (savedLeft) {
    setCssVariable("--workspace-left", savedLeft);
  }
  if (savedTop) {
    setCssVariable("--right-top", savedTop);
  }
}

function startSplitterDrag(splitter, onMove, onEnd) {
  splitter.classList.add("dragging");

  function handlePointerMove(event) {
    onMove(event);
  }

  function handlePointerUp() {
    splitter.classList.remove("dragging");
    window.removeEventListener("pointermove", handlePointerMove);
    window.removeEventListener("pointerup", handlePointerUp);
    if (onEnd) {
      onEnd();
    }
  }

  window.addEventListener("pointermove", handlePointerMove);
  window.addEventListener("pointerup", handlePointerUp);
}

function enableSplitters() {
  mainSplitter.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    startSplitterDrag(
      mainSplitter,
      (moveEvent) => {
        const rect = workspace.getBoundingClientRect();
        const percent = clamp(((moveEvent.clientX - rect.left) / rect.width) * 100, 25, 75);
        const value = `${percent.toFixed(1)}%`;
        setCssVariable("--workspace-left", value);
        window.localStorage.setItem(layoutStorageKeys.workspaceLeft, value);
      }
    );
  });

  rightSplitter.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    startSplitterDrag(
      rightSplitter,
      (moveEvent) => {
        const rect = rightPane.getBoundingClientRect();
        const percent = clamp(((moveEvent.clientY - rect.top) / rect.height) * 100, 25, 75);
        const value = `${percent.toFixed(1)}%`;
        setCssVariable("--right-top", value);
        window.localStorage.setItem(layoutStorageKeys.rightTop, value);
      }
    );
  });
}

async function fetchJson(url, options = {}) {
  if (appClosed) {
    throw new Error("application is closed");
  }

  const response = await fetch(url, options);
  let payload = null;

  try {
    payload = await response.json();
  } catch (error) {
    payload = null;
  }

  if (!response.ok) {
    const message = payload && payload.error ? payload.error : `HTTP ${response.status}`;
    throw new Error(message);
  }

  return payload;
}

function renderIdle(session) {
  documentMeta.textContent = "No PGN loaded";
  boardPane.innerHTML = '<div class="board-placeholder">Board SVG will render here.</div>';
  movesPane.innerHTML = '<div class="moves-placeholder">Move list will render here.</div>';
  gameSelect.innerHTML = "<option>No games loaded</option>";
  gameSelect.disabled = true;
  saveButton.disabled = true;
  boardFlipButton.disabled = true;
  boardFlipButton.setAttribute("aria-pressed", "false");
  commentEditor.value = "";
  commentEditor.disabled = true;
  diagramCheckbox.checked = false;
  diagramCheckbox.disabled = true;
  clearCommentsButton.disabled = true;
  applyButton.disabled = true;
  cancelButton.disabled = true;
  navButtons.forEach((button) => {
    button.disabled = true;
  });
  setStatus(`Status: ${session.status}`);
}

async function saveWithFilePicker(pgnText, suggestedFilename) {
  const handle = await window.showSaveFilePicker({
    suggestedName: suggestedFilename,
    types: [
      {
        description: "PGN files",
        accept: {
          "application/x-chess-pgn": [".pgn"],
          "text/plain": [".pgn"],
        },
      },
    ],
  });

  const writable = await handle.createWritable();
  await writable.write(pgnText);
  await writable.close();
  return handle.name || suggestedFilename;
}

function saveWithDownload(pgnText, suggestedFilename) {
  const blob = new Blob([pgnText], { type: "application/x-chess-pgn;charset=utf-8" });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = suggestedFilename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
  return suggestedFilename;
}

function renderBoard(svgMarkup, selectedGame, flipped) {
  if (!svgMarkup) {
    boardPane.innerHTML = '<div class="board-placeholder">No board available.</div>';
    return;
  }

  const boardTitle = selectedGame?.board_title || "";
  const topPlayer = flipped ? (selectedGame?.white || "White") : (selectedGame?.black || "Black");
  const bottomPlayer = flipped ? (selectedGame?.black || "Black") : (selectedGame?.white || "White");
  const titleMarkup = boardTitle ? `<div class="board-title">${boardTitle}</div>` : "";

  boardPane.innerHTML = `
    <div class="board-layout">
      ${titleMarkup}
      <div class="board-player board-player-top">${topPlayer}</div>
      <div class="board-svg">${svgMarkup}</div>
      <div class="board-player board-player-bottom">${bottomPlayer}</div>
    </div>
  `;
}

function buildMoveButton(move) {
  const hasComment = Boolean(move.comment_preview);
  const button = document.createElement("button");
  button.type = "button";
  button.className = [
    "move-row",
    move.selected ? "selected" : "",
    move.is_initial_position ? "move-row-initial" : "",
    hasComment ? "has-comment" : "",
  ].filter(Boolean).join(" ");
  button.dataset.ply = String(move.ply);

  const numSpan = document.createElement("span");
  numSpan.className = "move-number";
  const sanSpan = document.createElement("span");
  sanSpan.className = "move-san";

  if (move.is_initial_position) {
    numSpan.textContent = "0.";
    sanSpan.textContent = "Start Position";
    button.append(numSpan, sanSpan);
  } else {
    numSpan.textContent = `${move.move_number}${move.side === "white" ? "." : "..."}`;
    sanSpan.textContent = move.san;
    button.append(numSpan, sanSpan);

    if (move.diagram) {
      const diagSpan = document.createElement("span");
      diagSpan.className = "move-diagram";
      diagSpan.textContent = "*";
      button.append(diagSpan);
    }

    if (hasComment) {
      const previewSpan = document.createElement("span");
      previewSpan.className = "move-preview";
      previewSpan.textContent = move.comment_preview;
      button.append(previewSpan);
    }
  }

  button.addEventListener("click", () => {
    void selectPly(move.ply);
  });

  return button;
}

function renderMoves(moveRows) {
  if (!moveRows.length) {
    movesPane.innerHTML = '<div class="moves-placeholder">No moves in this game.</div>';
    navButtons.forEach((button) => {
      button.disabled = true;
    });
    return;
  }

  const grid = document.createElement("div");
  grid.className = "moves-grid";
  const wrapper = document.createElement("div");
  wrapper.className = "moves-layout";

  for (const move of moveRows) {
    if (move.is_initial_position) {
      wrapper.append(buildMoveButton(move));
      continue;
    }

    grid.append(buildMoveButton(move));
  }

  wrapper.append(grid);
  movesPane.replaceChildren(wrapper);
  navButtons.forEach((button) => {
    button.disabled = false;
  });
}

function ensureSelectedMoveVisible() {
  const selectedRow = movesPane.querySelector(".move-row.selected");
  if (!selectedRow) {
    return;
  }

  selectedRow.scrollIntoView({
    block: "nearest",
    inline: "nearest",
  });
}

function renderGames(games, selectedGame) {
  gameSelect.innerHTML = "";
  if (!games.length) {
    const option = document.createElement("option");
    option.textContent = "No games loaded";
    gameSelect.append(option);
    gameSelect.disabled = true;
    return;
  }

  for (const game of games) {
    const option = document.createElement("option");
    option.value = String(game.index);
    option.textContent = game.label;
    if (selectedGame && game.index === selectedGame.index) {
      option.selected = true;
    }
    gameSelect.append(option);
  }

  gameSelect.disabled = false;
}

function syncDraftButtons(enabled) {
  applyButton.disabled = !enabled || !editorDraft.dirty;
  cancelButton.disabled = !enabled || !editorDraft.dirty;
}

function renderEditor(editor, enabled, diagramEnabled) {
  editorDraft.comment = editor.comment || "";
  editorDraft.diagram = Boolean(editor.diagram);
  editorDraft.dirty = false;

  commentEditor.value = editorDraft.comment;
  commentEditor.disabled = !enabled;
  diagramCheckbox.checked = editorDraft.diagram;
  diagramCheckbox.disabled = !diagramEnabled;
  clearCommentsButton.disabled = !enabled;
  syncDraftButtons(enabled);
}

function updateDraftFromControls() {
  editorDraft.comment = commentEditor.value;
  editorDraft.diagram = diagramCheckbox.checked;
  editorDraft.dirty = true;
  syncDraftButtons(true);
}

function confirmDiscardDraftIfNeeded() {
  if (!editorDraft.dirty) {
    return true;
  }

  return window.confirm("Discard unapplied annotation changes for the current ply?");
}

function confirmDiscardDocumentIfNeeded() {
  if (!currentSession.unsaved_changes) {
    return true;
  }

  return window.confirm("Discard unsaved changes for the current PGN document?");
}

function renderView(view) {
  const session = view.session;
  currentSession = session;
  if (session.status === "idle") {
    renderIdle(session);
    return;
  }

  const sourceLabel = session.source_name || "Loaded PGN";
  const savedSuffix = session.last_saved_name ? ` | Last saved: ${session.last_saved_name}` : "";
  const dirtySuffix = session.unsaved_changes ? " | Unsaved changes" : "";
  documentMeta.textContent = `${sourceLabel}${savedSuffix}${dirtySuffix}`;
  saveButton.disabled = !session.unsaved_changes;
  boardFlipButton.disabled = !view.flip_enabled;
  boardFlipButton.setAttribute("aria-pressed", String(Boolean(view.board_flipped)));
  renderBoard(view.board_svg, view.selected_game, Boolean(view.board_flipped));
  renderGames(view.games, view.selected_game);
  gameSelect.dataset.currentValue = view.selected_game ? String(view.selected_game.index) : "";
  renderMoves(view.move_rows);
  ensureSelectedMoveVisible();
  renderEditor(view.editor, Boolean(view.editor_enabled), Boolean(view.diagram_enabled));

  if (view.selected_game) {
    setStatus(
      `Loaded ${view.games.length} game(s). Selected game: ${view.selected_game.white} vs ${view.selected_game.black}.${session.unsaved_changes ? " Unsaved changes." : ""}`
    );
  } else {
    setStatus(`Loaded ${view.games.length} game(s).${session.unsaved_changes ? " Unsaved changes." : ""}`);
  }
}

async function loadSession() {
  try {
    const session = await fetchJson("/api/session");
    currentSession = session;
    renderIdle(session);
  } catch (error) {
    setStatus(`Unable to load session: ${error.message}`);
  }
}

async function openSelectedFile(file) {
  const pgnText = await file.text();
  const view = await fetchJson("/api/open", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      display_name: file.name,
      pgn_text: pgnText,
    }),
  });

  renderView(view);
}

async function selectPly(ply) {
  if (!confirmDiscardDraftIfNeeded()) {
    return;
  }

  const view = await fetchJson("/api/select-ply", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ply }),
  });

  renderView(view);
}

async function navigate(action) {
  if (!confirmDiscardDraftIfNeeded()) {
    return;
  }

  const view = await fetchJson("/api/navigate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action }),
  });

  renderView(view);
}

async function selectGame(gameIndex) {
  if (!confirmDiscardDraftIfNeeded()) {
    gameSelect.value = gameSelect.dataset.currentValue || "";
    return;
  }

  const view = await fetchJson("/api/select-game", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ game_index: gameIndex }),
  });

  renderView(view);
}

openButton.addEventListener("click", () => {
  openFileInput.click();
});

openFileInput.addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (!file) {
    return;
  }

  if (!confirmDiscardDraftIfNeeded()) {
    openFileInput.value = "";
    return;
  }

  if (!confirmDiscardDocumentIfNeeded()) {
    openFileInput.value = "";
    return;
  }

  try {
    setStatus(`Opening ${file.name}…`);
    await openSelectedFile(file);
  } catch (error) {
    setStatus(`Unable to open PGN: ${error.message}`);
  } finally {
    openFileInput.value = "";
  }
});

gameSelect.addEventListener("change", async (event) => {
  try {
    await selectGame(Number(event.target.value));
  } catch (error) {
    setStatus(`Unable to change game: ${error.message}`);
  }
});

for (const button of navButtons) {
  button.addEventListener("click", async () => {
    try {
      await navigate(button.dataset.action);
    } catch (error) {
      setStatus(`Unable to navigate: ${error.message}`);
    }
  });
}

commentEditor.addEventListener("input", () => {
  updateDraftFromControls();
});

diagramCheckbox.addEventListener("change", () => {
  updateDraftFromControls();
});

boardFlipButton.addEventListener("click", async () => {
  const flipped = boardFlipButton.getAttribute("aria-pressed") !== "true";
  try {
    const view = await fetchJson("/api/set-board-flipped", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        flipped,
      }),
    });
    renderView(view);
    setStatus(`Board orientation ${flipped ? "flipped" : "reset"}.`);
  } catch (error) {
    setStatus(`Unable to update board orientation: ${error.message}`);
  }
});

applyButton.addEventListener("click", async () => {
  try {
    const view = await fetchJson("/api/apply-annotation", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        comment: editorDraft.comment,
        diagram: editorDraft.diagram,
      }),
    });
    renderView(view);
    setStatus("Annotation applied.");
  } catch (error) {
    setStatus(`Unable to apply annotation: ${error.message}`);
  }
});

cancelButton.addEventListener("click", async () => {
  try {
    const view = await fetchJson("/api/cancel-annotation", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });
    renderView(view);
    setStatus("Annotation changes discarded.");
  } catch (error) {
    setStatus(`Unable to cancel annotation changes: ${error.message}`);
  }
});

closeButton.addEventListener("click", async () => {
  if (!confirmDiscardDraftIfNeeded()) {
    return;
  }

  if (currentSession.unsaved_changes) {
    if (!window.confirm("You have unsaved annotation changes. Close the application anyway?")) {
      return;
    }
  }

  try {
    await fetchJson("/api/close", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });
    renderClosedState();
    window.setTimeout(() => {
      window.close();
    }, 100);
  } catch (error) {
    setStatus(`Unable to close application: ${error.message}`);
  }
});

clearCommentsButton.addEventListener("click", async () => {
  if (!confirmDiscardDraftIfNeeded()) {
    return;
  }

  if (!window.confirm("Clear all comments in the current game? Diagram markers will be preserved.")) {
    return;
  }

  try {
    const view = await fetchJson("/api/clear-comments", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });
    renderView(view);
    setStatus("Comments cleared for the current game.");
  } catch (error) {
    setStatus(`Unable to clear comments: ${error.message}`);
  }
});

saveButton.addEventListener("click", async () => {
  if (editorDraft.dirty) {
    setStatus("Apply or cancel the current annotation edits before saving.");
    return;
  }

  try {
    const payload = await fetchJson("/api/save", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });

    let outputName;
    if (typeof window.showSaveFilePicker === "function") {
      outputName = await saveWithFilePicker(payload.pgn_text, payload.suggested_filename);
      const view = await fetchJson("/api/confirm-save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ output_name: outputName }),
      });
      renderView(view);
      setStatus(`Saved to ${outputName}.`);
      return;
    }

    outputName = saveWithDownload(payload.pgn_text, payload.suggested_filename);
    setStatus(`Download started for ${outputName}. Browser save could not be confirmed.`);
  } catch (error) {
    setStatus(`Unable to save PGN: ${error.message}`);
  }
});

window.addEventListener("beforeunload", (event) => {
  if (!editorDraft.dirty && !currentSession.unsaved_changes) {
    return;
  }

  event.preventDefault();
  event.returnValue = "";
});

void loadSession();
loadPersistedLayout();
enableSplitters();
