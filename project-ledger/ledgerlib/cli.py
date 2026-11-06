from __future__ import annotations
import argparse, datetime as dt, json, re, sys
from collections import Counter
from pathlib import Path
from . import capture as cap
from .check import validate
from .export import canvas_frames, canvas_html, index_html, to_record
from .parse import known_tags, load_all, parse_text
from .schema import record_schema

ROOT = Path(__file__).resolve().parent.parent
USAGE = """ledger: track one-off AI-assisted projects.
  new <name> [--tool T] [--group G]   scaffold a project folder
  check [--strict]                    validate every prompts.md
  build                               write index.html, canvas.html, canvas-frames.json
  stats                               what is actually working
  capture <session.jsonl> <project>   append prompts/outputs from a Claude Code transcript
  schema                              print the JSON Schema for catalog records"""


def cmd_check(a):
    projects = load_all(ROOT)
    if not projects:
        print("no projects found"); return 0
    tags = known_tags((ROOT / "CONVENTIONS.md").read_text())
    errs = warns = 0
    for p in projects:
        for i in validate(p, tags, lambda n, p=p: (ROOT / p.folder / n).exists()):
            print(f"{i.severity[:5]:5} {i.code} {p.source} [{p.name}]: {i.message}")
            errs += i.severity == "error"; warns += i.severity == "warning"
    print(f"{len(projects)} projects, {errs} errors, {warns} warnings")
    return 1 if errs or (a.strict and warns) else 0


def cmd_build(a):
    recs = [to_record(p) for p in load_all(ROOT)]
    frames = canvas_frames(recs)
    (ROOT / "index.html").write_text(index_html(recs, dt.date.today().isoformat()))
    (ROOT / "canvas-frames.json").write_text(json.dumps(frames, indent=2) + "\n")
    (ROOT / "canvas.html").write_text(canvas_html(frames))
    print(f"wrote index.html, canvas-frames.json, canvas.html ({len(recs)} projects)")
    return 0


def cmd_stats(a):
    recs = [to_record(p) for p in load_all(ROOT)]
    if not recs:
        print("no projects"); return 0
    fmt = lambda c: ", ".join(f"{k}={v}" for k, v in c.most_common())
    print(f"{len(recs)} projects, {sum(r['prompt_count'] for r in recs)} prompts")
    for label, key in [("status", "status"), ("verified", "verified"),
                       ("artifact reuse", "artifact_reuse"), ("prompt reuse", "prompt_reuse")]:
        print(f"{label:15}", fmt(Counter(r[key] for r in recs)))
    print("tools          ", fmt(Counter(t for r in recs for t in r["tools"])))
    print("tags           ", fmt(Counter(t for r in recs for t in r["tags"])))
    used = [r for r in recs if not r["use"].lower().startswith(("none", "tbd"))]
    print(f"actually used  {len(used)}/{len(recs)}")
    print(f"needed >1 prompt: {sum(r['prompt_count'] > 1 for r in recs)}/{len(recs)}")
    return 0


def cmd_new(a):
    name = re.sub(r"[^a-z0-9]+", "_", a.name.lower()).strip("_")
    if not name:
        sys.exit("name must contain letters or digits")
    d = ROOT / "projects" / (a.group or "") / name
    if d.exists():
        sys.exit(f"{d} exists")
    d.mkdir(parents=True)
    title = a.name.replace("_", " ").title() if "_" in a.name or a.name.islower() else a.name
    tpl = (ROOT / "templates" / "prompts.md").read_text()
    (d / "prompts.md").write_text(tpl.replace("{{TITLE}}", title).replace("{{TOOL}}", a.tool)
                                  .replace("{{DATE}}", dt.date.today().isoformat()).replace("{{FILE}}", f"{name}.html"))
    print(f"created {d.relative_to(ROOT)}/prompts.md: fill in the prompt, drop {name}.html next to it")
    return 0


def cmd_capture(a):
    target = next((ROOT / "projects").rglob(f"{a.project}/prompts.md"), None)
    if not target:
        sys.exit(f"no project folder named {a.project}; run `new` first")
    existing = len(parse_text(target.read_text())[0].prompts) if target.read_text().strip() else 0
    turns = cap.read_turns(Path(a.session).read_text())
    if a.last:
        turns = turns[-a.last:]
    with target.open("a") as fh:
        fh.write(cap.render_turns(turns, existing + 1))
    print(f"appended {len(turns)} prompt(s) to {target.relative_to(ROOT)}. "
          "Verified defaults to not-run: raise it only if it is true.")
    return 0


def cmd_schema(a):
    print(json.dumps(record_schema(), indent=2)); return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ledger", description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("name"); n.add_argument("--tool", default="Claude Code · TBD"); n.add_argument("--group")
    c = sub.add_parser("check"); c.add_argument("--strict", action="store_true")
    sub.add_parser("build"); sub.add_parser("stats"); sub.add_parser("schema")
    k = sub.add_parser("capture"); k.add_argument("session"); k.add_argument("project"); k.add_argument("--last", type=int)
    a = ap.parse_args(argv)
    return {"new": cmd_new, "check": cmd_check, "build": cmd_build, "stats": cmd_stats,
            "capture": cmd_capture, "schema": cmd_schema}[a.cmd](a)
