from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Prompt:
    fields: dict = field(default_factory=dict)  # context-block fields, e.g. {"Verified": "not-run"}
    text: str = ""                              # the prompt as typed
    output: str = ""                            # the assistant's final message


@dataclass
class Project:
    name: str
    fields: dict = field(default_factory=dict)  # header fields
    prompts: list = field(default_factory=list)
    folder: str = ""                            # posix path relative to the ledger root
    source: str = ""                            # the prompts.md it came from
