from __future__ import annotations

import sys
import subprocess
import json
from pathlib import Path

from rich.console import Console
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

THEME = Theme(
    {
        "accent": "green",
        "accent_bold": "bold green",
        "accent_dim": "dim green",
        "border": "green",
    }
)
console = Console(theme=THEME)

ROOT = Path(__file__).resolve().parent
SCRIPTS = {
    "1": ("STILLNESS", ROOT / "stillness.py"),
    "2": ("ONE", ROOT / "one.py"),
    "3": ("UNTANGLE", ROOT / "untangle.py"),
}


def card() -> Panel:
    t = Text(justify="center")
    t.append("\nRITUALS\n", style="accent_bold")
    t.append("\nchoose\n\n", style="accent_dim")

    t.append("1. STILLNESS\n", style="accent")
    t.append("2. ONE\n", style="accent")
    t.append("3. UNTANGLE\n", style="accent")

    t.append("\nq to quit\n", style="accent_dim")
    t.append("\n")

    return Panel(
        Align.center(t, vertical="middle"),
        border_style="border",
        padding=(1, 4),
        title="STILLNESS / ONE / UNTANGLE",
        title_align="center",
    )


def read_last_jsonl(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None


def return_card(name: str, show_view: bool = False) -> Panel:
    t = Text(justify="center")
    t.append(f"\n{name}\n", style="accent_bold")
    t.append("\n")
    t.append("return to dashboard\n\n", style="accent_dim")
    t.append("r to return\n", style="accent")
    if show_view:
        t.append("v to view previous\n", style="accent")
    t.append("q to quit\n", style="accent_dim")

    return Panel(
        Align.center(t, vertical="middle"),
        border_style="border",
        padding=(1, 4),
        title="RITUALS",
        title_align="center",
    )


def view_last_untangle() -> Panel:
    log_path = ROOT / "untangle_log.jsonl"
    last = read_last_jsonl(log_path)

    t = Text(justify="center")
    t.append("\nprevious entry\n\n", style="accent_bold")

    if last and last.get("sentence"):
        t.append(last.get("sentence") + "\n", style="accent_dim")
    else:
        t.append("no previous entry found\n", style="accent_dim")

    t.append("\n")
    t.append("r to return · q to quit\n", style="accent")

    return Panel(
        Align.center(t, vertical="middle"),
        border_style="border",
        padding=(1, 4),
        title="UNTANGLE",
        title_align="center",
    )


def run_script(path: Path) -> int:
    try:
        return subprocess.run([sys.executable, str(path)], cwd=str(ROOT)).returncode
    except KeyboardInterrupt:
        return 130


def main() -> None:
    while True:
        console.clear()
        console.print(card())
        choice = console.input("> ").strip().lower()

        if choice in ("q", "quit", "exit"):
            console.clear()
            return

        if choice not in SCRIPTS:
            continue

        name, path = SCRIPTS[choice]
        if not path.exists():
            console.clear()
            console.print(f"\nmissing: {path.name}\n", style="accent_dim")
            console.input("press ENTER to return ")
            continue

        run_script(path)

        # Explicit return point with optional view
        console.clear()
        console.print(return_card(name, show_view=(name == "UNTANGLE")))

        while True:
            resp = console.input("> ").strip().lower()

            if resp in ("q", "quit", "exit"):
                console.clear()
                return

            if resp in ("", "r", "return"):
                break

            if name == "UNTANGLE" and resp in ("v", "view"):
                console.clear()
                console.print(view_last_untangle())
                # after viewing, wait again for r/q
                continue

        continue


if __name__ == "__main__":
    main()