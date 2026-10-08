#!/usr/bin/env python3
"""Claude Code status line. One row per group: a heading, a coloured
lead value, then items.
  Agent   <model>  effort · context bar
  Usage   <% left in the tightest window>  5h bar · week bar, each with reset
  Git     <branch>
Beyond the flagship, colour only marks a value that needs attention.
Reads the session JSON on stdin. Fails silently (prints nothing) on any error
so a broken status line never disrupts the prompt."""
import sys, os, json, subprocess, time

# ANSI helpers
def c(code, s): return "\033[" + code + "m" + s + "\033[0m" if code else s
# Muted truecolor palette, readable on light and dark backgrounds
DIM = "2"; GREY = "38;2;140;140;140"; GREEN = "38;2;88;160;112"; YELLOW = "38;2;204;145;48"
RED = "38;2;206;88;78"; BLUE = "38;2;82;132;204"; CYAN = "38;2;62;152;164"; MAGENTA = "38;2;152;112;204"
MODEL_COLORS = {"opus": MAGENTA, "sonnet": CYAN, "haiku": GREEN}
BRANCH_COLORS = {"main": RED, "master": RED, "production": RED, "development": BLUE}
HEAD_W = 8
ICONS = {"Linear": "◆", "Agent": "✦", "Usage": "◔", "Git": "⎇", "Prod": "▲"}


def row(heading, flagship, items):
    """One status row: heading in a fixed column, the coloured lead value, then dim-separated items."""
    out = heading.ljust(HEAD_W) + "  " + flagship
    items = [i for i in items if i]
    if items:
        out += "  " + c(DIM, " · ").join(items)
    return out


def level(pct, warn, crit):
    return GREEN if pct < warn else (YELLOW if pct < crit else RED)


def bar(pct, warn, crit, cells=10):
    """━━━─────── with the filled part coloured by threshold."""
    filled = min(cells, round(pct * cells / 100))
    return c(level(pct, warn, crit), "━" * filled) + c(DIM, "─" * (cells - filled))


def agent_row(data):
    model = data.get("model") or {}
    name = model.get("display_name") or model.get("id") or "?"
    family = next((f for f in MODEL_COLORS if f in name.lower()), None)
    items = [(data.get("effort") or {}).get("level")]
    # context % as Claude Code reports it (null before the first API call)
    pct = (data.get("context_window") or {}).get("used_percentage")
    if pct is not None:
        items.append(c(DIM, "context ") + bar(pct, 50, 80) + " " + str(round(pct)) + "%")
    return row(ICONS["Agent"] + " Agent", c(MODEL_COLORS.get(family, BLUE), name), items)


def usage_row(data):
    """Plan usage. The flagship is what is left in the tightest window; each window shows a bar and its reset."""
    items, left = [], []
    for key, label in (("five_hour", "5h"), ("seven_day", "week")):
        lim = (data.get("rate_limits") or {}).get(key) or {}
        if lim.get("used_percentage") is None:
            continue
        pct = round(lim["used_percentage"])
        left.append(100 - pct)
        seg = c(DIM, label + " ") + bar(pct, 70, 90) + " " + str(pct) + "%"
        secs = (lim.get("resets_at") or 0) - time.time()
        if secs > 0:
            reset = ("%dh%02dm" % (secs // 3600, secs % 3600 // 60) if secs < 86400
                     else time.strftime("%a %-I%p", time.localtime(lim["resets_at"])))
            seg += c(DIM, " resets " + reset)
        items.append(seg)
    if not left:
        return None
    tight = min(left)
    return row(ICONS["Usage"] + " Usage", c(level(100 - tight, 70, 90), "%d%% left" % tight), items)

def git_row(cwd):
    def git(*args):
        return subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, timeout=1).stdout.strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":  # detached: show short sha
        branch = git("rev-parse", "--short", "HEAD") or "detached"
    return row(ICONS["Git"] + " Git", c(BRANCH_COLORS.get(branch, CYAN), branch), []) if branch else None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or os.getcwd()
    lines = []
    for build in (lambda: agent_row(data), lambda: usage_row(data), lambda: git_row(cwd)):
        try:
            lines.append(build())
        except Exception:
            pass
    sys.stdout.write("\n".join(l for l in lines if l))

if __name__ == "__main__":
    main()
