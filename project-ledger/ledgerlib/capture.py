"""Claude Code transcript (JSONL) -> prompt sections."""
from __future__ import annotations
import datetime as dt, json
from .parse import escape_body


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(b.get("text", "") for b in content
                     if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str))


def read_turns(jsonl_text: str) -> list:
    """One dict {prompt, output, model, start, end} per human prompt. Never raises on bad lines."""
    turns, cur = [], None
    for ln in jsonl_text.splitlines():
        try:
            ev = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(ev, dict):
            continue
        msg = ev.get("message") if isinstance(ev.get("message"), dict) else {}
        ts = ev.get("timestamp")
        if ev.get("type") == "user" and not ev.get("isMeta") and not ev.get("isSidechain"):
            c = msg.get("content")
            if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                if cur:
                    cur["end"] = ts
                continue
            t = _text(c).strip()
            if not t or t.startswith(("<command-", "<local-command", "<system-reminder")):
                continue
            cur = {"prompt": t, "output": "", "model": "", "start": ts, "end": ts}
            turns.append(cur)
        elif ev.get("type") == "assistant" and cur and not ev.get("isSidechain"):
            t = _text(msg.get("content")).strip()
            if t:
                cur["output"] = t  # last text block wins: it is the final message
            m = msg.get("model")
            if isinstance(m, str) and m:
                cur["model"] = m
            cur["end"] = ts
    return turns


def seconds(a, b):
    try:
        p = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return max(0, round((p(b) - p(a)).total_seconds()))
    except Exception:
        return "TBD"


def render_turns(turns, first_number: int) -> str:
    out = []
    for i, t in enumerate(turns, first_number):
        day = t["start"][:10] if isinstance(t["start"], str) and t["start"] else "TBD"
        out.append(f"\n# Prompt {i} (TBD: what this prompt is for):\n\n"
                   f"> - **Tool:** Claude Code · {t['model'] or 'TBD'} · {day}\n"
                   f"> - **Session:** {'fresh' if i == 1 else 'continued'} · attached: TBD\n"
                   f"> - **Time:** {seconds(t['start'], t['end'])}s\n"
                   f"> - **Verified:** not-run\n> - **Human edits:** TBD\n\n"
                   f"{escape_body(t['prompt'])}\n\n## Output {i}:\n\n{escape_body(t['output']) or 'TBD'}\n")
    return "".join(out)
