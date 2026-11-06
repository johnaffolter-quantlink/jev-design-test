#!/usr/bin/env python3
"""ledger -- tiny, dependency-free tooling for a ledger of one-off AI-assisted apps.

Reads the `prompts.md` convention (a superset of paulkaefer/vibe-coding's
CONVENTIONS.md) and turns it into something queryable.

  ledger.py new <name> [--tool T] [--group G]   scaffold a project folder
  ledger.py check [--strict]                    lint every prompts.md
  ledger.py build                               write index.html and
                                              canvas frames (canvas-frames.json)
  ledger.py stats                               what's actually working?
  ledger.py capture <session.jsonl> <project>   append prompts/outputs from a
                                              Claude Code transcript

Markdown stays the source of truth; everything else is generated.
"""
import argparse, datetime as dt, html, json, re, subprocess, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / "projects"
REQUIRED = ["Files", "Dates", "Defaults", "Status", "Use", "Reusability",
            "Tags", "Takeaway", "Story value", "Surprises"]
STATUS = {"prototype", "keeper", "abandoned"}
VERIFIED = ["not-run", "syntax-checked", "agent-tested", "human-tested"]
STORY = {"none", "anecdote", "case study", "chapter-worthy"}
LEVELS = {"low", "medium", "high"}
FIELD = re.compile(r"^>\s*-\s*\*\*(.+?):\*\*\s*(.*)$")


# ---------------------------------------------------------------- parsing
def known_tags():
    txt = (ROOT / "CONVENTIONS.md").read_text()
    sec = txt.split("## Tags", 1)[-1].split("\n## ", 1)[0]
    return set(re.findall(r"^\|\s*`([^`]+)`", sec, re.M))


def parse_fields(lines):
    out = {}
    for ln in lines:
        m = FIELD.match(ln)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def parse_prompts_md(path):
    """Return a list of project dicts found in one prompts.md (groups have many)."""
    text = path.read_text()
    parts = re.split(r"^(?=# Project:)", text, flags=re.M)
    projects = []
    for part in parts:
        m = re.match(r"# Project:\s*(.+)", part)
        if not m:
            continue
        body = part.splitlines()
        head = []
        for ln in body[1:]:
            if re.match(r"#{1,2}\s*(Prompt|Output)", ln):
                break
            head.append(ln)
        prompts = []
        for blk in re.split(r"^(?=# Prompt)", part, flags=re.M)[1:]:
            ctx = []
            for ln in blk.splitlines()[1:]:
                if ln.startswith(">") or not ln.strip():
                    ctx.append(ln)
                else:
                    break
            prompts.append(parse_fields(ctx))
        projects.append({
            "name": m.group(1).strip(),
            "path": str(path.relative_to(ROOT)),
            "folder": path.parent,
            "fields": parse_fields(head),
            "prompts": prompts,
        })
    return projects


def load_all():
    found = []
    for p in sorted(PROJECTS.rglob("prompts.md")):
        found += parse_prompts_md(p)
    return found


def split_csv(v):
    return [x.strip() for x in v.split(",") if x.strip()]


def best_verified(proj):
    vs = [p.get("Verified", "") for p in proj["prompts"]]
    idx = [VERIFIED.index(v) for v in vs if v in VERIFIED]
    return VERIFIED[max(idx)] if idx else "TBD"


def to_record(proj):
    f = proj["fields"]
    files = split_csv(f.get("Files", ""))
    rel = proj["folder"].relative_to(ROOT)
    tools = {p.get("Tool", "").split(" · 20")[0] for p in proj["prompts"] if p.get("Tool")}
    tools.add(f.get("Defaults", ""))
    reuse = f.get("Reusability", "")
    ra = re.search(r"artifact\s+(\w+)", reuse)
    rp = re.search(r"prompt pattern\s+(\w+)", reuse)
    return {
        "name": proj["name"], "folder": str(rel), "source": proj["path"],
        "files": files,
        "open": next((str(rel / x) for x in files if x.endswith(".html")), None),
        "dates": f.get("Dates", "TBD"), "defaults": f.get("Defaults", "TBD"),
        "tools": sorted(t for t in tools if t and t != "TBD"),
        "status": f.get("Status", "TBD"), "use": f.get("Use", "TBD"),
        "artifact_reuse": ra.group(1) if ra else "TBD",
        "prompt_reuse": rp.group(1) if rp else "TBD",
        "tags": split_csv(f.get("Tags", "")),
        "takeaway": f.get("Takeaway", "TBD"),
        "story_value": f.get("Story value", "TBD"),
        "surprises": f.get("Surprises", "TBD"),
        "prompt_count": len(proj["prompts"]),
        "verified": best_verified(proj),
    }


# ----------------------------------------------------------------- check
def cmd_check(a):
    tags, errs, warns = known_tags(), [], []
    projs = load_all()
    if not projs:
        print("no projects found"); return 0
    for pr in projs:
        n, f, where = pr["name"], pr["fields"], pr["path"]
        e = lambda m: errs.append(f"{where} [{n}]: {m}")
        w = lambda m: warns.append(f"{where} [{n}]: {m}")
        for k in REQUIRED:
            if k not in f: e(f"missing field '{k}' (write TBD, don't omit)")
        if f.get("Status") not in STATUS | {"TBD", None}: e(f"bad Status {f['Status']!r}")
        if f.get("Story value") not in STORY | {"TBD", None}: e(f"bad Story value {f['Story value']!r}")
        if "Reusability" in f and f["Reusability"] != "TBD":
            for part in ("artifact", "prompt pattern"):
                m = re.search(part + r"\s+(\w+)", f["Reusability"])
                if not m or m.group(1) not in LEVELS | {"TBD"}: e(f"Reusability needs '{part} low|medium|high'")
        for t in split_csv(f.get("Tags", "")):
            if t not in tags and t != "TBD": e(f"unknown tag '{t}' (add it to CONVENTIONS.md first)")
        for x in split_csv(f.get("Files", "")):
            if x != "TBD" and not (pr["folder"] / x).exists():
                (e if f.get("Status") == "keeper" else w)(f"listed file '{x}' not found")
        if not pr["prompts"]: e("no '# Prompt' sections")
        for i, p in enumerate(pr["prompts"], 1):
            if p.get("Verified") not in VERIFIED: e(f"prompt {i}: Verified must be one of {VERIFIED}")
            if "Tool" not in p and f.get("Defaults", "TBD") == "TBD": e(f"prompt {i}: no Tool and no Defaults")
            if "Human edits" not in p: w(f"prompt {i}: no 'Human edits' line")
        if not re.fullmatch(r"[a-z0-9]+(_[a-z0-9]+)*", pr["folder"].name):
            w("folder name is not snake_case")
        # honesty rules: claims need evidence
        if f.get("Status") == "keeper" and f.get("Use", "none yet").lower().startswith(("none", "tbd")):
            w("keeper with no recorded real Use")
        if f.get("Status") == "keeper" and best_verified(pr) in ("not-run", "TBD"):
            e("keeper but nothing above 'not-run' -- verify it or demote it")
        tbd = sum(1 for k in REQUIRED if f.get(k) == "TBD")
        if tbd > 4: w(f"{tbd} fields still TBD")
    for m in warns: print("warn ", m)
    for m in errs: print("error", m)
    print(f"{len(projs)} projects, {len(errs)} errors, {len(warns)} warnings")
    return 1 if errs or (a.strict and warns) else 0



# ---------------------------------------------------------------- canvas
# Emits frames in the shape used by quantlink-inc/canvas (lib/canvas/pages.ts):
#   Frame = {id,x,y,w,h,title,kind,spec:{root,elements:{id:{type,props,children}}}}
# using only components its registry defines: Stack, Heading, Text, Metric, Sheet.
def _el(t, props, children=None):
    return {"type": t, "props": props, "children": children or []}


def canvas_frames(recs):
    frames = []
    kc = sum(r["status"] == "keeper" for r in recs)
    frames.append({"id": "ledger-summary", "x": 0, "y": 0, "w": 480, "h": 320, "title": "Summary", "kind": "page",
        "spec": {"root": "root", "elements": {
            "root": _el("Stack", {"direction": "column", "gap": "sm"}, ["h", "m1", "m2", "m3"]),
            "h": _el("Heading", {"text": "Project Ledger", "level": "h3"}),
            "m1": _el("Metric", {"label": "Projects", "value": str(len(recs)), "trend": None}),
            "m2": _el("Metric", {"label": "Keepers", "value": str(kc), "trend": None}),
            "m3": _el("Metric", {"label": "Prompts recorded", "value": str(sum(r["prompt_count"] for r in recs)), "trend": None}),
        }}})
    cols = ["Project", "Status", "Verified", "Use"]
    frames.append({"id": "ledger-catalog", "x": 520, "y": 0, "w": 760, "h": 320, "title": "Catalog", "kind": "sheet",
        "spec": {"root": "root", "elements": {
            "root": _el("Stack", {"direction": "column", "gap": "sm"}, ["h", "t"]),
            "h": _el("Heading", {"text": "Catalog", "level": "h3"}),
            "t": _el("Sheet", {"columns": cols, "rows": [[r["name"], r["status"], r["verified"], r["use"]] for r in recs]}),
        }}})
    for i, r in enumerate(recs):
        fid = "ledger-" + re.sub(r"[^a-z0-9]+", "-", r["folder"].lower()).strip("-")
        frames.append({"id": fid, "x": (i % 3) * 480, "y": 360 + (i // 3) * 340, "w": 440, "h": 300,
            "title": r["name"], "kind": "page",
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


VIEWER = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Project Ledger Canvas</title>
<style>
:root{--bg:#FFFFFF;--fg:#000000;--mut:#525252;--card:#FAFAFA;--line:#D4D4D4;--accent:#206343}
@media(prefers-color-scheme:dark){:root{--bg:#0E0E0E;--fg:#FFFFFF;--mut:#A3A3A3;--card:#0C0C0C;--line:#404040;--accent:#7BA892}}
html,body{margin:0;height:100%;overflow:hidden;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}
#bar{position:fixed;top:0;left:0;right:0;padding:8px 16px;display:flex;gap:12px;align-items:center;z-index:2;background:var(--bg);border-bottom:1px solid var(--line)}
#bar a{color:var(--accent)}#stage{position:absolute;inset:41px 0 0 0;cursor:grab;touch-action:none}
#world{position:absolute;transform-origin:0 0}
.frame{position:absolute;box-sizing:border-box;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.frame>.t{padding:6px 12px;border-bottom:1px solid var(--line);color:var(--mut);font-size:12px}
.frame>.b{padding:12px;display:grid;gap:6px;align-content:start}
.metric{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:6px}.metric span:first-child{color:var(--mut);font-size:12px}
table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;color:var(--mut)}td,th{padding:4px;border-bottom:1px solid var(--line)}
.muted{color:var(--mut)}.caption{color:var(--mut);font-size:12px}h3{margin:0}
</style><div id="bar"><b>Project Ledger</b><a href="index.html">Back to index</a><span class="muted" id="n"></span><span class="muted">drag to pan, scroll to zoom</span></div>
<div id="stage"><div id="world"></div></div>
<script id="d" type="application/json">__FRAMES__</script>
<script>
const F=JSON.parse(document.getElementById('d').textContent),w=document.getElementById('world'),st=document.getElementById('stage');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function node(sp,id){const e=sp.elements[id],p=e.props,k=()=>e.children.map(c=>node(sp,c)).join('');
 switch(e.type){case'Stack':return'<div style="display:grid;gap:8px">'+k()+'</div>';
 case'Heading':return'<h3>'+esc(p.text)+'</h3>';case'Text':return'<div class="'+esc(p.variant||'')+'">'+esc(p.text)+'</div>';
 case'Metric':return'<div class="metric"><span>'+esc(p.label)+'</span><b>'+esc(p.value)+'</b></div>';
 case'Sheet':return'<table><thead><tr>'+p.columns.map(c=>'<th>'+esc(c)+'</th>').join('')+'</tr></thead><tbody>'+p.rows.map(r=>'<tr>'+r.map(c=>'<td>'+esc(c)+'</td>').join('')+'</tr>').join('')+'</tbody></table>';}
 return''}
w.innerHTML=F.map(f=>`<div class="frame" data-id="${esc(f.id)}" style="left:${f.x}px;top:${f.y}px;width:${f.w}px;height:${f.h}px"><div class="t">${esc(f.title)} · ${esc(f.kind)}</div><div class="b">${node(f.spec,f.spec.root)}</div></div>`).join('');
document.getElementById('n').textContent=F.length+' frames';
let x=24,y=24,z=.8,drag=null;const ap=()=>w.style.transform=`translate(${x}px,${y}px) scale(${z})`;ap();
st.addEventListener('pointerdown',e=>{drag=[e.clientX-x,e.clientY-y];st.setPointerCapture(e.pointerId)});
st.addEventListener('pointermove',e=>{if(drag){x=e.clientX-drag[0];y=e.clientY-drag[1];ap()}});
st.addEventListener('pointerup',()=>drag=null);
st.addEventListener('wheel',e=>{e.preventDefault();const k=e.deltaY<0?1.1:.9,r=st.getBoundingClientRect(),px=e.clientX-r.left,py=e.clientY-r.top;
 x=px-(px-x)*k;y=py-(py-y)*k;z*=k;ap()},{passive:false});
</script></html>"""

# ----------------------------------------------------------------- build
PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Ledger</title>
<style>
:root{--bg:#FFFFFF;--fg:#000000;--sec:#262626;--mut:#525252;--card:#FAFAFA;--line:#D4D4D4;--accent:#206343}
@media(prefers-color-scheme:dark){:root{--bg:#0E0E0E;--fg:#FFFFFF;--sec:#D4D4D4;--mut:#A3A3A3;--card:#0C0C0C;--line:#404040;--accent:#7BA892}}
body{margin:0 auto;max-width:980px;padding:24px 16px;font:16px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
h1{margin:0}.sub{color:var(--mut);margin:.2em 0 1.2em}
.bar{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px}
input,select{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.card h3{margin:0 0 4px}.card a{color:var(--accent)}
.tag,.pill{display:inline-block;font-size:12px;border:1px solid var(--line);border-radius:99px;padding:1px 8px;margin:2px 4px 2px 0;color:var(--mut)}
.pill.keeper{color:var(--accent);border-color:var(--accent)}
.mut{color:var(--mut);font-size:14px}
</style>
<h1>Project Ledger</h1>
<p class="sub" id="sub"></p>
<p class="mut"><a href="canvas.html" style="color:var(--accent)">Open as canvas</a></p>
<div class="bar"><input id="q" placeholder="search…" type="search">
<select id="st"><option value="">any status</option><option>keeper</option><option>prototype</option><option>abandoned</option></select>
<select id="tg"><option value="">any tag</option></select>
<select id="vf"><option value="">any verification</option><option>human-tested</option><option>agent-tested</option><option>syntax-checked</option><option>not-run</option></select></div>
<div class="grid" id="g"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const $=id=>document.getElementById(id), esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
[...new Set(D.flatMap(p=>p.tags))].sort().forEach(t=>$('tg').add(new Option(t)));
$('sub').textContent=D.length+' projects · '+D.filter(p=>p.status==='keeper').length+' keepers · built __DATE__';
function draw(){const q=$('q').value.toLowerCase(),s=$('st').value,t=$('tg').value,v=$('vf').value;
 const rank={keeper:0,prototype:1,abandoned:2};
 $('g').innerHTML=D.filter(p=>(!s||p.status===s)&&(!t||p.tags.includes(t))&&(!v||p.verified===v)&&(!q||JSON.stringify(p).toLowerCase().includes(q)))
 .sort((a,b)=>(rank[a.status]??3)-(rank[b.status]??3)||a.name.localeCompare(b.name))
 .map(p=>`<div class="card"><h3>${p.open?`<a href="${esc(p.open)}">${esc(p.name)}</a>`:esc(p.name)}</h3>
 <span class="pill ${esc(p.status)}">${esc(p.status)}</span><span class="pill">${esc(p.verified)}</span>
 <p>${esc(p.takeaway)}</p><p class="mut">Use: ${esc(p.use)}<br>${esc(p.defaults)} · ${p.prompt_count} prompt(s) · ${esc(p.dates)}</p>
 <p class="mut"><a href="${esc(p.source)}">prompts &amp; outputs</a></p>${p.tags.map(x=>`<span class="tag">${esc(x)}</span>`).join('')}</div>`).join('')||'<p class="mut">nothing matches</p>'}
['q','st','tg','vf'].forEach(i=>$(i).addEventListener('input',draw));draw();
</script></html>"""


def cmd_build(a):
    recs = [to_record(p) for p in load_all()]
    data = json.dumps(recs).replace("</", "<\\/")
    (ROOT / "index.html").write_text(
        PAGE.replace("__DATA__", data).replace("__DATE__", dt.date.today().isoformat()))
    frames = canvas_frames(recs)
    (ROOT / "canvas-frames.json").write_text(json.dumps(frames, indent=2) + "\n")
    (ROOT / "canvas.html").write_text(VIEWER.replace("__FRAMES__", json.dumps(frames).replace("</", "<\\/")))
    print(f"wrote index.html, canvas-frames.json, canvas.html ({len(recs)} projects)")
    return 0


# ----------------------------------------------------------------- stats
def cmd_stats(a):
    recs = [to_record(p) for p in load_all()]
    if not recs: print("no projects"); return 0
    c = lambda k: Counter(r[k] for r in recs).most_common()
    print(f"{len(recs)} projects, {sum(r['prompt_count'] for r in recs)} prompts")
    for label, key in [("status", "status"), ("verified", "verified"),
                       ("artifact reuse", "artifact_reuse"), ("prompt reuse", "prompt_reuse")]:
        print(f"{label:15}", ", ".join(f"{k}={v}" for k, v in c(key)))
    print("tools          ", ", ".join(f"{k}={v}" for k, v in Counter(t for r in recs for t in r["tools"]).most_common()))
    print("tags           ", ", ".join(f"{k}={v}" for k, v in Counter(t for r in recs for t in r["tags"]).most_common()))
    used = [r for r in recs if not r["use"].lower().startswith(("none", "tbd"))]
    print(f"actually used  {len(used)}/{len(recs)}")
    mul = [r for r in recs if r["prompt_count"] > 1]
    print(f"needed >1 prompt: {len(mul)}/{len(recs)}")
    return 0


# ------------------------------------------------------------------- new
def cmd_new(a):
    name = re.sub(r"[^a-z0-9]+", "_", a.name.lower()).strip("_")
    d = PROJECTS / (a.group or "") / name
    if d.exists(): sys.exit(f"{d} exists")
    d.mkdir(parents=True)
    tpl = (ROOT / "templates" / "prompts.md").read_text()
    today = dt.date.today().isoformat()
    title = a.name.replace("_", " ").title() if "_" in a.name or a.name.islower() else a.name
    (d / "prompts.md").write_text(tpl.replace("{{TITLE}}", title).replace("{{TOOL}}", a.tool)
                                  .replace("{{DATE}}", today).replace("{{FILE}}", f"{name}.html"))
    print(f"created {d.relative_to(ROOT)}/prompts.md -- fill in the prompt, drop {name}.html next to it")
    return 0


# --------------------------------------------------------------- capture
def _text(content):
    if isinstance(content, str): return content
    return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def read_turns(jsonl):
    """Yield dicts {prompt, output, model, start, end} per human prompt."""
    turns, cur = [], None
    for ln in Path(jsonl).read_text().splitlines():
        try: ev = json.loads(ln)
        except ValueError: continue
        msg, ts = ev.get("message") or {}, ev.get("timestamp")
        if ev.get("type") == "user" and not ev.get("isMeta") and not ev.get("isSidechain"):
            c = msg.get("content")
            if isinstance(c, list) and any(b.get("type") == "tool_result" for b in c if isinstance(b, dict)):
                if cur: cur["end"] = ts
                continue
            t = _text(c).strip()
            if not t or t.startswith(("<command-", "<local-command", "<system-reminder")): continue
            cur = {"prompt": t, "output": "", "model": "", "start": ts, "end": ts}
            turns.append(cur)
        elif ev.get("type") == "assistant" and cur and not ev.get("isSidechain"):
            t = _text(msg.get("content")).strip()
            if t: cur["output"] = t          # last text block wins = the final message
            cur["model"] = msg.get("model") or cur["model"]
            cur["end"] = ts
    return turns


def _secs(a, b):
    try:
        p = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return max(0, round((p(b) - p(a)).total_seconds()))
    except Exception:
        return "TBD"


def cmd_capture(a):
    target = next(PROJECTS.rglob(f"{a.project}/prompts.md"), None)
    if not target: sys.exit(f"no project folder named {a.project}; run `new` first")
    existing = len(re.findall(r"^# Prompt", target.read_text(), re.M))
    turns = read_turns(a.session)
    if a.last: turns = turns[-a.last:]
    out = []
    for i, t in enumerate(turns, existing + 1):
        day = (t["start"] or "")[:10] or "TBD"
        out.append(f"\n# Prompt {i} (TBD: what this prompt is for):\n\n"
                   f"> - **Tool:** Claude Code · {t['model'] or 'TBD'} · {day}\n"
                   f"> - **Session:** {'fresh' if i == 1 else 'continued'} · attached: TBD\n"
                   f"> - **Time:** {_secs(t['start'], t['end'])}s\n"
                   f"> - **Verified:** not-run\n> - **Human edits:** TBD\n\n"
                   f"{t['prompt']}\n\n## Output {i}:\n\n{t['output'] or 'TBD'}\n")
    with target.open("a") as fh: fh.write("".join(out))
    print(f"appended {len(turns)} prompt(s) to {target.relative_to(ROOT)}. "
          "Verified defaults to not-run: raise it only if it is true.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("name"); n.add_argument("--tool", default="Claude Code · TBD"); n.add_argument("--group")
    c = sub.add_parser("check"); c.add_argument("--strict", action="store_true")
    sub.add_parser("build"); sub.add_parser("stats")
    k = sub.add_parser("capture"); k.add_argument("session"); k.add_argument("project"); k.add_argument("--last", type=int)
    a = ap.parse_args()
    sys.exit({"new": cmd_new, "check": cmd_check, "build": cmd_build, "stats": cmd_stats,
              "capture": cmd_capture}[a.cmd](a))


if __name__ == "__main__":
    main()
