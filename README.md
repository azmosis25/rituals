STILLNESS / ONE / UNTANGLE

A small suite of terminal-based rituals.
No metrics. No streaks. No optimization.

Just breath, attention, language, and time.

⸻

What This Is

This repository contains three minimal terminal practices:

• STILLNESS — sit with breath
• ONE — do one thing
• UNTANGLE — name the next honest step

Each tool is intentionally narrow.
Each does one thing, then gets out of the way.

This is not a productivity system.
It is a set of containers for presence, action, and clarity.

⸻

Core Principles

• Presence over performance  
Nothing here is meant to be optimized.

• Legibility without numbers  
Time and breath are felt, not gamified.

• Ritual over routine  
Each practice has a clear beginning and ending.

• Data without pressure  
Logs exist quietly. They are never surfaced.

• Silence scales best  
As commitment increases, the interface disappears.

⸻

STILLNESS

A minimal meditation practice designed for the terminal.

STILLNESS supports showing up without striving.
There are no scores, charts, or progress indicators.

The interface is intentionally spare.
The experience is intentionally quiet.

This is closer to a digital zendo than an app.

— Breath Language —

The breath is rendered using three symbols, each representing one second:

• █ — inhale  
• ░ — hold (top or bottom)  
• ▒ — exhale

Symbols are spaced for clarity:

█ █ █ ░ ▒ ▒ ▒

Over time, the body learns the rhythm without instruction.

— Session Lengths —

• 1 minute — reset  
• 2 minutes — pause  
• 5 minutes — daily anchor  
• 10 minutes — settling  
• 20 minutes — deep sitting

Longer is not better.
Showing up is enough.

Run:

python stillness.py

⸻

ONE

A single-task container.

ONE holds exactly one task for a fixed span of time.
Not a list. Not a planner. Not a tracker.

You choose the task.
The container holds it.
Then it ends.

— Rules —

• Only one task  
• Fixed 25-minute session  
• Large, centered task text  
• Countdown timer (MM:SS)  
• Auto-exit when time ends

After a completed session, a mandatory 5-minute break follows.
This boundary is intentional.

Completion is acknowledged, not celebrated.

Run:

python one.py

⸻

UNTANGLE

A one-sentence clarity practice.

UNTANGLE exists to interrupt overthinking.
You may write only one sentence.
You cannot edit it.

The prompt is always:

name the next honest step

Nothing more is required.

— Quiet Recall (Optional) —

UNTANGLE can optionally display the previous sentence.
This is off by default.

When enabled, recall is:
• dim  
• non-interactive  
• limited to the last entry only

The intention is continuity, not rumination.

Run:

python untangle.py

⸻

Logging (Invisible by Design)

Each tool logs locally to a simple JSONL file.

Logs may include:
• timestamps  
• duration  
• completion or release

There are:
• no streaks  
• no summaries  
• no dashboards

The data exists, but it does not ask for attention.

⸻

What This Will Never Add

• Scores or ratings  
• Gamification  
• Leaderboards  
• Optimization loops

These tools are not meant to make you better.
They are meant to make you honest.

⸻

A Note on Use

Use these tools one at a time.
Do not chain them automatically.

Let friction teach you where attention resists.

If you feel the urge to add features,
consider whether that urge is the practice.

⸻

Closing

Nothing needs to change.

Sit.
Name.
Do one thing.

Then stop.
