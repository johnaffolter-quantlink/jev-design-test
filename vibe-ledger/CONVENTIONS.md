# Conventions

How projects in this repo are organized and documented. Each project is something built with an AI assistant. The goal is a record that others (and my future self) can learn from and write about: what was asked, what came back, how well it was checked, and whether it was worth it.

## Folders

- One folder per project, with its own `prompts.md`.
- Group projects in a shared folder (`games/`, `productivity/`, `teaching/`, etc.) only when three or more share a theme. A group has one `prompts.md` with one section per project.
- Folder names are `snake_case`. Use the project's own file name inside it.

## `prompts.md`

Every project's `prompts.md` has three layers, top to bottom:

1. **Project header**, written once and revised as you learn more.
2. **Prompt sections**, one per prompt, each with a context block.
3. **Output**, the assistant's final message.

```markdown
# Project: Class Timer

> - **Files:** timer.html, timers.html
> - **Dates:** 2026-10-20 → 2026-10-27
> - **Defaults:** Claude Code · Sonnet 5.5
> - **Status:** keeper
> - **Use:** used in class 2026-10-28; would use again
> - **Reusability:** artifact high · prompt pattern medium
> - **Tags:** classroom-tool, audio, localStorage
> - **Takeaway:** easy to throw together; required minimal iterations to "perfect"
> - **Story value:** I've historically used Google's timer feature + physical timers for brewing tea. This will save me time and be easier to access at all times.
> - **Surprises:** I was surprised with how well Claude was able to produce interesting visuals for the sand + tea options.

# Prompt 1 (what this prompt is for):

> - **Tool:** Claude Code · Sonnet 5.5 · 2026-10-20
> - **Session:** fresh · attached: none
> - **Time:** 54s
> - **Verified:** agent-tested
> - **Human edits:** none

The prompt text, exactly as typed.

## Output 1:

The assistant's final message.
```

### Project header fields

| Field | Values |
| --- | --- |
| Files | The deliverable files in this folder |
| Dates | First and last prompt dates (git history is a fine source) |
| Defaults | Tool and model used unless a prompt says otherwise |
| Status | `prototype` / `keeper` / `abandoned` |
| Use | Where it was actually used, or `none yet`. Real use is the strongest evidence |
| Reusability | `low` / `medium` / `high`, rated separately for the **artifact** (is the thing worth reusing?) and the **prompt pattern** (is the technique worth copying?) |
| Tags | From the list below |
| Takeaway | One sentence. Write it while it's fresh |
| Story value | `none` / `anecdote` / `case study` / `chapter-worthy` |
| Surprises | Failures and pleasant surprises. These make the best writing |

Write `TBD` rather than guessing. Don't leave a field out.

### Prompt context block fields

Only **Tool/model/date**, **Verified** and **Human edits** are required. For students: Tool/model/date and Verified are enough.

| Field | Meaning |
| --- | --- |
| Tool | Tool, model and date, for example `Claude Code · Sonnet 5.5 · 2026-10-28`. Omit repeats of the project Defaults |
| Session | `fresh` or `continued`, plus any files attached with `@` |
| Time | How long the assistant worked, as a number. Optional |
| Verified | One value from the list below |
| Human edits | Anything changed by hand afterward (pasting a style block, fixing a path), or `none` |

### Verified values

| Value | Meaning |
| --- | --- |
| `not-run` | Written but never run |
| `syntax-checked` | Parsed or linted, or logic run headless, but the real thing was never seen working |
| `agent-tested` | The assistant ran it (browser pane, scripted play-through) |
| `human-tested` | I used it myself and it worked |

Use the highest level that is true. If a prompt moves up a level later, edit the value and add a note in Human edits.

### Output

- Paste the assistant's **final message** verbatim, since it is the part that says what was built and how well it was checked.
- Mid-task progress lines ("Now I'll check the layout…") may be dropped, but never drop the final summary.
- Pasted CLI footers ("Crunched for 54s") and `git` commands don't go in `prompts.md`. Put the number in `Time`. Git history already has the rest.
- Boilerplate offers ("If you want to keep this work, I can move this session…") can be cut.

## Scope: what belongs here (and what doesn't)

**Working definition:** one-off apps that don't merit their own repository. A good fit is single-purpose, small enough to read in one sitting (aim for one main file), has no secrets and no server, and has one user (usually you).

**Graduate it to its own repo** when any of these become true: it needs a build step or dependencies you must keep updated; it holds a secret or talks to a paid API; someone other than you depends on it; you've edited it in more than three separate sessions; it outgrew ~1,000 lines or one file plus assets. Leave a `Graduated: <url>` line in the header and set Status to `abandoned` here, so the prompt history stays but the ledger doesn't claim ownership.

**Retire it** when a prototype sits untouched for 60 days (`vibe.py stale`). Promote, use it, or mark it `abandoned`. Abandoned projects stay, because their Surprises are the useful part.

## Versioning

Two layers, neither needing extra tools:

1. **Prompts are the changelog.** Each `# Prompt N` section is one iteration. To see "v2," read Prompt 2 and its Output.
2. **Git is the diff.** Commit after each prompt with the message `<project>: prompt N - <what changed>`. Tag a meaningful milestone `<project>/v2` so `git diff <project>/v1 <project>/v2 -- projects/<project>` works. Never rename the deliverable per version (`timer_v2.html`); that's what git is for.

## Optional header fields

These are ignored by the checker if absent: `Graduated:` (URL), `Depends on:` (CDN libraries or APIs the file loads at run time, since those can rot), `Privacy:` (anything personal in the prompts or data).

## Tooling

Run `python3 vibe.py` (stdlib only, Python 3.8+) from this folder:

| Command | Does |
| --- | --- |
| `new <name>` | Scaffold a folder and `prompts.md` with every field present as `TBD` |
| `capture <session.jsonl> <project>` | Append prompt and final-output sections from a Claude Code transcript, with timing and model filled in and Verified set to `not-run` |
| `check` | Lint: required fields, allowed values, known tags, listed files exist, and "keeper requires verification" |
| `build` | Regenerate `catalog.json` and `index.html` from the markdown |
| `stats` / `stale` | How much of this was actually worth it |

`index.html` and `catalog.json` are generated. Don't edit them by hand.

## Tags

Use these, and add a new one only when none fits, then add it here.

| Tag | For |
| --- | --- |
| `single-file-html` | Self-contained `.html`, no build or dependencies (most things here) |
| `classroom-tool` | Built to be used while teaching |
| `teaching-example` | Built to be shown to students as an example |
| `game` | Playable game |
| `data-viz` | Charts, dashboards, explainers |
| `presentation` | Slides or presenting aids |
| `productivity` | Planners, matrices, lists |
| `print-pdf` | Print or PDF output matters |
| `audio` | Generated sound |
| `drag-drop` | Drag-and-drop interaction |
| `canvas` | Canvas drawing or image pixels |
| `physics` | Simulation or collision logic |
| `localStorage` | Saves state in the browser |
| `export-import` | JSON, PNG or CSV in or out |
| `theming` | Light, dark, or custom themes |
| `source-material` | Built from an attached document or pasted code |
| `brainstorm` | Ideas or design discussion rather than a build |
| `site` | Part of the personal site |

## Index

`ideas.md` is the backlog. `index.html` is generated by `vibe.py build` and lists every project, keepers first, so promoting a project to `keeper` in its `prompts.md` is the only step.
