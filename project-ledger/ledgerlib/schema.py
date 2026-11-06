"""Single source of truth for the ledger format. Everything else imports from here."""
from __future__ import annotations

TBD = "TBD"

# Header fields, in the order they are written. All are required (write TBD, never omit).
HEADER_FIELDS = ("Files", "Dates", "Defaults", "Status", "Use", "Reusability",
                 "Tags", "Takeaway", "Story value", "Surprises")
STATUS = ("prototype", "keeper", "abandoned")
STORY = ("none", "anecdote", "case study", "chapter-worthy")
LEVELS = ("low", "medium", "high")
# Ordered weakest to strongest: a project's level is the strongest of its prompts.
VERIFIED = ("not-run", "syntax-checked", "agent-tested", "human-tested")
PROMPT_FIELDS = ("Tool", "Session", "Time", "Verified", "Human edits")

# Issue codes are stable identifiers; tests and tooling match on them, never on message text.
CODES = {
    "E001": "missing header field",
    "E002": "invalid Status",
    "E003": "invalid Story value",
    "E004": "invalid Reusability",
    "E005": "unknown tag",
    "E006": "no prompt sections",
    "E007": "invalid Verified",
    "E008": "prompt has no Tool and project has no Defaults",
    "E009": "keeper that was never verified",
    "E010": "listed file missing from a keeper",
    "W001": "prompt has no Human edits line",
    "W002": "folder name is not snake_case",
    "W003": "keeper with no recorded real Use",
    "W004": "many fields still TBD",
    "W005": "listed file missing",
}


def record_schema() -> dict:
    """JSON Schema (draft 2020-12) for one catalog record produced by export.to_record."""
    s = {"type": "string"}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "project-ledger/record.schema.json",
        "title": "Ledger record",
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "folder", "source", "files", "open", "dates", "defaults", "tools",
                     "status", "use", "artifact_reuse", "prompt_reuse", "tags", "takeaway",
                     "story_value", "surprises", "prompt_count", "verified"],
        "properties": {
            "name": s, "folder": s, "source": s, "dates": s, "defaults": s, "use": s,
            "takeaway": s, "surprises": s,
            "files": {"type": "array", "items": s},
            "open": {"type": ["string", "null"]},
            "tools": {"type": "array", "items": s},
            "tags": {"type": "array", "items": s},
            "status": {"enum": [*STATUS, TBD]},
            "story_value": {"enum": [*STORY, TBD]},
            "artifact_reuse": {"enum": [*LEVELS, TBD]},
            "prompt_reuse": {"enum": [*LEVELS, TBD]},
            "verified": {"enum": [*VERIFIED, TBD]},
            "prompt_count": {"type": "integer", "minimum": 0},
        },
    }
