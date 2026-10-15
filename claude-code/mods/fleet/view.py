"""Fleet in its own terminal tab: every local Claude chat, the ones waiting on you first.

Run it in a Zed terminal tab you rename to "fleet". Press a row's letter to jump to that
chat's tab. Zed has no "focus this tab" command, so the jump reads the tab order Zed saved
and presses Zed's next/previous-tab keys that many times (needs Accessibility for Zed).
Never calls a model. Keys: a letter jumps, r refreshes, q quits.
"""

import curses
import importlib.util
import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("fleet_scan", os.path.join(HERE, "scan.py"))
scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan)

TICK_S = 3
FLEET_TAB = "fleet"
NEXT_TAB, PREV_TAB = "]", "["  # with cmd+shift: Zed's pane::ActivateNextItem / ActivatePreviousItem
KEYS = [k for k in "abcdefghijklmnopstuvwxyz"]  # q and r are taken
SECTIONS = [
    ("question", "Asking you"),
    ("permission", "Needs approval"),
    ("finished", "Finished"),
    ("working", "Working"),
]


def age(secs):
    secs = max(0, int(secs or 0))
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    return f"{secs // 3600}h{secs % 3600 // 60}m"


def tab_position(title):
    """(steps, why): how many tabs to move from the fleet tab to the tab titled `title`."""
    for workspace in scan.zed_terminals():
        titles = [t for _, t in workspace["tabs"]]
        if FLEET_TAB in titles and title in titles:
            n = len(titles)
            forward = (titles.index(title) - titles.index(FLEET_TAB)) % n
            return (forward if forward <= n - forward else forward - n), ""
    return None, f'no Zed window has both a "{FLEET_TAB}" tab and a "{title}" tab'


def jump(title):
    steps, why = tab_position(title)
    if steps is None:
        return why
    if steps == 0:
        return ""
    key = NEXT_TAB if steps > 0 else PREV_TAB
    script = (
        'tell application "System Events" to repeat %d times\n'
        'keystroke "%s" using {command down, shift down}\n'
        "delay 0.04\n"
        "end repeat" % (abs(steps), key)
    )
    run = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return "" if run.returncode == 0 else "jump failed: allow Zed in System Settings > Privacy > Accessibility"


class Screen:
    def __init__(self, win):
        self.win = win
        curses.use_default_colors()  # keep the terminal's own background
        curses.curs_set(0)
        pairs = {"question": curses.COLOR_RED, "permission": curses.COLOR_YELLOW, "finished": curses.COLOR_GREEN,
                 "sub": curses.COLOR_CYAN, "bg": curses.COLOR_MAGENTA}
        self.color = {}
        for i, (name, fg) in enumerate(pairs.items(), start=1):
            curses.init_pair(i, fg, -1)
            self.color[name] = curses.color_pair(i)
        self.dim = curses.A_DIM
        self.y = 0

    def put(self, x, text, attr=0):
        h, w = self.win.getmaxyx()
        if self.y < h - 1 and x < w:
            self.win.addnstr(self.y, x, text, max(0, w - x - 1), attr)

    def right(self, text, attr=0):
        _, w = self.win.getmaxyx()
        self.put(max(0, w - len(text) - 2), text, attr)

    def line(self):
        self.y += 1


def draw(screen, data, keymap, message, stamp):
    win = screen.win
    win.erase()
    _, w = win.getmaxyx()
    screen.y = 0
    rows = data["sessions"]
    counts = "   ".join(f"{title} {sum(r['group'] == g for r in rows)}" for g, title in SECTIONS[:2])
    screen.put(1, "Fleet", curses.A_BOLD)
    screen.put(8, counts, screen.dim)
    screen.right(f"live · {age(time.time() - stamp)} ago", screen.dim)
    screen.line()
    keys = iter(KEYS)
    keymap.clear()
    for group, title in SECTIONS:
        members = [r for r in rows if r["group"] == group]
        if not members:
            continue
        screen.line()
        head = f"{title} {len(members)} "
        screen.put(1, head, screen.color.get(group, 0) | curses.A_BOLD)
        screen.put(1 + len(head), "─" * max(0, w - len(head) - 4), screen.dim)
        screen.line()
        is_loud = group in ("question", "permission")
        for r in members:
            key = next(keys, None) if r["tab"] else None
            if key:
                keymap[key] = r["tab"]
            screen.put(1, f"[{key}]" if key else "   ", curses.A_BOLD if key else screen.dim)
            screen.put(5, "BG  " if r["kind"] == "bg" else "MAIN", screen.color["bg"] if r["kind"] == "bg" else screen.dim)
            name = r["name"] + (f" ({r['tab']})" if r["tab"] else "")
            screen.put(10, name, curses.A_BOLD if is_loud else 0)
            ctx = f"{r['ctxPct']}% " if r["ctx"] else ""
            band = r["ctxBand"]
            screen.right(f"{ctx}{age(r['secs'])}", screen.color["question"] if band >= 3 else screen.color["permission"] if band else screen.dim)
            screen.line()
            call = r["pending"][-1] if r["pending"] else None
            if is_loud and call:
                screen.put(10, call["tool"] + " ", screen.color.get(group, 0))
                screen.put(11 + len(call["tool"]), call["text"])
                screen.line()
                if call.get("options"):
                    screen.put(10, "  /  ".join(call["options"]), screen.dim)
                    screen.line()
            elif is_loud and not any(x["state"] == "waiting" for x in r["subs"]):
                stuck = (r.get("turnSecs") or 0) > 600
                note = f"says waiting, but no turn for {age(r['turnSecs'])}: check the chat" if stuck else r["last"]
                screen.put(10, note, screen.color["permission"] if stuck else screen.dim)
                screen.line()
            elif group == "finished" and r["last"]:
                screen.put(10, r["last"], screen.dim)
                screen.line()
            for x in r["subs"]:
                if x["state"] != "waiting" and not is_loud:
                    continue
                screen.put(12, "↳ SUB ", screen.color["sub"])
                screen.put(18, f"{x['name']} {x['model'] or x['type']}")
                screen.right(age(x["secs"]), screen.dim)
                screen.line()
                if x["state"] == "waiting" and x["pending"]:
                    screen.put(18, x["pending"]["tool"] + " ", screen.color["permission"])
                    screen.put(19 + len(x["pending"]["tool"]), x["pending"]["text"])
                    screen.line()
    screen.line()
    screen.put(1, message or "letter: jump to that chat's tab · r: refresh · q: quit", screen.dim)
    win.refresh()


def main(win):
    screen = Screen(win)
    win.timeout(250)
    keymap, message = {}, ""
    data, stamp = scan.snapshot(), time.time()
    while True:
        if time.time() - stamp >= TICK_S:
            data, stamp = scan.snapshot(), time.time()
        draw(screen, data, keymap, message, stamp)
        ch = win.getch()
        if ch == -1:
            continue
        key = chr(ch) if 0 <= ch < 256 else ""
        if key == "q":
            return
        if key == "r":
            data, stamp, message = scan.snapshot(), time.time(), ""
        elif key in keymap:
            message = jump(keymap[key])


if __name__ == "__main__":
    # Name the tab once in its title bar; Zed's own rename is what the jump looks up.
    print(f"\033]0;{FLEET_TAB}\007", end="", flush=True)
    curses.wrapper(main)
