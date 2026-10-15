"""Prints one JSON snapshot of every live local Claude session for the fleet pane.

Reads ~/.claude/sessions/<pid>.json for status and the tail of each transcript for
what the session is blocked on. Never calls a model.
"""

import glob
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import time

HOME = os.path.expanduser("~")
SESSIONS = f"{HOME}/.claude/sessions"
PROJECTS = f"{HOME}/.claude/projects"
TAIL_BYTES = 262144
SUB_RECENT_S = 600  # a subagent file untouched this long is finished or abandoned
SUB_STUCK_S = 8  # an unanswered subagent call older than this waits on a prompt
STALE_S = 7200  # a session or handoff file untouched this long is hidden
ZED_DB = f"{HOME}/Library/Application Support/Zed/db/0-stable/db.sqlite"
WRAPPERS = {"timeout", "rtk", "proxy", "env", "sudo", "nice", "time", "command", "exec", "eval"}
FALLBACK_BANDS = (0.5, 0.7, 0.85)
FALLBACK_WINDOW = 500_000
_ctx_modules = {}


def ctx_band(cwd, tokens):
    """Context share and band, from the repo's own .claude/hooks/ctx.py when it has one."""
    if cwd not in _ctx_modules:
        mod = None
        path = os.path.join(cwd, ".claude", "hooks", "ctx.py")
        if os.path.exists(path):
            try:
                spec = importlib.util.spec_from_file_location(f"ctx_{len(_ctx_modules)}", path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            except Exception:
                mod = None
        _ctx_modules[cwd] = mod
    mod = _ctx_modules[cwd]
    limit = mod.window(cwd) if mod else FALLBACK_WINDOW
    bands = mod.BANDS if mod else FALLBACK_BANDS
    return round(100 * tokens / limit), sum(1 for b in bands if tokens >= b * limit)


def main_checkout(cwd):
    out = subprocess.run(["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         capture_output=True, text=True).stdout.strip()
    return os.path.dirname(out) if out.endswith("/.git") else ""


def handoffs(roots, now):
    """handoff/*.md in each main checkout, with the owner named on line 1."""
    out = []
    for root in sorted(roots):
        for path in sorted(glob.glob(f"{root}/handoff/*.md")):
            try:
                with open(path) as f:
                    head = f.readline().strip()
            except OSError:
                head = ""
            if now - os.path.getmtime(path) > STALE_S:
                continue
            owner = re.split(r",| \(| for |\. ", re.sub(r"^Owner:\s*", "", head))[0].strip()
            out.append({
                "file": os.path.basename(path),
                "owner": owner,
                "secs": int(now - os.path.getmtime(path)),
            })
    return out


def tail_entries(path, size=TAIL_BYTES):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            end = f.tell()
            f.seek(max(0, end - size))
            raw = f.read().decode("utf-8", "replace")
    except OSError:
        return []
    out = []
    for line in raw.splitlines()[1:] if end > size else raw.splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def one_line(text, n=160):
    return re.sub(r"\s+", " ", str(text or "")).strip()[:n]


def command_key(command):
    """The command a Bash call runs, as its first two words: 'git merge-base', 'pnpm install'."""
    for part in re.split(r"&&|;|\|\|", str(command or "")):
        words = part.split()
        # Wrappers run the real command after them: timeout 300 <cmd>, rtk proxy <cmd>, env X=1 <cmd>.
        while words and (words[0] in WRAPPERS or "=" in words[0] or words[0].isdigit()):
            words = words[1:]
        if not words or words[0] in ("cd", "set", "export", "echo"):
            continue
        if words[0] in ("for", "while", "if"):
            return f"{words[0]} loop"
        second = words[1] if len(words) > 1 and re.fullmatch(r"[a-z][\w:-]*", words[1]) else ""
        return f"{words[0]} {second}".strip()
    return ""


def call(tool, text, key=None, options=None):
    out = {"tool": tool, "text": one_line(text), "key": key or tool}
    if options:
        out["options"] = options
    return out


def summarise(name, args):
    """Turns a tool call into what the pane shows: tool, what it does, and a key that groups repeats."""
    args = args if isinstance(args, dict) else {}
    short = name.split("__")[-1] if name.startswith("mcp__") else name
    if name == "AskUserQuestion":
        q = (args.get("questions") or [{}])[0]
        return call("Question", q.get("question"), options=[one_line(o.get("label"), 40) for o in q.get("options") or []])
    if name == "Bash":
        cmd = args.get("command")
        return call("Bash", args.get("description") or cmd, "Bash " + (command_key(cmd) or "?"))
    if name in ("Edit", "Write", "Read", "NotebookEdit"):
        return call(name, os.path.basename(str(args.get("file_path", ""))))
    if name == "Agent":
        return call("Agent", args.get("description"))
    if name == "Skill":
        return call("Skill", args.get("skill"), "Skill " + str(args.get("skill")))
    if name == "ExitPlanMode":
        return call("Plan", "approve plan")
    key = next((args[k] for k in ("issueId", "id", "url", "query", "title", "project_id") if args.get(k)), None)
    if key is None:
        key = next((v for v in args.values() if isinstance(v, str)), "")
    server = name.split("__")[1] if name.startswith("mcp__") else ""
    label = f"{server}.{short}" if server else short
    return call(label, key, label)


def read_transcript(entries):
    """Unanswered tool calls, last assistant text, branch and context size."""
    answered, calls, last_text, branch, ctx, turn_at = set(), [], "", "", 0, ""
    for e in entries:
        branch = e.get("gitBranch") or branch
        if e.get("type") in ("user", "assistant"):
            turn_at = e.get("timestamp") or turn_at
        msg = e.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        if e.get("type") == "user":
            for b in content:
                if b.get("type") == "tool_result":
                    answered.add(b.get("tool_use_id"))
        elif e.get("type") == "assistant":
            u = msg.get("usage") or {}
            ctx = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (
                u.get("cache_creation_input_tokens") or 0
            ) or ctx
            for b in content:
                if b.get("type") == "tool_use":
                    calls.append(b)
                elif b.get("type") == "text" and b.get("text", "").strip():
                    last_text = b["text"]
    pending = [summarise(c.get("name", ""), c.get("input")) for c in calls if c.get("id") not in answered]
    return pending, last_text, branch, ctx, turn_at


def secs_since(iso, now):
    try:
        return int(now - time.mktime(time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")) + time.localtime().tm_gmtoff * -1)
    except (TypeError, ValueError):
        return None


def zed_terminals():
    """Zed's terminal tabs per workspace, in tab-bar order: [{workspace, tabs: [(item_id, custom title)]}].

    Zed saves this to its own DB a moment after a change. It stores no pid, so tabs match chats by name."""
    try:
        db = sqlite3.connect(f"file:{ZED_DB}?mode=ro", uri=True, timeout=0.2)
        titles = {(w, i): t or "" for w, i, t in db.execute("select workspace_id, item_id, custom_title from terminals")}
        layouts = db.execute("select key, value from kv_store where key like '\"TerminalPanel\"-%'").fetchall()
    except sqlite3.Error:
        return []
    out = []
    for key, value in layouts:
        workspace = int(key.split("-")[-1].strip('"'))
        order = []

        def walk(node):
            if "Pane" in node:
                order.extend(node["Pane"].get("children") or [])
            for child in (node.get("Group") or {}).get("children") or []:
                walk(child)

        try:
            walk(json.loads(value).get("items") or {})
        except (ValueError, AttributeError):
            continue
        out.append({"workspace": workspace, "tabs": [(i, titles.get((workspace, i), "")) for i in order]})
    return out


DATE_WORD = re.compile(r"^(\d{1,2}[a-z]{3}|[a-z]{3}\d{1,2})$")  # 15oct, oct15
TAB_OVERRIDES = f"{HOME}/.claude/fleet-tabs.json"  # {"<chat name>": "<tab title>"} for pairs no rule can find


def name_words(text):
    return [w for w in re.split(r"[\s\-_]+", text.lower()) if w and not DATE_WORD.match(w)]


def word_fits(tab_word, chat_word):
    """Same word, one inside the other (review in codereview), or the same first 3 letters (deps, dependency)."""
    if tab_word == chat_word:
        return True
    short, long_ = sorted((tab_word, chat_word), key=len)
    return len(short) >= 3 and (short in long_ or tab_word[:3] == chat_word[:3])


def coverage(tab, chat):
    """Share of the chat's words the tab names, when every tab word fits one; else 0."""
    tw, cw = name_words(tab), name_words(chat)
    if not tw or not cw or not all(any(word_fits(t, c) for c in cw) for t in tw):
        return 0
    return sum(any(word_fits(t, c) for t in tw) for c in cw) / len(cw)


def match_tabs(names, tabs):
    """{chat name: tab title}. Overrides first, then each tab to the chat it covers best, best pairs first."""
    try:
        out = {k: v for k, v in json.load(open(TAB_OVERRIDES)).items() if k in names and v in tabs}
    except (OSError, ValueError):
        out = {}
    pairs = sorted(((coverage(t, n), n, t) for t in tabs for n in names), reverse=True)
    used = set(out.values())
    for score, name, tab in pairs:
        if score > 0 and name not in out and tab not in used:
            out[name] = tab
            used.add(tab)
    return out


def first_line(text):
    for line in (text or "").splitlines():
        line = line.strip(" #*`>-")
        if line:
            return one_line(line)
    return ""


def subagents(transcript, now, is_parent_waiting):
    folder = transcript[: -len(".jsonl")] + "/subagents"
    out = []
    for path in glob.glob(f"{folder}/*.jsonl"):
        age = now - os.path.getmtime(path)
        if age > SUB_RECENT_S:
            continue
        entries = tail_entries(path, 65536)
        if not entries:
            continue
        last = entries[-1]
        content = (last.get("message") or {}).get("content")
        is_done = (
            last.get("type") == "assistant"
            and isinstance(content, list)
            and not any(b.get("type") == "tool_use" for b in content)
        )
        if is_done:
            continue
        try:
            meta = json.load(open(path[: -len(".jsonl")] + ".meta.json"))
        except (OSError, ValueError):
            meta = {}
        pending, _, _, _, _ = read_transcript(entries)
        # A subagent's prompt shows on its parent, so it can only wait while the parent does.
        is_stuck = is_parent_waiting and bool(pending) and age > SUB_STUCK_S
        out.append(
            {
                "name": one_line(meta.get("description") or os.path.basename(path), 60),
                "type": meta.get("agentType", ""),
                "model": meta.get("model", ""),
                "isBackground": meta.get("requestShape") == "background",
                "state": "waiting" if is_stuck else "working",
                "pending": pending[-1] if is_stuck else None,
                "secs": int(age),
            }
        )
    return sorted(out, key=lambda s: (s["state"] != "waiting", s["secs"]))


GROUP_ORDER = {"question": 0, "permission": 1, "finished": 2, "working": 3}


def group_of(row):
    """Where the session sits in the views: question and permission wait on you."""
    if row["status"] == "waiting" or any(x["state"] == "waiting" for x in row["subs"]):
        return "question" if any(c["tool"] == "Question" for c in row["pending"]) else "permission"
    return "finished" if row["status"] == "idle" else "working"


def snapshot():
    files = []
    for path in glob.glob(f"{SESSIONS}/*.json"):
        try:
            files.append(json.load(open(path)))
        except (OSError, ValueError):
            pass
    pids = ",".join(str(f["pid"]) for f in files if f.get("pid"))
    ps = subprocess.run(["ps", "-o", "pid=", "-p", pids], capture_output=True, text=True).stdout if pids else ""
    live = {int(p) for p in ps.split()}
    now = time.time()
    rows = []
    roots = set()
    tabs = sorted({t for w in zed_terminals() for _, t in w["tabs"] if t})
    for f in files:
        if f.get("pid") not in live:
            continue
        sid = f.get("sessionId", "")
        found = glob.glob(f"{PROJECTS}/*/{sid}.jsonl")
        touched = max([(f.get("updatedAt") or 0) / 1000] + [os.path.getmtime(p) for p in found])
        if now - touched > STALE_S:
            continue
        pending, last_text, branch, ctx, turn_at = read_transcript(tail_entries(found[0])) if found else ([], "", "", 0, "")
        cwd = f.get("cwd") or HOME
        pct, band = ctx_band(cwd, ctx)
        roots.add(main_checkout(cwd))
        since = (f.get("statusUpdatedAt") or f.get("updatedAt") or now * 1000) / 1000
        rows.append(
            {
                "sessionId": sid,
                "name": f.get("name") or sid[:8],
                "kind": "bg" if f.get("kind") == "bg" else "main",
                "status": f.get("status") or "?",
                "waitingFor": f.get("waitingFor") or "",
                "secs": int(now - since),
                "branch": branch,
                "ctx": ctx,
                "ctxPct": pct,
                "ctxBand": band,
                "pending": pending,
                "last": first_line(last_text),
                "turnSecs": secs_since(turn_at, now),
                "subs": subagents(found[0], now, f.get("status") == "waiting") if found else [],
            }
        )
    matched = match_tabs([r["name"] for r in rows], tabs)
    for r in rows:
        r["tab"] = matched.get(r["name"], "")
        r["group"] = group_of(r)
    rows.sort(key=lambda r: (GROUP_ORDER[r["group"]], -r["secs"]))
    return {"sessions": rows, "handoffs": handoffs(roots - {""}, now)}


if __name__ == "__main__":
    print(json.dumps(snapshot()))
