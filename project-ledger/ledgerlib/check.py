"""Validation. validate() is pure: pass in the known tags and a file-exists predicate."""
from __future__ import annotations
import re
from collections import namedtuple
from .parse import FIELD  # noqa: F401  (re-exported for callers that lint raw lines)
from .schema import HEADER_FIELDS, LEVELS, STATUS, STORY, TBD, VERIFIED

Issue = namedtuple("Issue", "severity code message")


def split_csv(v: str) -> list:
    return [x.strip() for x in v.split(",") if x.strip()]


def best_verified(project) -> str:
    idx = [VERIFIED.index(p.fields["Verified"]) for p in project.prompts
           if p.fields.get("Verified") in VERIFIED]
    return VERIFIED[max(idx)] if idx else TBD


def reuse_levels(text: str) -> tuple:
    a = re.search(r"artifact\s+(\w+)", text)
    r = re.search(r"prompt pattern\s+(\w+)", text)
    return (a.group(1) if a else TBD, r.group(1) if r else TBD)


def validate(project, tags: set, file_exists=lambda name: True) -> list:
    f, issues = project.fields, []
    err = lambda c, m: issues.append(Issue("error", c, m))
    warn = lambda c, m: issues.append(Issue("warning", c, m))

    for k in HEADER_FIELDS:
        if k not in f:
            err("E001", f"missing field '{k}' (write TBD, don't omit)")
    if f.get("Status", TBD) not in (*STATUS, TBD):
        err("E002", f"bad Status {f['Status']!r}")
    if f.get("Story value", TBD) not in (*STORY, TBD):
        err("E003", f"bad Story value {f['Story value']!r}")
    if f.get("Reusability", TBD) != TBD:
        for label, lvl in zip(("artifact", "prompt pattern"), reuse_levels(f["Reusability"])):
            if lvl not in (*LEVELS, TBD) or (lvl == TBD and label not in f["Reusability"]):
                err("E004", f"Reusability needs '{label} low|medium|high'")
    for t in split_csv(f.get("Tags", "")):
        if t != TBD and t not in tags:
            err("E005", f"unknown tag '{t}' (add it to CONVENTIONS.md first)")
    keeper = f.get("Status") == "keeper"
    for name in split_csv(f.get("Files", "")):
        if name != TBD and not file_exists(name):
            (err if keeper else warn)("E010" if keeper else "W005", f"listed file '{name}' not found")
    if not project.prompts:
        err("E006", "no '# Prompt' sections")
    for i, p in enumerate(project.prompts, 1):
        if p.fields.get("Verified") not in VERIFIED:
            err("E007", f"prompt {i}: Verified must be one of {list(VERIFIED)}")
        if "Tool" not in p.fields and f.get("Defaults", TBD) == TBD:
            err("E008", f"prompt {i}: no Tool and no Defaults")
        if "Human edits" not in p.fields:
            warn("W001", f"prompt {i}: no 'Human edits' line")
    leaf = project.folder.rsplit("/", 1)[-1] if project.folder else ""
    if leaf and not re.fullmatch(r"[a-z0-9]+(_[a-z0-9]+)*", leaf):
        warn("W002", "folder name is not snake_case")
    if keeper and f.get("Use", "none yet").lower().startswith(("none", "tbd")):
        warn("W003", "keeper with no recorded real Use")
    if keeper and best_verified(project) in (VERIFIED[0], TBD):
        err("E009", "keeper but nothing above 'not-run': verify it or demote it")
    if sum(1 for k in HEADER_FIELDS if f.get(k) == TBD) > 4:
        warn("W004", "more than 4 header fields still TBD")
    return issues
