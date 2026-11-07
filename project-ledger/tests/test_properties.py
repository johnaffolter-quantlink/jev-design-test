"""Property-based tests. Each test states an invariant that must hold for ALL generated inputs."""
import json, re, subprocess, sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from ledgerlib import capture
from ledgerlib.check import best_verified, validate
from ledgerlib.export import canvas_frames, canvas_html, index_html, slug, to_record, unique_ids
from ledgerlib.model import Project, Prompt
from ledgerlib.parse import STRUCTURAL, escape_body, parse_text
from ledgerlib.render import render_project
from ledgerlib.schema import CODES, HEADER_FIELDS, TBD, VERIFIED, record_schema
from strategies import TAGS, free_text, line, projects, prompts

ROOT = Path(__file__).resolve().parent.parent
settings.register_profile("ci", max_examples=200, deadline=None,
                          suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
settings.load_profile("ci")
KNOWN = set(TAGS)


# ------------------------------------------------------------------ parse / render
@given(projects())
def test_render_then_parse_preserves_structure(p):
    """Whatever the prompt text says, the project parses back with the same shape."""
    [q] = parse_text(render_project(p), p.folder, p.source)
    assert q.name == p.name
    assert q.fields == p.fields
    assert len(q.prompts) == len(p.prompts)
    for a, b in zip(p.prompts, q.prompts):
        assert b.fields == a.fields
        assert b.text == escape_body(a.text).strip()
        assert b.output == (escape_body(a.output).strip() or TBD)


@given(st.lists(projects(), min_size=1, max_size=4))
def test_group_file_roundtrips_in_order(ps):
    """A group prompts.md (several projects in one file) keeps count, names and order."""
    text = "\n".join(render_project(p) for p in ps)
    got = parse_text(text)
    assert [g.name for g in got] == [p.name for p in ps]
    assert [len(g.prompts) for g in got] == [len(p.prompts) for p in ps]


@given(free_text)
def test_escaped_text_has_no_structural_lines(t):
    assert not any(STRUCTURAL.match(ln) for ln in escape_body(t).split("\n"))


@given(free_text)
def test_escape_is_stable_under_reparse(t):
    """Escaping what a parse returned adds nothing: render->parse->render->parse is a fixed point."""
    p = Project("P", {k: "x" for k in HEADER_FIELDS}, [Prompt({"Verified": "not-run"}, t, t)])
    once = parse_text(render_project(p))[0]
    twice = parse_text(render_project(once))[0]
    assert (once.prompts[0].text, once.prompts[0].output) == (twice.prompts[0].text, twice.prompts[0].output)


# ------------------------------------------------------------------ validation
@given(projects())
def test_generated_valid_projects_have_no_errors(p):
    errors = [i for i in validate(p, KNOWN) if i.severity == "error"]
    # The only legitimate error on a well-formed project is the keeper-verification rule.
    assert all(i.code == "E009" for i in errors)
    if p.fields["Status"] != "keeper" or best_verified(p) != VERIFIED[0]:
        assert errors == []


@given(projects(), st.sampled_from(HEADER_FIELDS))
def test_removing_any_header_field_is_reported(p, field):
    del p.fields[field]
    assert any(i.code == "E001" and field in i.message for i in validate(p, KNOWN))


@given(projects(), st.text(min_size=1, max_size=12).filter(lambda s: s.strip() not in ("prototype", "keeper", "abandoned", TBD)))
def test_invalid_status_is_reported(p, bad):
    p.fields["Status"] = bad
    assert any(i.code == "E002" for i in validate(p, KNOWN))


@given(projects(), line.filter(lambda t: t not in TAGS and t != TBD and "," not in t))
def test_unknown_tag_is_reported(p, tag):
    p.fields["Tags"] = f"{p.fields['Tags']}, {tag}"
    assert any(i.code == "E005" and tag in i.message for i in validate(p, KNOWN))


@given(projects(), st.sampled_from(VERIFIED[1:]))
def test_keeper_needs_one_verified_prompt(p, level):
    p.fields["Status"] = "keeper"
    for pr in p.prompts:
        pr.fields["Verified"] = VERIFIED[0]
    assert any(i.code == "E009" for i in validate(p, KNOWN))
    p.prompts[0].fields["Verified"] = level
    assert not any(i.code == "E009" for i in validate(p, KNOWN))


@given(projects())
def test_every_issue_has_a_known_code_matching_its_severity(p):
    p.fields.pop(HEADER_FIELDS[0], None)
    for i in validate(p, KNOWN, file_exists=lambda n: False):
        assert i.code in CODES
        assert i.severity == ("error" if i.code.startswith("E") else "warning")


@given(st.lists(prompts(), max_size=5), prompts())
def test_adding_a_prompt_never_lowers_verification(ps, extra):
    p = Project("P", {}, list(ps))
    before = best_verified(p)
    p.prompts.append(extra)
    after = best_verified(p)
    if before != TBD:
        assert VERIFIED.index(after) >= VERIFIED.index(before)


@given(st.lists(prompts(), min_size=1, max_size=5))
def test_best_verified_is_the_maximum(ps):
    levels = [VERIFIED.index(x.fields["Verified"]) for x in ps]
    assert best_verified(Project("P", {}, ps)) == VERIFIED[max(levels)]


# ------------------------------------------------------------------ export
@given(projects())
def test_record_conforms_to_published_schema(p):
    jsonschema = pytest.importorskip("jsonschema")
    rec = to_record(p)
    jsonschema.validate(rec, record_schema())
    assert rec["prompt_count"] == len(p.prompts)
    assert json.loads(json.dumps(rec)) == rec


def test_committed_schema_file_is_current():
    assert json.loads((ROOT / "schema" / "record.schema.json").read_text()) == record_schema()


@given(st.lists(projects(), max_size=9), st.booleans())
def test_canvas_frames_satisfy_invariants(ps, share_folder):
    """Mirrors canvas_frames.check.mjs: unique ids, resolvable children, valid types, no overlap."""
    if share_folder:  # group files put several projects in one folder
        for p in ps:
            p.folder = "projects/g"
    frames = canvas_frames([to_record(p) for p in ps])
    ids = [f["id"] for f in frames]
    assert len(set(ids)) == len(ids)
    for f in frames:
        els = f["spec"]["elements"]
        assert f["spec"]["root"] in els
        for el in els.values():
            assert el["type"] in {"Stack", "Heading", "Text", "Metric", "Sheet"}
            assert all(c in els for c in el["children"])
    for i, a in enumerate(frames):
        for b in frames[i + 1:]:
            assert not (a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"]
                        and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"])


@given(st.lists(st.tuples(line, line), max_size=8))
def test_unique_ids_never_collide(pairs):
    recs = [{"folder": f, "name": n} for f, n in pairs]
    ids = unique_ids(recs)
    assert len(set(ids)) == len(ids)


@given(free_text)
def test_slug_is_always_a_safe_nonempty_token(s):
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug(s))


@given(st.lists(projects(), max_size=3), st.text(max_size=40) | st.sampled_from(["</script><b>", "<!--", "a b", '"quoted"']))
def test_embedded_json_survives_hostile_text(ps, nasty):
    """Whatever the content, the page's JSON blob parses back to the records and cannot close its own tag."""
    for p in ps:
        p.name = p.name + nasty
        p.fields["Takeaway"] = nasty or "x"
    recs = [to_record(p) for p in ps]
    for html_text, blob_id in ((index_html(recs, "2026-01-01"), "data"), (canvas_html(canvas_frames(recs)), "d")):
        m = re.search(rf'<script id="{blob_id}" type="application/json">(.*?)</script>', html_text, re.S)
        assert m and "<" not in m.group(1)
        json.loads(m.group(1))
    assert json.loads(re.search(r'id="data" type="application/json">(.*?)</script>',
                                index_html(recs, "d"), re.S).group(1)) == recs


# ------------------------------------------------------------------ capture
@given(st.text(max_size=400))
def test_read_turns_never_raises_on_garbage(s):
    assert isinstance(capture.read_turns(s), list)


@given(st.lists(st.fixed_dictionaries({"type": st.sampled_from(["user", "assistant", "x"]),
                                       "message": st.one_of(st.none(), st.integers(), st.dictionaries(st.text(max_size=5), st.integers() | st.none() | st.text(max_size=5), max_size=3)),
                                       "timestamp": st.none() | st.integers() | st.text(max_size=8)}), max_size=8))
def test_read_turns_tolerates_wrong_shapes(events):
    capture.read_turns("\n".join(json.dumps(e) for e in events))


@given(st.lists(st.tuples(free_text.map(str.strip).filter(bool).filter(lambda t: not t.startswith(("<command-", "<local-command", "<system-reminder"))),
                          free_text), min_size=1, max_size=4))
def test_captured_transcript_becomes_exactly_that_many_prompts(pairs):
    """Capture then parse yields one prompt per human turn, each unverified, whatever the text contains."""
    events = []
    for prompt, answer in pairs:
        events.append({"type": "user", "timestamp": "2026-11-01T10:00:00Z", "message": {"role": "user", "content": prompt}})
        events.append({"type": "assistant", "timestamp": "2026-11-01T10:00:05Z",
                       "message": {"model": "m", "content": [{"type": "text", "text": answer or "ok"}]}})
    turns = capture.read_turns("\n".join(json.dumps(e) for e in events))
    assert len(turns) == len(pairs)
    header = "\n".join(["# Project: C", *(f"> - **{k}:** {TBD}" for k in HEADER_FIELDS)])
    [proj] = parse_text(header + "\n" + capture.render_turns(turns, 1))
    assert len(proj.prompts) == len(pairs)
    assert all(pr.fields["Verified"] == "not-run" for pr in proj.prompts)
    assert [pr.fields["Time"] for pr in proj.prompts] == ["5s"] * len(pairs)


# ------------------------------------------------------------------ repo smoke
def test_repository_ledger_is_valid_and_canvas_check_passes():
    r = subprocess.run([sys.executable, "ledger.py", "check"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
