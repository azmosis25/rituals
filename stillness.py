from __future__ import annotations

import sys
import time
import math
import json
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.live import Live
from rich.text import Text
from rich.theme import Theme

# Green-forward, minimal theme
THEME = Theme(
    {
        "accent": "green",
        "accent_bold": "bold green",
        "accent_mid": "green",
        "accent_dim": "dim green",
        "border": "green",
    }
)

console = Console(theme=THEME)

# ---------- Config ----------

WAVE = "░▒▓█▓▒░"
WAVE_WIDTH = 18          # visual width of the breathing bar
FRAME_DT = 0.08          # seconds between frames (lower = smoother)

# If True, the live meditation view has no borders (clean full-screen feel)
ZEN_MODE = True

ARRIVAL_SEC = 30
INTEGRATE_SEC = 12
WHISPER_MIN_SEC = 35
WHISPER_SHOW_SEC = 4
MIND_SHOW_SEC = 60

# Local, invisible logging (JSONL). No streaks, no totals.
LOG_PATH = Path(__file__).with_name("stillness_log.jsonl")

SIGNATURE_LINES = [
    "nothing needs to change",
    "you are allowed to be here",
    "this breath is enough",
    "return to the body",
    "soften the effort",
]

MICRO_SEASON_INTENTIONS = {
    "winter": [
        "rest beneath effort",
        "nothing to accomplish",
        "let stillness hold you",
        "soften and remain",
    ],
    "spring": [
        "let attention grow",
        "begin again gently",
        "notice what opens",
        "arrive where you are",
    ],
    "summer": [
        "remain open",
        "breathe and widen",
        "stay with what is",
        "this breath is enough",
    ],
    "autumn": [
        "release what is complete",
        "let the mind untie itself",
        "exhale and simplify",
        "return to the body",
    ],
}

MIND_WORDS = ["scattered", "noticing", "settling", "open", "quiet", "vast"]


@dataclass
class Session:
    preset_key: str = ""
    name: str = "Zazen"
    minutes: int = 20
    intention: str = ""
    inhale: float = 4.5
    hold_top: float = 1.5
    exhale: float = 7.0
    hold_bottom: float = 0.0
    cue: str = "breathe"
    texture: str = WAVE
    deep: bool = False

    @classmethod
    def from_preset(cls, preset_key: str, minutes: int, intention: str) -> Session:
        preset = BREATH_PRESETS.get(preset_key)
        if not preset:
            raise ValueError(f"Unknown preset: {preset_key}")
        return cls(
            preset_key=preset_key,
            name=preset["label"],
            minutes=minutes,
            intention=intention,
            inhale=float(preset["inhale"]),
            hold_top=float(preset["hold_top"]),
            exhale=float(preset["exhale"]),
            hold_bottom=float(preset["hold_bottom"]),
            cue=str(preset["cue"]),
            texture=str(preset.get("texture", WAVE)),
            deep=False,
        )


BREATH_PRESETS = {
    "zazen": {
        "label": "Settle the nervous system",
        "inhale": 4.5,
        "hold_top": 1.5,
        "exhale": 7.0,
        "hold_bottom": 0.0,
        "texture": "░▒▓█▓▒░",
        "cue": "breathe",
    },
    "equal": {
        "label": "Balance and steady",
        "inhale": 5.0,
        "hold_top": 0.0,
        "exhale": 5.0,
        "hold_bottom": 0.0,
        "texture": "░▒▓▓▒░",
        "cue": "steady",
    },
    "box": {
        "label": "Regain control",
        "inhale": 4.0,
        "hold_top": 4.0,
        "exhale": 4.0,
        "hold_bottom": 4.0,
        "texture": "█ ▓ ▒ ░",
        "cue": "box",
    },
    "sigh": {
        "label": "Release tension",
        "inhale": 3.5,
        "hold_top": 0.0,
        "exhale": 7.5,
        "hold_bottom": 0.0,
        "texture": "░░▒▒▓▓▓",
        "cue": "release",
    },
}


# ---------- Rendering ----------

def _now_hhmm() -> str:
    return datetime.now().strftime("%H:%M")


def _micro_season_key(dt: datetime) -> str:
    # simple, stable mapping (no web needed): meteorological seasons
    m = dt.month
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    return "autumn"


def _pick_intention() -> str:
    dt = datetime.now()
    season = _micro_season_key(dt)
    options = MICRO_SEASON_INTENTIONS[season]
    # deterministic-ish daily rotation
    day_index = int(dt.strftime("%j"))  # day of year
    return options[day_index % len(options)]


def _mind_word(elapsed_sec: float) -> str:
    # slow drift through “weather” states
    idx = int(elapsed_sec // 90)  # change about every 90 seconds
    return MIND_WORDS[idx % len(MIND_WORDS)]


def _breath_phase(t: float, sess: Session) -> float:
    """
    Returns a value 0..1 describing breath fullness.
    0 = empty (bottom), 1 = full (top).
    Cycle: inhale -> hold_top -> exhale -> hold_bottom
    """
    cycle = sess.inhale + sess.hold_top + sess.exhale + sess.hold_bottom
    x = t % cycle

    if x < sess.inhale:
        # ease-in-out inhale
        p = x / sess.inhale
        return 0.5 - 0.5 * math.cos(math.pi * p)

    x -= sess.inhale
    if x < sess.hold_top:
        return 1.0

    x -= sess.hold_top
    if x < sess.exhale:
        p = x / sess.exhale
        return 0.5 + 0.5 * math.cos(math.pi * p)  # reverse ease
    return 0.0


def _breath_bar_by_phase(t: float, sess: Session, width: int) -> Text:
    """Semantic breath bar with spacing and phase coloring.

    Symbols (1 second each):
      █ = inhale   (bright)
      ░ = hold     (dim)
      ▒ = exhale   (mid)

    Rendered as spaced glyphs: "█ █ █ █".
    """
    cycle = sess.inhale + sess.hold_top + sess.exhale + sess.hold_bottom
    x = t % cycle

    parts: list[tuple[str, str]] = []  # (symbol, style)

    def add(sym: str, style: str, count: int):
        for _ in range(max(0, count)):
            parts.append((sym, style))

    # Inhale
    if x < sess.inhale:
        add("█", "accent_bold", int(x))
    else:
        add("█", "accent_bold", int(sess.inhale))
        x -= sess.inhale

        # Hold (top)
        if x < sess.hold_top:
            add("░", "accent_dim", int(x))
        else:
            add("░", "accent_dim", int(sess.hold_top))
            x -= sess.hold_top

            # Exhale
            if x < sess.exhale:
                add("▒", "accent_mid", int(x))
            else:
                add("▒", "accent_mid", int(sess.exhale))
                x -= sess.exhale

                # Hold (bottom)
                add("░", "accent_dim", int(min(x, sess.hold_bottom)))

    bar = Text(justify="center")
    for i, (sym, style) in enumerate(parts):
        if i:
            bar.append(" ")
        bar.append(sym, style=style)

    # Pad so the bar doesn't jitter in the center.
    # Each token is 1 char + 1 space (except last), so budget ~ width*2.
    target = width * 2
    if bar.plain.__len__() < target:
        bar.append(" " * (target - len(bar.plain)))
    return bar


# Helper: preview the full-cycle breath bar
def _breath_template(sess: Session, width: int) -> Text:
    """Render a full-cycle preview (whole seconds) for the selected practice."""
    parts: list[tuple[str, str]] = []

    def add(sym: str, style: str, count: int):
        for _ in range(max(0, count)):
            parts.append((sym, style))

    add("█", "accent_bold", int(sess.inhale))
    add("░", "accent_dim", int(sess.hold_top))
    add("▒", "accent_mid", int(sess.exhale))
    add("░", "accent_dim", int(sess.hold_bottom))

    t = Text(justify="center")
    for i, (sym, style) in enumerate(parts):
        if i:
            t.append(" ")
        t.append(sym, style=style)

    target = width * 2
    if len(t.plain) < target:
        t.append(" " * (target - len(t.plain)))
    return t


def home_screen(sess: Session) -> Panel:
    title = Text("STILLNESS", justify="center")
    title.stylize("accent_bold")

    intention = Text(sess.intention, justify="center")
    intention.stylize("italic accent")

    body = Text(justify="center")
    body.append("\n")
    body.append(f"time  {_now_hhmm()}\n", style="accent_dim")
    body.append(f"session  {sess.name}\n", style="accent_dim")
    body.append(f"duration  {sess.minutes} min\n", style="accent_dim")
    body.append("\n")
    body.append("breath\n", style="accent_dim")
    body.append(_breath_template(sess, WAVE_WIDTH))
    body.append("\n\n")
    body.append("mind  settling\n", style="accent_dim")
    body.append("\n")
    body.append("press ENTER to begin\n", style="accent")
    body.append("q then ENTER to quit\n", style="accent_dim")

    content = Align.center(Text.assemble(title, "\n\n", intention, "\n", body), vertical="middle")
    return Panel(content, border_style="border", padding=(1, 4))


def live_screen(fullness: float, cue: str, elapsed: float, sess: Session):
    bar_width = 10 if sess.deep else WAVE_WIDTH
    bar = _breath_bar_by_phase(elapsed, sess, bar_width)

    # deep sitting: terminal-as-void (no labels, no extra text)
    if sess.deep:
        return Align.center(Text.assemble("\n", bar, "\n"), vertical="middle")

    line1 = bar

    line2 = Text(cue, justify="center")
    line2.stylize("accent_dim")

    show_mind = elapsed < MIND_SHOW_SEC
    mind = Text(f"mind: {_mind_word(elapsed)}", justify="center")
    mind.stylize("accent_dim")

    quit_hint = Text("q to end", justify="center")
    quit_hint.stylize("accent_dim")

    if show_mind:
        assembled = Text.assemble("\n", line1, "\n\n", line2, "\n\n", mind, "\n\n", quit_hint, "\n")
    else:
        assembled = Text.assemble("\n", line1, "\n\n", line2, "\n\n", quit_hint, "\n")

    content = Align.center(assembled, vertical="middle")

    if ZEN_MODE:
        return content

    return Panel(content, border_style="border", padding=(1, 6))


def complete_screen():
    msg = Text(justify="center")
    msg.append("\ncomplete\n", style="accent_bold")
    msg.append("\nremain seated a moment\n", style="accent_dim")
    msg.append("\npress any key to return\n", style="accent_dim")
    content = Align.center(msg, vertical="middle")

    if ZEN_MODE:
        return content

    return Panel(content, border_style="border", padding=(1, 6))


def arrival_screen() -> Align:
    msg = Text(justify="center")
    msg.append("\narrive\n", style="accent_bold")
    msg.append("\nplace attention in the body\n", style="accent_dim")
    return Align.center(msg, vertical="middle")


def integrate_screen() -> Align:
    msg = Text(justify="center")
    msg.append("\nwhat are you carrying forward?\n", style="accent_bold")
    msg.append("\n(hold the answer gently)\n", style="accent_dim")
    return Align.center(msg, vertical="middle")


# ---------- Input helpers ----------

def read_key_nonblocking() -> Optional[str]:
    """
    Minimal cross-platform key read (best-effort).
    - On Windows: uses msvcrt.
    - On Unix: uses select + tty raw mode.
    """
    if sys.platform.startswith("win"):
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            return ch
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
        ch = sys.stdin.read(1)
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def wait_for_enter_or_quit() -> bool:
    """
    Returns True if ENTER pressed, False if quit.
    """
    while True:
        ch = console.input("")  # blocks for a line
        # VS Code terminal sends enter as empty line here
        if ch.strip().lower() == "q":
            return False
        return True


def bell() -> None:
    # Terminal bell (best-effort). Subtle anchor, no ticking.
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass

def sleep_with_quit(seconds: float) -> bool:
    """Sleep in small slices; return True if user pressed 'q'."""
    end = time.time() + seconds
    while time.time() < end:
        ch = read_key_nonblocking()
        if ch and ch.lower() == "q":
            return True
        time.sleep(0.05)
    return False


def log_event(event: dict) -> None:
    try:
        event = {**event, "ts": datetime.now().isoformat(timespec="seconds")}
        LOG_PATH.write_text("", encoding="utf-8") if not LOG_PATH.exists() else None
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # logging must never interrupt practice
        pass


# ---------- Main ----------


def configure_session(intention: str) -> Session:
    console.clear()

    # Build numbered menu in a calm centered layout
    keys = list(BREATH_PRESETS.keys())

    lines = Text(justify="center")
    lines.append("\nchoose a breath practice\n\n", style="accent_bold")

    for i, k in enumerate(keys, start=1):
        label = BREATH_PRESETS[k]["label"]
        lines.append(f"{i}. {label}\n", style="accent")

    lines.append("\nchoose duration (minutes)\n", style="accent_bold")
    lines.append("options: 1, 2, 5, 10, 20\n\n", style="accent_dim")
    lines.append("enter practice number (default 1): ", style="accent")

    card = Panel(
        Align.center(lines, vertical="middle"),
        border_style="border",
        padding=(1, 4),
        title="STILLNESS / CHOOSE",
        title_align="center",
    )
    console.print(card)

    choice_raw = console.input("")
    if not choice_raw.strip():
        choice_idx = 1
    else:
        try:
            choice_idx = int(choice_raw.strip())
        except ValueError:
            choice_idx = 1

    if choice_idx < 1 or choice_idx > len(keys):
        choice_idx = 1

    preset_key = keys[choice_idx - 1]

    console.print("\nDuration in minutes (default 5): ", style="accent")
    minutes_raw = console.input("")
    if not minutes_raw.strip():
        minutes = 5
    else:
        try:
            minutes = int(minutes_raw.strip())
        except ValueError:
            minutes = 20

    # guardrails
    if minutes < 1:
        minutes = 1
    if minutes > 180:
        minutes = 180
    if minutes not in (1, 2, 5, 10, 20):
        # snap to the nearest allowed duration
        allowed = [1, 2, 5, 10, 20]
        minutes = min(allowed, key=lambda x: abs(x - minutes))

    deep = False
    if minutes >= 20:
        console.print("\nDeep Sitting (terminal-as-void)? [y/N]: ", style="accent")
        deep_raw = console.input("").strip().lower()
        deep = deep_raw in ("y", "yes")

    sess = Session.from_preset(preset_key=preset_key, minutes=minutes, intention=intention)
    sess.deep = deep
    return sess


def run_session(sess: Session) -> None:
    total_sec = sess.minutes * 60
    start = time.time()
    interrupted = False

    # Arrival ritual
    console.clear()
    console.print(arrival_screen())
    if sleep_with_quit(ARRIVAL_SEC):
        # user chose to exit before the session began
        return
    bell()
    log_event(
        {
            "event": "session_start",
            "preset": sess.preset_key,
            "label": sess.name,
            "minutes": sess.minutes,
            "deep": sess.deep,
        }
    )

    with Live(refresh_per_second=30, console=console, screen=True) as live:
        # whisper line appears once per session (not in deep mode)
        rng = random.Random()
        rng.seed(f"{datetime.now().date().isoformat()}-{sess.preset_key}-{sess.minutes}")
        whisper_line = rng.choice(SIGNATURE_LINES)
        whisper_at = None
        if (not sess.deep) and total_sec > (WHISPER_MIN_SEC + 30):
            whisper_at = rng.uniform(WHISPER_MIN_SEC, max(WHISPER_MIN_SEC, total_sec - 25))
        whisper_until = None

        while True:
            elapsed = time.time() - start
            if elapsed >= total_sec:
                break

            fullness = _breath_phase(elapsed, sess)

            cue = sess.cue  # deliberately minimal
            if whisper_at is not None and whisper_until is None and elapsed >= whisper_at:
                whisper_until = elapsed + WHISPER_SHOW_SEC

            if whisper_until is not None and elapsed <= whisper_until:
                cue = whisper_line

            live.update(live_screen(fullness, cue, elapsed, sess))

            # allow quitting with q (nonblocking)
            ch = read_key_nonblocking()
            if ch and ch.lower() == "q":
                interrupted = True
                break

            time.sleep(FRAME_DT)

        bell()
        live.update(complete_screen())
        time.sleep(1.2)

    # Integration pause
    console.clear()
    console.print(integrate_screen())
    time.sleep(INTEGRATE_SEC)

    # wait for any key (best-effort)
    console.clear()
    console.print(complete_screen())
    console.print()
    console.print(" ", end="")

    log_event(
        {
            "event": "session_end",
            "preset": sess.preset_key,
            "label": sess.name,
            "minutes": sess.minutes,
            "deep": sess.deep,
            "interrupted": interrupted,
        }
    )


def main() -> None:
    intention = _pick_intention()
    sess = configure_session(intention=intention)

    console.clear()
    console.print(home_screen(sess))

    console.print()
    console.print(Align.center(Text("press ENTER to begin · q then ENTER to quit", style="accent_dim")))
    started = wait_for_enter_or_quit()
    if not started:
        console.clear()
        return

    run_session(sess)
    # return to the home screen after session
    console.clear()
    console.print(home_screen(sess))


if __name__ == "__main__":
    main()