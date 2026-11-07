"""Records, canvas frames and the two generated pages. All pure except reading templates."""
from __future__ import annotations
import json, re
from pathlib import Path
from .check import best_verified, reuse_levels, split_csv
from .schema import TBD

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
FRAME_W, FRAME_H, GAP = 440, 300, 40


def to_record(p) -> dict:
    f = p.fields
    files = split_csv(f.get("Files", ""))
    tools = {pr.fields["Tool"].split(" · 20")[0] for pr in p.prompts if pr.fields.get("Tool")}
    tools.add(f.get("Defaults", ""))
    art, pat = reuse_levels(f.get("Reusability", ""))
    return {
        "name": p.name, "folder": p.folder, "source": p.source, "files": files,
        "open": next((f"{p.folder}/{x}" for x in files if x.endswith(".html")), None),
        "dates": f.get("Dates", TBD), "defaults": f.get("Defaults", TBD),
        "tools": sorted(t for t in tools if t and t != TBD),
        "status": f.get("Status", TBD), "use": f.get("Use", TBD),
        "artifact_reuse": art, "prompt_reuse": pat, "tags": split_csv(f.get("Tags", "")),
        "takeaway": f.get("Takeaway", TBD), "story_value": f.get("Story value", TBD),
        "surprises": f.get("Surprises", TBD), "prompt_count": len(p.prompts),
        "verified": best_verified(p),
    }


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"


def _el(t, props, children=None):
    return {"type": t, "props": props, "children": children or []}


def unique_ids(records) -> list:
    """Stable, collision-free frame ids: ledger-<folder>-<name>, suffixed -2, -3 on a clash."""
    seen, out = {}, []
    for r in records:
        base = f"ledger-{slug(r['folder'])}-{slug(r['name'])}"
        seen[base] = seen.get(base, 0) + 1
        out.append(base if seen[base] == 1 else f"{base}-{seen[base]}")
    return out


def canvas_frames(records) -> list:
    """Frames in the shape used by quantlink-inc/canvas (lib/canvas/pages.ts)."""
    frames = [
        {"id": "ledger-summary", "x": 0, "y": 0, "w": 480, "h": 320, "title": "Summary", "kind": "page",
         "spec": {"root": "root", "elements": {
             "root": _el("Stack", {"direction": "column", "gap": "sm"}, ["h", "m1", "m2", "m3"]),
             "h": _el("Heading", {"text": "Project Ledger", "level": "h3"}),
             "m1": _el("Metric", {"label": "Projects", "value": str(len(records)), "trend": None}),
             "m2": _el("Metric", {"label": "Keepers", "value": str(sum(r["status"] == "keeper" for r in records)), "trend": None}),
             "m3": _el("Metric", {"label": "Prompts recorded", "value": str(sum(r["prompt_count"] for r in records)), "trend": None}),
         }}},
        {"id": "ledger-catalog", "x": 520, "y": 0, "w": 760, "h": 320, "title": "Catalog", "kind": "sheet",
         "spec": {"root": "root", "elements": {
             "root": _el("Stack", {"direction": "column", "gap": "sm"}, ["h", "t"]),
             "h": _el("Heading", {"text": "Catalog", "level": "h3"}),
             "t": _el("Sheet", {"columns": ["Project", "Status", "Verified", "Use"],
                                "rows": [[r["name"], r["status"], r["verified"], r["use"]] for r in records]}),
         }}},
    ]
    for i, (r, fid) in enumerate(zip(records, unique_ids(records))):
        frames.append({
            "id": fid, "x": (i % 3) * (FRAME_W + GAP), "y": 360 + (i // 3) * (FRAME_H + GAP),
            "w": FRAME_W, "h": FRAME_H, "title": r["name"], "kind": "page",
            "spec": {"root": "root", "elements": {
                "root": _el("Stack", {"direction": "column", "gap": "sm"}, ["h", "t", "m1", "m2", "m3", "g"]),
                "h": _el("Heading", {"text": r["name"], "level": "h3"}),
                "t": _el("Text", {"text": r["takeaway"], "variant": "muted"}),
                "m1": _el("Metric", {"label": "Status", "value": r["status"], "trend": None}),
                "m2": _el("Metric", {"label": "Verified", "value": r["verified"], "trend": None}),
                "m3": _el("Metric", {"label": "Use", "value": r["use"], "trend": None}),
                "g": _el("Text", {"text": ", ".join(r["tags"]) or "no tags", "variant": "caption"}),
            }}})
    return frames


def embed_json(obj) -> str:
    """JSON safe to place inside <script type="application/json">: no '<' ever appears."""
    return json.dumps(obj).replace("<", "\\u003c")


def index_html(records, date: str) -> str:
    return (TEMPLATES / "index.html").read_text().replace("__DATA__", embed_json(records)).replace("__DATE__", date)


def canvas_html(frames) -> str:
    return (TEMPLATES / "canvas.html").read_text().replace("__FRAMES__", embed_json(frames))
