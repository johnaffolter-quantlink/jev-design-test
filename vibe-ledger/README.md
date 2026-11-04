# Vibe Ledger

A framework for tracking one-off vibe-coded apps. Week 8 homework, Option 2. It extends Paul Kaefer's `prompts.md` convention from `paulkaefer/vibe-coding` and stays compatible with it: his files parse unchanged.

```
vibe-ledger/
  CONVENTIONS.md     the rules (Paul's, plus scope, graduation, versioning)
  vibe.py            stdlib-only CLI: new / capture / check / build / stats / stale
  templates/         prompts.md scaffold
  projects/<name>/   deliverable + prompts.md   (groups: projects/<group>/<name>/)
  catalog.json       GENERATED from the markdown
  index.html         GENERATED searchable landing page
```

Try it: `python3 vibe.py check && python3 vibe.py build && python3 vibe.py stats`.

## What Paul cares about, and where it lives

| Priority | Answer |
| --- | --- |
| Versioning | Each prompt section is one iteration. Git commits per prompt (`<project>: prompt N - ...`) and `<project>/vN` tags give real diffs. No `_v2` filenames. |
| Prompts and outputs | `prompts.md` beside the app. `capture` pulls them from a Claude Code transcript instead of relying on copy and paste. |
| Tool and model | Per-project `Defaults`, per-prompt `Tool` only when it differs. `capture` fills the model from the transcript. |
| How useful is it | `Status`, `Use`, split `Reusability` (artifact vs prompt pattern), and `Verified`. `check` enforces that a `keeper` has been verified. |
| Parent `index.html` | Generated. Promoting a project to `keeper` in its own file is the only step; nobody edits a `PROJECTS` array. |

## Design decisions, and why

**Markdown stays the source of truth; JSON and HTML are generated.** The metadata has to survive being read by humans on GitHub and by someone whose tool disappears in two years. A database or a YAML sidecar would drift from the prompts it describes. The cost is a forgiving parser (`> - **Key:** value`) rather than a schema validator, and I accept that.

**Honesty is enforced, not encouraged.** The weakest point of any self-reported ledger is inflated claims. `capture` always sets `Verified: not-run`, `check` rejects a keeper that never got past `not-run`, and warns on a keeper with no real `Use`. You have to type the upgrade yourself, and an upgrade is a claim you can be asked about.

**Who is this for? Git-comfortable people first, with a floor for everyone else.** Git gives versioning and diffs for free, and the tooling assumes it. But nothing requires it: the tool reads plain folders, `index.html` is a static file you can open from disk, and the only required habit is "put the prompt next to the file". A non-git user gets a catalog, not versioning, and I think that is the right trade. Making git invisible would need a hosted product, which defeats "no repo needed".

**Tools for people who already have a pile.** `new` makes every field exist as `TBD` so the cheapest entry is ten seconds. `capture` backfills from transcripts you already have, which is how a person with 40 old apps would catch up. `stats` and `stale` answer "is this habit paying off?" and "what is rotting?". The tool deliberately has no AI call in it: summarising your own work is where an LLM would invent the Takeaway and Surprises that make the record worth reading.

**What this is for.** One-off apps that don't merit their own repository. That definition needs an exit, or the ledger becomes a junkyard, so `CONVENTIONS.md` adds graduation rules (build step, secrets, other users, more than three sessions) and a 60-day staleness rule for prototypes.

## Limits I know about

- `capture` reads the Claude Code JSONL layout as it is today. Other tools (ChatGPT, Cursor, a web chat) need manual paste or a new reader; `read_turns` is the one function to replace.
- The parser reads Paul's format loosely. A field typo like `**Stauts:**` is caught by `check` as a missing field, but a malformed bullet that doesn't match the pattern is silently ignored by `build`.
- Scale ceiling: the generated page embeds all records in one file. Fine for hundreds; at thousands you want pagination.
- Only one example project, `tip_split`, which is a fixture I wrote to exercise the tooling and not a record of real use. Its header says so.
- `capture` was tested against one real transcript and one synthetic project, not a wide range of sessions. Tool-result filtering and the final-message rule are the likeliest places to be wrong on long sessions.
