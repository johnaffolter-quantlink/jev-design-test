"""Project -> prompts.md. The inverse of parse.parse_text for well-formed input."""
from __future__ import annotations
from .model import Project
from .parse import escape_body
from .schema import HEADER_FIELDS, PROMPT_FIELDS, TBD


def render_project(p: Project) -> str:
    out = [f"# Project: {p.name}", ""]
    for k in HEADER_FIELDS:
        out.append(f"> - **{k}:** {p.fields.get(k, TBD)}")
    for i, pr in enumerate(p.prompts, 1):
        out += ["", f"# Prompt {i} (TBD):", ""]
        out += [f"> - **{k}:** {v}" for k, v in pr.fields.items()]
        out += ["", escape_body(pr.text), "", f"## Output {i}:", "", escape_body(pr.output).strip() or TBD]
    return "\n".join(out) + "\n"
