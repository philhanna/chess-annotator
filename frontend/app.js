async function loadSession() {
  const statusBar = document.getElementById("status-bar");

  try {
    const response = await fetch("/api/session");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const session = await response.json();
    statusBar.textContent = `Status: ${session.status}. Frontend root: ${session.frontend_root}`;
  } catch (error) {
    statusBar.textContent = `Unable to load session: ${error.message}`;
  }
}

void loadSession();
