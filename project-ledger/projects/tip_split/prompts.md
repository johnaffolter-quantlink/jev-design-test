# Project: Tip Split

> - **Files:** tip_split.html
> - **Dates:** 2026-11-04 → 2026-11-04
> - **Defaults:** Claude Code · Sonnet 5.5
> - **Status:** prototype
> - **Use:** none yet
> - **Reusability:** artifact low · prompt pattern low
> - **Tags:** single-file-html, productivity
> - **Takeaway:** Fixture project that shows the ledger format end to end; deliberately trivial.
> - **Story value:** none
> - **Surprises:** none. This is a sample entry written to exercise the tooling, not a real usage record.

# Prompt 1 (initial build):

> - **Tool:** Claude Code · Sonnet 5.5 · 2026-11-04
> - **Session:** fresh · attached: none
> - **Verified:** agent-tested
> - **Human edits:** none

Make a single-file HTML tip calculator: bill, tip percent, number of people, show the per-person amount and the total. Mobile friendly, no dependencies.

## Output 1:

Created `tip_split.html`. Three number inputs (bill, tip %, people) recalculate on input and show the per-person amount and total. Checked headless with Playwright: bill 60, tip 20%, 3 people gives $24.00 each ($72.00 total); changing to 4 people gives $18.00.
