from __future__ import annotations

import csv
import json
import os
import pathlib
import subprocess
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv(".env")

STATE_FILE = pathlib.Path(os.path.expanduser(os.getenv("SRS_STATE_FILE", "french_progress_plus.json")))
EXPORT_DIR = pathlib.Path(os.path.expanduser(os.getenv("SRS_EXPORT_DIR", "~/.french_tutor/exports")))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {"vocab": [], "level": "A1", "mode": "chat", "topic": "cafe"}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_due(vocab: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = datetime.now()
    due: List[Dict[str, Any]] = []
    for item in vocab:
        nd = item.get("next_due")
        if not nd:
            continue
        try:
            due_dt = datetime.fromisoformat(nd)
        except Exception:
            continue
        if due_dt <= now:
            due.append(item)
    return due


def write_csv(vocab: List[Dict[str, Any]]) -> pathlib.Path:
    stamp = datetime.now().strftime("%Y-%m-%d")
    path = EXPORT_DIR / f"srs_{stamp}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["word", "translation", "example", "box", "next_due"]
        )
        writer.writeheader()
        for item in vocab:
            writer.writerow(
                {
                    "word": item.get("word", ""),
                    "translation": item.get("translation", ""),
                    "example": item.get("example", ""),
                    "box": item.get("box", 1),
                    "next_due": item.get("next_due", ""),
                }
            )
    return path


def notify(title: str, message: str) -> None:
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{safe_message}" with title "{safe_title}"'],
            check=False,
        )
    except Exception:
        pass


def main() -> None:
    state = load_state()
    vocab = state.get("vocab", [])
    due = compute_due(vocab)
    csv_path = write_csv(vocab)

    print(f"[French Tutor] {len(due)} word(s) are due.")
    for item in due[:10]:
        word = item.get("word", "?")
        translation = item.get("translation", "?")
        box = item.get("box", 1)
        next_due = item.get("next_due", "")
        print(f" - {word} → {translation} (box {box}, due {next_due})")
    if len(due) > 10:
        print(f" ... and {len(due) - 10} more.")

    if due:
        notify("French Vocab Due", f"{len(due)} to review today — CSV: {csv_path.name}")
    else:
        notify("French Vocab", f"All clear today — CSV: {csv_path.name}")


if __name__ == "__main__":
    main()
