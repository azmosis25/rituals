from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# -----------------------------
# Theme (match your green ritual suite)
# -----------------------------
THEME = Theme(
    {
        "accent": "green",
        "accent_bold": "bold green",
        "accent_dim": "dim green",
        "border": "green",
    }
)
console = Console(theme=THEME)

# -----------------------------
# Config
# -----------------------------
LOG_PATH = Path(__file__).with_name("untangle_log.jsonl")
RECALL_LAST = False  # Optional recall of last sentence (quiet, off by default)


@dataclass
class Entry:
    sentence: str
    ts: str


def log_entry(sentence: str) -> None:
    try:
        e = Entry(sentence=sentence, ts=datetime.now().isoformat(timespec="seconds"))
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(e.__dict__, ensure_ascii=False) + "\n")
    except Exception:
        # Logging must never block the practice.
        pass


def read_last_sentence() -> str | None:
    if not LOG_PATH.exists():
        return None
    try:
        with LOG_PATH.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            return None
        last = json.loads(lines[-1])
        return last.get("sentence")
    except Exception:
        return None


def card(title: str, body: Text) -> Panel:
    return Panel(
        Align.center(body, vertical="middle"),
        border_style="border",
        padding=(1, 4),
        title=title,
        title_align="center",
    )


def prompt_screen() -> Panel:
    t = Text(justify="center")
    t.append("\nUNTANGLE\n", style="accent_bold")
    t.append("\n")
    t.append("name the next honest step\n", style="accent_dim")
    t.append("one sentence only\n", style="accent_dim")
    if RECALL_LAST:
        last = read_last_sentence()
        if last:
            t.append("\nlast time:\n", style="accent_dim")
            t.append(last + "\n", style="accent_dim")
    t.append("\n")
    t.append("press ENTER to submit.\n", style="accent_dim")
    t.append("type /q to exit.\n", style="accent_dim")
    return card("UNTANGLE", t)


def complete_screen() -> Panel:
    t = Text(justify="center")
    t.append("\nsaved\n", style="accent_bold")
    t.append("\n")
    t.append("release it\n", style="accent_dim")
    return card("UNTANGLE", t)


def normalize_one_sentence(s: str) -> str:
    s = " ".join(s.strip().split())
    if not s:
        return s

    # Soft guard: ensure it ends like a sentence (without being pedantic)
    if s[-1] not in ".!?":
        s += "."
    return s


def main() -> None:
    console.clear()
    console.print(prompt_screen())
    console.print()

    raw = console.input("> ").strip()
    if raw.lower() in ("/q", "q", "quit", "exit"):
        console.clear()
        return

    sentence = normalize_one_sentence(raw)

    if not sentence:
        console.clear()
        return

    # Hard rule: one line only. If user pastes multi-line, take first line.
    sentence = sentence.splitlines()[0].strip()
    sentence = normalize_one_sentence(sentence)

    log_entry(sentence)

    console.clear()
    console.print(complete_screen())

    # Brief pause, then auto-exit
    try:
        import time
        time.sleep(1.1)
    except Exception:
        pass

    console.clear()


if __name__ == "__main__":
    main()
