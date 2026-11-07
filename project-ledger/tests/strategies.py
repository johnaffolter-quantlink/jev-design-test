"""Generators for ledger data. Kept separate so every test file draws from the same definitions."""
from hypothesis import strategies as st
from ledgerlib.model import Project, Prompt
from ledgerlib.schema import HEADER_FIELDS, LEVELS, PROMPT_FIELDS, STATUS, STORY, TBD, VERIFIED

TAGS = ("single-file-html", "game", "audio", "data-viz", "productivity")

# One-line values: what a header or context field may hold. No control chars or line separators.
line = (st.text(alphabet=st.characters(blacklist_categories=("Cc", "Cs", "Zl", "Zp")), min_size=1, max_size=30)
        .map(str.strip).filter(bool))
# Free text: anything at all (except lone surrogates), including hostile structural lines.
HOSTILE = ["# Project: x", "# Prompt 9", "## Output 3:", "> - **Verified:** human-tested", "#Prompt", "> quote"]
free_text = st.one_of(
    st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=200),
    st.lists(st.one_of(st.sampled_from(HOSTILE), st.text(max_size=20)), max_size=6).map("\n".join),
)
filenames = st.from_regex(r"[a-z][a-z0-9_]{0,10}\.(html|js|json)", fullmatch=True)


@st.composite
def reusability(draw):
    return f"artifact {draw(st.sampled_from(LEVELS))} · prompt pattern {draw(st.sampled_from(LEVELS))}"


@st.composite
def headers(draw, valid=True):
    h = {
        "Files": ", ".join(draw(st.lists(filenames, min_size=1, max_size=3, unique=True))),
        "Dates": "2026-11-01 → 2026-11-02",
        "Defaults": draw(line),
        "Status": draw(st.sampled_from(STATUS)),
        "Use": draw(line),
        "Reusability": draw(reusability()),
        "Tags": ", ".join(draw(st.lists(st.sampled_from(TAGS), min_size=1, max_size=3, unique=True))),
        "Takeaway": draw(line),
        "Story value": draw(st.sampled_from(STORY)),
        "Surprises": draw(line),
    }
    return h


@st.composite
def prompts(draw, verified=None):
    f = {"Tool": draw(line), "Verified": draw(verified or st.sampled_from(VERIFIED)), "Human edits": draw(line)}
    if draw(st.booleans()):
        f["Session"] = draw(line)
    return Prompt(f, draw(free_text).strip(), draw(free_text).strip())


@st.composite
def projects(draw, folder=None):
    leaf = draw(st.from_regex(r"[a-z][a-z0-9]{0,6}(_[a-z0-9]{1,5}){0,2}", fullmatch=True))
    folder = folder or f"projects/{leaf}"
    return Project(draw(line), draw(headers()), draw(st.lists(prompts(), min_size=1, max_size=4)),
                   folder, f"{folder}/prompts.md")
