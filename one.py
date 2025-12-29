from __future__ import annotations

import sys
import time
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.theme import Theme

# -----------------------------
# Theme (green-forward, calm)
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
WORK_MIN = 25                       # Only deep work sessions
BREAK_MIN = 5                       # Mandatory break after deep work
ARRIVAL_SEC = 10                    # Ritual "arrival" before session begins
FRAME_DT = 1.0                      # UI refresh (1-second ticks)

LOG_PATH = Path(__file__).with_name("one_log.jsonl")


@dataclass
class OneSession:
    task: str
    minutes: int
    started_at: str
    interrupted: bool = False
    outcome: str = "released"  # "complete" or "released"


# -----------------------------
# Helpers
# -----------------------------
def bell() -> None:
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass


def log_event(event: dict) -> None:
    try:
        event = {**event, "ts": datetime.now().isoformat(timespec="seconds")}
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_key_nonblocking() -> Optional[str]:
    """Best-effort cross-platform single-key read."""
    if sys.platform.startswith("win"):
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getwch()
        return None

    import select
    import termios
    import tty

    dr, _, _ = select.select([sys.stdin], [], [], 0)
    if not dr:
        return None

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def sleep_with_quit(seconds: float) -> bool:
    """Sleep in small slices; return True if user pressed 'q'."""
    end = time.time() + seconds
    while time.time() < end:
        ch = read_key_nonblocking()
        if ch and ch.lower() == "q":
            return True
        time.sleep(0.05)
    return False


# -----------------------------
# Screens
# -----------------------------
def card(title: str, body: Text) -> Panel:
    return Panel(
        Align.center(body, vertical="middle"),
        border_style="border",
        padding=(1, 4),
        title=title,
        title_align="center",
    )


def arrival_screen(task: str, minutes: int) -> Panel:
    t = Text()
    t.append("\ncommit\n", style="accent_bold")
    t.append("\n")
    t.append(task.strip() + "\n", style="accent_bold")
    t.append("\n")
    t.append(f"{minutes} minutes\n", style="accent_dim")
    t.append("\n(q to exit)\n", style="accent_dim")
    return card("ONE", t)


def fmt_mmss(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


def work_screen(task: str, remaining_sec: int) -> Text:
    # Large, centered task. Minimal context.
    t = Text(justify="center")
    t.append("\nONE\n", style="accent_bold")
    t.append("\n")
    t.append(task.strip() + "\n", style="accent_bold")
    t.append("\n")
    t.append("\n")
    t.append(f"{fmt_mmss(remaining_sec)}\n", style="accent_dim")
    t.append("\n")
    t.append("remain\n", style="accent_dim")
    t.append("\n")
    # Subtle quit option (ritual-friendly, not “UI-ish”)
    t.append("q to release\n", style="accent_dim")
    return t


def break_screen(remaining_sec: int) -> Text:
    t = Text(justify="center")
    t.append("\nbreak\n", style="accent_bold")
    t.append("\n")
    t.append(f"{fmt_mmss(remaining_sec)}\n", style="accent_dim")
    t.append("\n")
    t.append("walk • water • breathe\n", style="accent_dim")
    t.append("\n")
    t.append("(q to end)\n", style="accent_dim")
    return t


def end_question() -> Panel:
    t = Text()
    t.append("\ncomplete\n", style="accent_bold")
    t.append("\n")
    t.append("did you finish?\n\n", style="accent_dim")
    t.append("[y] yes    [n] no\n", style="accent")
    return card("ONE", t)


# -----------------------------
# Flow
# -----------------------------
def choose_task() -> str:
    console.clear()

    lines = Text()
    lines.append("\nwhat is the one thing?\n\n", style="accent_bold")
    lines.append("(25 minutes. one line. no editing once started)\n", style="accent_dim")

    console.print(card("ONE", lines))
    task = console.input("\n> ").strip()
    if not task:
        task = "return to the task"

    return task


def run_work(sess: OneSession) -> None:
    total_sec = WORK_MIN * 60

    # Arrival ritual
    console.clear()
    console.print(arrival_screen(sess.task, sess.minutes))
    if sleep_with_quit(ARRIVAL_SEC):
        sess.interrupted = True
        return

    bell()
    log_event({"event": "one_start", "task": sess.task, "minutes": WORK_MIN})

    start = time.time()
    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while True:
            elapsed = time.time() - start
            if elapsed >= total_sec:
                break

            remaining = max(0, int(total_sec - elapsed))
            live.update(Align.center(work_screen(sess.task, remaining), vertical="middle"))

            ch = read_key_nonblocking()
            if ch and ch.lower() == "q":
                sess.interrupted = True
                break

            time.sleep(FRAME_DT)

    bell()


def run_break() -> bool:
    """Return True if user quit during break."""
    total_sec = BREAK_MIN * 60
    start = time.time()

    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while True:
            elapsed = time.time() - start
            if elapsed >= total_sec:
                break

            remaining = max(0, int(total_sec - elapsed))
            live.update(Align.center(break_screen(remaining), vertical="middle"))

            ch = read_key_nonblocking()
            if ch and ch.lower() == "q":
                return True

            time.sleep(FRAME_DT)

    return False


def ask_outcome(sess: OneSession) -> None:
    console.clear()
    console.print(end_question())

    while True:
        ch = console.input("\n> ").strip().lower()
        if ch in ("y", "yes"):
            sess.outcome = "complete"
            return
        if ch in ("n", "no", ""):
            sess.outcome = "released"
            return


def main() -> None:
    task = choose_task()

    sess = OneSession(
        task=task,
        minutes=WORK_MIN,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    run_work(sess)

    # If user quit early, we still log and exit quietly.
    if sess.interrupted:
        log_event(
            {
                "event": "one_end",
                "task": sess.task,
                "minutes": WORK_MIN,
                "interrupted": True,
                "outcome": "released",
            }
        )
        console.clear()
        return

    # Time ended: auto-exit after acknowledgment and break rule
    ask_outcome(sess)

    # Mandatory break after deep work
    log_event({"event": "break_start", "minutes": BREAK_MIN})
    console.clear()
    quit_break = run_break()
    log_event({"event": "break_end", "minutes": BREAK_MIN, "interrupted": quit_break})

    log_event(
        {
            "event": "one_end",
            "task": sess.task,
            "minutes": WORK_MIN,
            "interrupted": False,
            "outcome": sess.outcome,
        }
    )

    console.clear()
    # auto-exit (per your choice)


if __name__ == "__main__":
    main()