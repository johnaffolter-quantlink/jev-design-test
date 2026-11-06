# Project Ledger

A framework for tracking one-off AI-assisted apps. EIS 606 Week 8 homework, Option 2. It extends Paul Kaefer's `prompts.md` convention from `paulkaefer/vibe-coding` and stays compatible with it: his files parse unchanged.

```
project-ledger/
  ledger.py                entry point (python3 ledger.py <command>)
  ledgerlib/               the code, one concern per module
    schema.py              single source of truth: fields, enums, issue codes, JSON Schema
    model.py               Project, Prompt
    parse.py               prompts.md -> Project (pure)
    render.py              Project -> prompts.md (the inverse of parse)
    check.py               validate(): stable issue codes, no I/O
    export.py              records, canvas frames, generated pages
    capture.py             Claude Code transcript -> prompt sections
    cli.py                 argument handling and file I/O only
  schema/record.schema.json  JSON Schema for catalog records (generated from schema.py)
  tests/                   property-based tests (Hypothesis)
  templates/               prompts.md scaffold, index.html, canvas.html
  CONVENTIONS.md           the rules (Paul's, plus scope, graduation, versioning)
  canvas_frames.check.mjs  canvas-side invariant check, in the Quantlink *.check style
  projects/<name>/         deliverable + prompts.md   (groups: projects/<group>/<name>/)
  index.html               GENERATED searchable landing page
  canvas-frames.json       GENERATED frames for the Quantlink canvas
  canvas.html              GENERATED pan/zoom preview of those frames
  screenshots/             UI captures (see below)
```

The ledger itself needs only the Python standard library. Tests need `pip install -r requirements-dev.txt`.

Try it: `python3 ledger.py check && python3 ledger.py build && python3 ledger.py stats && node canvas_frames.check.mjs && python3 -m pytest tests -q`.

## Standards and testing

**One schema.** `ledgerlib/schema.py` defines every field, allowed value and issue code once. The parser, validator, exporter and JSON Schema all import it, so they cannot disagree. Validation issues carry stable codes (`E001` missing field, `E009` unverified keeper, `W003` keeper with no real use, and so on) so tools match on codes, never on message text.

**Catalog records have a published JSON Schema** (`schema/record.schema.json`, draft 2020-12; `python3 ledger.py schema` prints it). A test fails if the committed file drifts from `schema.py`.

**Property-based tests** (`tests/test_properties.py`, Hypothesis) generate random projects and hostile text and assert invariants rather than examples:

| Property | Meaning |
| --- | --- |
| Render then parse preserves structure | Any prompt text, including lines like `# Prompt 9` or `> - **Verified:**`, parses back to the same fields and prompt count |
| Validation is total and coded | Every issue has a known code whose letter matches its severity; removing any header field is always reported |
| Verification is monotonic | A project's level is the maximum over its prompts; adding a prompt never lowers it |
| Records conform to the schema | `to_record` output always validates |
| Canvas frames are well formed | Unique ids, resolvable children, only registry components, no overlap, including when many projects share a folder |
| Generated pages are injection-safe | The embedded JSON always parses back and can never close its own `<script>` tag |
| Capture is robust | Arbitrary or malformed transcripts never raise; N human turns always become N parsed prompts |

**What the properties found.** Two real defects, both fixed: a prompt whose first line began with `>` (a markdown quote) was silently swallowed as metadata, and a whitespace-only output was not normalised to `TBD` until a second write. Captured prompts that contain structural lines such as `# Prompt 2` are now escaped on write, so a pasted markdown prompt can no longer split a project in two. I confirmed the tests can fail by reintroducing the unsafe-JSON embedding on purpose; they caught it.

**CI.** `.github/workflows/ledger.yml` runs the tests, the validator, the canvas check, and confirms the generated files are current.

**Not covered.** The tests run in-process on generated data; they don't exercise the CLI's file handling beyond one smoke test of `check`, and the CI workflow has not yet run on GitHub. Python 3.13 is what I ran locally; older versions are untested.

## UI

Screenshots in `screenshots/` were captured headless (Playwright) from a scratch copy that had five extra placeholder entries, so the pages show more than the single committed sample. Those placeholder entries are not in this repo.

| View | Light | Dark |
| --- | --- | --- |
| Index (all projects) | `screenshots/index-light.png` | `screenshots/index-dark.png` |
| Canvas preview | `screenshots/canvas-light.png` | `screenshots/canvas-dark.png` |
| Phone width | `screenshots/index-mobile.png` | |

## Alignment with Quantlink

Read from `quantlink-inc/canvas` and `quantlink-inc/quantlink-main` (read only; nothing in either repo was changed).

| Quantlink convention | Where it shows up here |
| --- | --- |
| Canvas `Frame` shape: `{id, x, y, w, h, title, kind, spec}` with a json-render `Spec` (`lib/canvas/pages.ts`) | `ledger.py build` writes `canvas-frames.json` in that shape: a summary frame, a catalog frame (`kind: sheet`) and one `page` frame per project |
| Registry components (`Stack`, `Heading`, `Text`, `Metric`, `Sheet`) | The export uses only those five types |
| `*.check.ts` invariant scripts that print `<name>.check ok` | `canvas_frames.check.mjs`: unique ids, valid kinds, every child resolves, no frame overlap |
| Design tokens in `packages/ui/src/tokens.css` (`surface-base`, `surface-raised`, `border-default`, `text-primary`, `text-muted`, `text-positive`) | `index.html` and `canvas.html` use the light and dark values of those tokens as CSS variables |
| Kebab-case frame ids and refs | Frame ids are `ledger-<project>` |

**Not done, and worth being clear about:** the frames have not been loaded into the real canvas app. The check validates against a component list copied by hand from `lib/canvas/registry.tsx`, so it can drift. The colour values are copied from `tokens.css`, not imported from `@quantlink/ui`. `canvas.html` is a small stand-in renderer, not the canvas's own. Importing `canvas-frames.json` into the canvas (for example through its `/api/examples` route) is the next step and needs someone who can run that app.

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

**Tools for people who already have a pile.** `new` makes every field exist as `TBD` so the cheapest entry is ten seconds. `capture` backfills from transcripts you already have, which is how a person with 40 old apps would catch up. `stats` answers "is this habit paying off?". The tool deliberately has no AI call in it: summarising your own work is where an LLM would invent the Takeaway and Surprises that make the record worth reading.

**What this is for.** One-off apps that don't merit their own repository. That definition needs an exit, or the ledger becomes a junkyard, so `CONVENTIONS.md` adds graduation rules (build step, secrets, other users, more than three sessions) and a 60-day rule for prototypes that sit untouched (checked by eye, no command).

## Limits I know about

- `capture` reads the Claude Code JSONL layout as it is today. Other tools (ChatGPT, Cursor, a web chat) need manual paste or a new reader; `read_turns` is the one function to replace.
- The parser reads Paul's format loosely. A field typo like `**Stauts:**` is caught by `check` as a missing field, but a malformed bullet that doesn't match the pattern is silently ignored by `build`.
- Scale ceiling: the generated page embeds all records in one file. Fine for hundreds; at thousands you want pagination.
- Only one example project, `tip_split`, which is a fixture I wrote to exercise the tooling and not a record of real use. Its header says so.
- `capture` was tested against one real transcript and one synthetic project, not a wide range of sessions. Tool-result filtering and the final-message rule are the likeliest places to be wrong on long sessions.
