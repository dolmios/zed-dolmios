#!/usr/bin/env python3
"""Claude Code status line: model | git branch | context % | session cost.
Reads the session JSON on stdin. Fails silently (prints nothing) on any error
so a broken status line never disrupts the prompt."""
import sys, os, json, subprocess

# ANSI helpers
def c(code, s): return "\033[" + code + "m" + s + "\033[0m"
DIM = "2"; CYAN = "36"; MAGENTA = "35"; GREEN = "32"; YELLOW = "33"; RED = "31"

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or os.getcwd()
    model = data.get("model") or {}
    model_name = model.get("display_name") or model.get("id") or "?"
    model_id = (model.get("id") or "").lower()

    segs = [c(CYAN, model_name)]

    # git branch
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=1)
        branch = r.stdout.strip()
        if branch == "HEAD":  # detached: show short sha
            r2 = subprocess.run(["git", "-C", cwd, "rev-parse", "--short", "HEAD"],
                               capture_output=True, text=True, timeout=1)
            branch = r2.stdout.strip() or "detached"
        if branch:
            segs.append(c(MAGENTA, branch))
    except Exception:
        pass

    # context % from transcript (last usage entry = tokens the model last saw)
    try:
        tpath = data.get("transcript_path")
        if tpath and os.path.exists(tpath):
            size = os.path.getsize(tpath)
            with open(tpath, "rb") as f:
                f.seek(max(0, size - 524288))
                chunk = f.read().decode("utf-8", "ignore")
            ctx_tokens = None
            for line in reversed(chunk.splitlines()):
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                msg = obj.get("message")
                usage = msg.get("usage") if isinstance(msg, dict) else None
                if usage:
                    ctx_tokens = (usage.get("input_tokens", 0)
                                  + usage.get("cache_read_input_tokens", 0)
                                  + usage.get("cache_creation_input_tokens", 0))
                    break
            if ctx_tokens:
                window = 1_000_000 if "1m" in model_id else 200_000
                pct = round(100 * ctx_tokens / window)
                color = GREEN if pct < 50 else (YELLOW if pct < 80 else RED)
                segs.append(c(color, "ctx " + str(pct) + "%"))
    except Exception:
        pass

    # session cost
    try:
        cost = (data.get("cost") or {}).get("total_cost_usd")
        if cost is not None:
            segs.append(c(DIM, "${:.2f}".format(cost)))
    except Exception:
        pass

    sys.stdout.write(c(DIM, "  ").join(segs))

if __name__ == "__main__":
    main()
