"""Persist last run stats and run history for the GUI."""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from src.gui.env_io import get_project_root

DATA_DIR = get_project_root() / "data"
LAST_RUN_FILE = DATA_DIR / "last_run.json"
HISTORY_FILE = DATA_DIR / "run_history.json"
MAX_HISTORY = 10


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_last_run(applied: int, skipped: int, discovered: int = 0, errors: int = 0) -> None:
    ensure_data_dir()
    data = {
        "applied": applied,
        "skipped": skipped,
        "discovered": discovered,
        "errors": errors,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    LAST_RUN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    # Append to history
    history = load_run_history()
    history.insert(0, data)
    HISTORY_FILE.write_text(json.dumps(history[:MAX_HISTORY], indent=2), encoding="utf-8")


def load_last_run() -> dict[str, Any]:
    if not LAST_RUN_FILE.exists():
        return {}
    try:
        return json.loads(LAST_RUN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_run_history() -> list[dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
