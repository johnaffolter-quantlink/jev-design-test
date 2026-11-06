"""prompts.md -> Project. Pure functions of text; no filesystem access except load_all."""
from __future__ import annotations
import re
from pathlib import Path
from .model import Project, Prompt

FIELD = re.compile(r"^>\s*-\s*\*\*(.+?):\*\*[ \t]*(.*)$")
# A line that would be read as structure if it appeared inside a prompt or output body.
STRUCTURAL = re.compile(r"^(#{1,2}\s*(Project:|Prompt|Output)|>\s*-\s*\*\*)")


def escape_body(text: str) -> str:
    """Make free text safe to embed: structural-looking lines get a leading backslash,
    which markdown renders as the literal character."""
    return "\n".join("\\" + ln if STRUCTURAL.match(ln) else ln for ln in text.split("\n"))


def parse_fields(lines) -> dict:
    out = {}
    for ln in lines:
        m = FIELD.match(ln)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def parse_text(text: str, folder: str = "", source: str = "") -> list:
    """Return every project in one prompts.md (a group file holds several)."""
    projects = []
    for part in re.split(r"^(?=# Project:)", text, flags=re.M):
        m = re.match(r"# Project:[ \t]*(.+)", part)
        if not m:
            continue
        lines = part.split("\n")[1:]
        head = []
        for ln in lines:
            if re.match(r"#{1,2}\s*(Prompt|Output)", ln):
                break
            head.append(ln)
        prompts = []
        for blk in re.split(r"^(?=# Prompt)", part, flags=re.M)[1:]:
            blines = blk.split("\n")[1:]
            i, ctx = 0, []
            while i < len(blines) and (not blines[i].strip() or FIELD.match(blines[i])):
                ctx.append(blines[i]); i += 1
            rest = "\n".join(blines[i:])
            body, _, out = re.split(r"(^## Output[^\n]*\n?)", rest, maxsplit=1, flags=re.M) \
                if re.search(r"^## Output", rest, re.M) else (rest, "", "")
            prompts.append(Prompt(parse_fields(ctx), body.strip(), out.strip()))
        projects.append(Project(m.group(1).strip(), parse_fields(head), prompts, folder, source))
    return projects


def load_all(root: Path) -> list:
    found = []
    for p in sorted((root / "projects").rglob("prompts.md")):
        found += parse_text(p.read_text(), p.parent.relative_to(root).as_posix(),
                            p.relative_to(root).as_posix())
    return found


def known_tags(conventions_text: str) -> set:
    sec = conventions_text.split("## Tags", 1)[-1].split("\n## ", 1)[0]
    return set(re.findall(r"^\|\s*`([^`]+)`", sec, re.M))
