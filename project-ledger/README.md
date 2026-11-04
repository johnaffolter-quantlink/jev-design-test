# Project Ledger

A framework for tracking one-off AI-assisted apps. EIS 606 Week 8 homework, Option 2. It extends Paul Kaefer's `prompts.md` convention from `paulkaefer/vibe-coding` and stays compatible with it: his files parse unchanged.

```
project-ledger/
  CONVENTIONS.md     the rules (Paul's, plus scope, graduation, versioning)
  canvas_frames.check.mjs  invariant check for the canvas export
  ledger.py            stdlib-only CLI: new / capture / check / build / stats / stale
  templates/         prompts.md scaffold
  projects/<name>/   deliverable + prompts.md   (groups: projects/<group>/<name>/)
  catalog.json       GENERATED from the markdown
  index.html         GENERATED searchable landing page
  canvas-frames.json GENERATED frames for the Quantlink canvas
  canvas.html        GENERATED pan/zoom preview of those frames
  screenshots/       UI captures (see below)
```

Try it: `python3 ledger.py check && python3 ledger.py build && python3 ledger.py stats && node canvas_frames.check.mjs`.

## UI

Screenshots in `screenshots/` were captured headless (Playwright) from a scratch copy that had five extra placeholder entries, so the pages show more than the single committed sample. Those placeholder entries are not in this repo.

| View | Light | Dark |
| --- | --- | --- |
| Index (all projects) | `screenshots/index-light.png` | `screenshots/index-dark.png` |
| Index filtered to keepers | `screenshots/index-keepers-light.png` | `screenshots/index-keepers-dark.png` |
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

**Tools for people who already have a pile.** `new` makes every field exist as `TBD` so the cheapest entry is ten seconds. `capture` backfills from transcripts you already have, which is how a person with 40 old apps would catch up. `stats` and `stale` answer "is this habit paying off?" and "what is rotting?". The tool deliberately has no AI call in it: summarising your own work is where an LLM would invent the Takeaway and Surprises that make the record worth reading.

**What this is for.** One-off apps that don't merit their own repository. That definition needs an exit, or the ledger becomes a junkyard, so `CONVENTIONS.md` adds graduation rules (build step, secrets, other users, more than three sessions) and a 60-day staleness rule for prototypes.

## Limits I know about

- `capture` reads the Claude Code JSONL layout as it is today. Other tools (ChatGPT, Cursor, a web chat) need manual paste or a new reader; `read_turns` is the one function to replace.
- The parser reads Paul's format loosely. A field typo like `**Stauts:**` is caught by `check` as a missing field, but a malformed bullet that doesn't match the pattern is silently ignored by `build`.
- Scale ceiling: the generated page embeds all records in one file. Fine for hundreds; at thousands you want pagination.
- Only one example project, `tip_split`, which is a fixture I wrote to exercise the tooling and not a record of real use. Its header says so.
- `capture` was tested against one real transcript and one synthetic project, not a wide range of sessions. Tool-result filtering and the final-message rule are the likeliest places to be wrong on long sessions.
