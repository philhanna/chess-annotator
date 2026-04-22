const statusBar = document.getElementById("status-bar");
const documentMeta = document.getElementById("document-meta");
const openButton = document.getElementById("open-button");
const closeButton = document.getElementById("close-button");
const saveButton = document.getElementById("save-button");
const openFileInput = document.getElementById("open-file-input");
const boardPane = document.getElementById("board-pane");
const movesPane = document.getElementById("moves-pane");
const gameSelect = document.getElementById("game-select");
const commentEditor = document.getElementById("comment-editor");
const diagramCheckbox = document.getElementById("diagram-checkbox");
const navButtons = Array.from(document.querySelectorAll(".nav-button"));

function setStatus(message) {
  statusBar.textContent = message;
}

async function fetchJson(url, options = {}) {
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
  commentEditor.value = "";
  commentEditor.disabled = true;
  diagramCheckbox.checked = false;
  diagramCheckbox.disabled = true;
  navButtons.forEach((button) => {
    button.disabled = true;
  });
  setStatus(`Status: ${session.status}`);
}

function renderBoard(svgMarkup) {
  if (!svgMarkup) {
    boardPane.innerHTML = '<div class="board-placeholder">No board available.</div>';
    return;
  }
  boardPane.innerHTML = svgMarkup;
}

function buildMoveButton(move) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `move-row${move.selected ? " selected" : ""}`;
  button.dataset.ply = String(move.ply);

  const head = document.createElement("div");
  head.className = "move-head";
  head.innerHTML = `
    <span class="move-number">${move.move_number}${move.side === "white" ? "." : "..."}</span>
    <span class="move-san">${move.san}</span>
    <span class="move-diagram">${move.diagram ? "*" : ""}</span>
  `;

  const preview = document.createElement("div");
  preview.className = "move-preview";
  preview.textContent = move.comment_preview || " ";

  button.append(head, preview);
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

  const whiteColumn = document.createElement("div");
  whiteColumn.className = "move-column";
  const blackColumn = document.createElement("div");
  blackColumn.className = "move-column";
  const grid = document.createElement("div");
  grid.className = "moves-grid";

  for (const move of moveRows) {
    const target = move.side === "white" ? whiteColumn : blackColumn;
    target.append(buildMoveButton(move));
  }

  grid.append(whiteColumn, blackColumn);
  movesPane.replaceChildren(grid);
  navButtons.forEach((button) => {
    button.disabled = false;
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

function renderEditor(editor, enabled) {
  commentEditor.value = editor.comment || "";
  commentEditor.disabled = !enabled;
  diagramCheckbox.checked = Boolean(editor.diagram);
  diagramCheckbox.disabled = !enabled;
}

function renderView(view) {
  const session = view.session;
  if (session.status === "idle") {
    renderIdle(session);
    return;
  }

  documentMeta.textContent = session.source_name || "Loaded PGN";
  saveButton.disabled = true;
  renderBoard(view.board_svg);
  renderGames(view.games, view.selected_game);
  renderMoves(view.move_rows);
  renderEditor(view.editor, false);

  if (view.selected_game) {
    setStatus(
      `Loaded ${view.games.length} game(s). Selected game: ${view.selected_game.white} vs ${view.selected_game.black}.`
    );
  } else {
    setStatus(`Loaded ${view.games.length} game(s).`);
  }
}

async function loadSession() {
  try {
    const session = await fetchJson("/api/session");
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

closeButton.addEventListener("click", async () => {
  try {
    await fetchJson("/api/close", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });
    setStatus("Closing application…");
  } catch (error) {
    setStatus(`Unable to close application: ${error.message}`);
  }
});

void loadSession();
