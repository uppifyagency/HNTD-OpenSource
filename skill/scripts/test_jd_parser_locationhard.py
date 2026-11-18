"""Layer-1 deterministic eval for the JD-parser `locationHard` classification.

This is the BLOCKING CI gate of the two-layer JD-parser eval introduced by the
`pass2-geo-constraint` feature (feature-delta §"Producer Verification").

It does **NOT** invoke an LLM. It encodes the classification *rule* — the 9-rule
decision table + Hybrid rule from the contract spec (feature-delta §"Contract
Spec — locationHard" → "The DEFINITION of hard") — as a tiny pure reference
function: a trigger-phrase matcher over the EN+IT anchor table. The reference
function MUST mirror sub-rule 2a in `skill/agents/github-hr-jd-parser.md` so the
test and the LLM producer instruction stay in lockstep.

Purpose: anti-drift. If someone edits the rule table without updating the
fixture set, this test fails. It guards the SPECIFICATION, not the LLM (that is
Layer 2, `eval_jd_parser_locationhard.py`).

Run:  cd skill/scripts && .venv/bin/python -m pytest test_jd_parser_locationhard.py
"""

import json
import re
from pathlib import Path

import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "locationhard_jds.json"


# ---------------------------------------------------------------------------
# EN + IT anchor vocabulary — mirrors sub-rule 2a of github-hr-jd-parser.md.
# Each entry is a precedence-ordered rule (rule 1..8 of the contract table).
# Rule 9 (conservative default) is NOT a phrase rule — it is the fallthrough.
# ---------------------------------------------------------------------------

# Rule 1 — on-site / in-office presence required.
ONSITE_TRIGGERS = (
    "on-site",
    "on site",
    "in-office",
    "in office",
    "in sede",
    "in presenza",
    "richiesta presenza in sede",
    "presenza obbligatoria",
)

# Rule 2 — mandatory relocation.
RELOCATION_TRIGGERS = (
    "relocation required",
    "must relocate",
    "must be willing to relocate",
    "trasferimento richiesto",
    "richiesto trasferimento",
    "richiesto il trasferimento",
    "disponibilità al trasferimento",
)

# Rule 3 — explicitly no remote.
NO_REMOTE_TRIGGERS = (
    "no remote",
    "remote not available",
    "remote work is not offered",
    "no smart working",
    "non è previsto smart working",
    "non è previsto lavoro da remoto",
    "no remoto",
    "niente smart working",
)

# Rule 4 — a specific city/country stated as an obligatory requirement.
OBLIGATORY_PLACE_TRIGGERS = (
    "must be based in",
    "office (mandatory)",
    "sede di lavoro:",
    "con sede a",
)
# Rule 4 also fires on the IT pattern "sede di <città> obbligatoria" — a place
# token followed (within the same JD) by an obligatory marker. Modelled as a
# regex so the city name is not enumerated.
OBLIGATORY_PLACE_REGEX = re.compile(r"sede di .+? obbligatoria", re.IGNORECASE)

# Rule 6 — remote with a location stated only as a preference (SOFT).
PREFERENCE_TRIGGERS = (
    "preferably",
    "preference",
    "preferibilmente",
    "preferenza sede",
)

# Rule 7 — timezone-overlap-only requirement (SOFT).
TIMEZONE_TRIGGERS = (
    "overlap cet",
    "overlap working hours",
    "eu timezone",
    "sovrapposizione fuso orario",
    "sovrapposizione del fuso orario",
    "fuso orario eu",
)

# Rule 8 — fully remote, no location signal (SOFT).
FULLY_REMOTE_TRIGGERS = (
    "100% remote",
    "fully remote",
    "work from anywhere",
    "100% da remoto",
    "completamente da remoto",
)

# Hybrid rule — a mandated recurring in-office cadence ⇒ HARD (rule 5).
HYBRID_CADENCE_REGEX = re.compile(
    r"(hybrid|ibrido).{0,80}?"
    r"(\d+\s*(day|days|giorn[oi])\s*(/|per|a|al)?\s*"
    r"(week|month|settimana|mese))",
    re.IGNORECASE | re.DOTALL,
)
# Hybrid exception — the in-office portion is EXPLICITLY optional ⇒ SOFT.
HYBRID_OPTIONAL_TRIGGERS = (
    "office is available if you prefer",
    "office available if you prefer",
    "if you prefer to work on-site",
    "if you prefer to work on site",
    "ufficio disponibile se preferisci",
    "presenza in ufficio facoltativa",
)


def _contains_any(text: str, triggers) -> bool:
    """True if `text` (case-insensitively) contains any phrase in `triggers`."""
    lowered = text.lower()
    return any(trigger.lower() in lowered for trigger in triggers)


def classify_location_hard(jd: str) -> bool:
    """Pure reference classifier for `locationHard`.

    Mirrors the 9-rule decision table + Hybrid rule of the contract spec and
    sub-rule 2a of `github-hr-jd-parser.md`. Rules are applied IN ORDER and the
    FIRST match wins. Rule 9 (conservative default ⇒ ``True``) is the
    fallthrough when no phrase rule matches.

    Returns ``True`` when geography is a HARD filter, ``False`` when it is a
    PREFERENCE only.
    """
    text = jd or ""

    # Hybrid exception is checked before the hybrid-cadence rule so an
    # explicitly-optional office never resolves to hard.
    if _contains_any(text, HYBRID_OPTIONAL_TRIGGERS):
        return False  # rule 5 exception (optional in-office) — SOFT

    # Rule 5 — hybrid with a mandated recurring in-office cadence ⇒ HARD.
    if HYBRID_CADENCE_REGEX.search(text):
        return True

    # Rule 1 — on-site / in-office presence required ⇒ HARD.
    if _contains_any(text, ONSITE_TRIGGERS):
        return True

    # Rule 2 — mandatory relocation ⇒ HARD.
    if _contains_any(text, RELOCATION_TRIGGERS):
        return True

    # Rule 3 — explicitly no remote ⇒ HARD.
    if _contains_any(text, NO_REMOTE_TRIGGERS):
        return True

    # Rule 4 — a specific place stated as an obligatory requirement ⇒ HARD.
    if _contains_any(text, OBLIGATORY_PLACE_TRIGGERS):
        return True
    if OBLIGATORY_PLACE_REGEX.search(text):
        return True

    # Rule 6 — remote with a location preference only ⇒ SOFT.
    if _contains_any(text, PREFERENCE_TRIGGERS):
        return False

    # Rule 7 — timezone-overlap-only ⇒ SOFT.
    if _contains_any(text, TIMEZONE_TRIGGERS):
        return False

    # Rule 8 — fully remote, no location signal ⇒ SOFT.
    if _contains_any(text, FULLY_REMOTE_TRIGGERS):
        return False

    # Rule 9 — ambiguous / no clear signal either way ⇒ conservative default.
    return True


# ---------------------------------------------------------------------------
# Hard-trigger detection — used to PROVE `it-ambiguous` resolves via rule 9
# (the conservative fallthrough) and NOT via a hard-trigger phrase match.
# ---------------------------------------------------------------------------

_HARD_TRIGGER_GROUPS = (
    ONSITE_TRIGGERS,
    RELOCATION_TRIGGERS,
    NO_REMOTE_TRIGGERS,
    OBLIGATORY_PLACE_TRIGGERS,
)


def matches_hard_trigger(jd: str) -> bool:
    """True if `jd` matches any HARD-trigger phrase or the hybrid-cadence rule.

    This is the set of rules 1-5 that produce ``True`` via an explicit phrase
    match — it deliberately EXCLUDES rule 9 (the conservative fallthrough).
    """
    if HYBRID_CADENCE_REGEX.search(jd or ""):
        return True
    if OBLIGATORY_PLACE_REGEX.search(jd or ""):
        return True
    return any(_contains_any(jd, group) for group in _HARD_TRIGGER_GROUPS)


_SOFT_TRIGGER_GROUPS = (
    PREFERENCE_TRIGGERS,
    TIMEZONE_TRIGGERS,
    FULLY_REMOTE_TRIGGERS,
    HYBRID_OPTIONAL_TRIGGERS,
)


def matches_soft_trigger(jd: str) -> bool:
    """True if `jd` matches any SOFT-trigger phrase (rules 6-8 + hybrid opt)."""
    return any(_contains_any(jd, group) for group in _SOFT_TRIGGER_GROUPS)


# ---------------------------------------------------------------------------
# Fixture loading.
# ---------------------------------------------------------------------------

def _load_fixtures():
    with FIXTURES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


FIXTURES = _load_fixtures()
HARD_PHRASES = [p for group in _HARD_TRIGGER_GROUPS for p in group]
SOFT_PHRASES = [p for group in _SOFT_TRIGGER_GROUPS for p in group]


# ---------------------------------------------------------------------------
# Test 1 — the fixture set is well-formed (the eval's input contract).
# ---------------------------------------------------------------------------

def test_fixture_set_is_well_formed():
    """The 11 representative fixtures: balanced split, complete fields."""
    assert len(FIXTURES) == 11, "expected exactly 11 representative fixtures"

    ids = [f["id"] for f in FIXTURES]
    assert len(set(ids)) == 11, "fixture ids must be unique"

    hard = [f for f in FIXTURES if f["expected"] is True]
    soft = [f for f in FIXTURES if f["expected"] is False]
    assert len(hard) == 6, "expected 6 hard (expected:true) fixtures"
    assert len(soft) == 5, "expected 5 soft (expected:false) fixtures"

    for fixture in FIXTURES:
        assert set(fixture.keys()) == {"id", "lang", "jd", "expected", "note"}
        assert fixture["lang"] in ("en", "it")
        assert isinstance(fixture["expected"], bool)
        assert fixture["jd"].strip(), f"{fixture['id']} has empty JD text"


# ---------------------------------------------------------------------------
# Test 2 — every fixture classifies to its expected value.
# This is the anti-drift core: edit the rule table without updating the
# fixtures and this parametrized test fails.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["id"] for f in FIXTURES])
def test_reference_function_classifies_fixture(fixture):
    """The reference classifier reproduces every fixture's expected value."""
    actual = classify_location_hard(fixture["jd"])
    assert actual is fixture["expected"], (
        f"fixture {fixture['id']}: expected locationHard="
        f"{fixture['expected']} ({fixture['note']}), got {actual}"
    )


# ---------------------------------------------------------------------------
# Test 3 — `it-ambiguous` resolves to true via rule 9 ONLY.
# It must NOT match any hard-trigger phrase and must NOT match any soft
# signal — its `true` answer can come only from the conservative fallthrough.
# ---------------------------------------------------------------------------

def test_it_ambiguous_resolves_via_conservative_default_only():
    """`it-ambiguous` is true via rule 9, never via a hard-trigger match."""
    fixture = next(f for f in FIXTURES if f["id"] == "it-ambiguous")
    jd = fixture["jd"]

    assert classify_location_hard(jd) is True, "must classify hard"
    assert not matches_hard_trigger(jd), (
        "it-ambiguous must NOT match a hard-trigger phrase — its `true` must "
        "come from rule 9 (conservative default), not a phrase match"
    )
    assert not matches_soft_trigger(jd), (
        "it-ambiguous must NOT match a soft signal either — otherwise rule 9 "
        "would not be exercised"
    )


# ---------------------------------------------------------------------------
# Test 4 — `en-hybrid-optional` resolves to false via the hybrid-optional
# exception ONLY, and ONLY because that exception is checked BEFORE the on-site
# rule. The fixture text ("...if you prefer to work on-site") genuinely
# contains a hard trigger ("on-site"); the SOFT verdict depends entirely on
# rule precedence. This test makes that ordering invariant explicit so a
# future reorder of `classify_location_hard` cannot silently break it.
# ---------------------------------------------------------------------------

def test_en_hybrid_optional_resolves_via_exception_despite_hard_trigger():
    """`en-hybrid-optional` is false via the exception checked before rule 1."""
    fixture = next(f for f in FIXTURES if f["id"] == "en-hybrid-optional")
    jd = fixture["jd"]

    assert classify_location_hard(jd) is False, "must classify soft"
    assert matches_hard_trigger(jd) is True, (
        "en-hybrid-optional genuinely contains a hard trigger ('on-site') — "
        "its `false` answer depends on the hybrid-optional exception being "
        "checked BEFORE the on-site rule, not on the absence of a hard trigger"
    )
    assert matches_soft_trigger(jd) is True, (
        "the hybrid-optional trigger must fire — it is the soft signal that "
        "the precedence-ordered exception relies on"
    )


# ---------------------------------------------------------------------------
# Property 1 — any JD containing a hard-trigger phrase always classifies true.
# Universal invariant over arbitrary JD strings built from anchor vocabulary.
# The 11 named fixtures are canonical @example anchors.
# ---------------------------------------------------------------------------

@st.composite
def _jd_with_hard_trigger(draw):
    """An arbitrary JD that embeds at least one HARD-trigger phrase."""
    trigger = draw(st.sampled_from(HARD_PHRASES))
    prefix = draw(st.text(alphabet=st.characters(whitelist_categories=("L", "Zs")),
                          max_size=40))
    suffix = draw(st.text(alphabet=st.characters(whitelist_categories=("L", "Zs")),
                          max_size=40))
    return f"{prefix} {trigger} {suffix}"


@given(jd=_jd_with_hard_trigger())
@settings(max_examples=120, deadline=None)
@example(jd=next(f["jd"] for f in FIXTURES if f["id"] == "it-onsite-milan"))
@example(jd=next(f["jd"] for f in FIXTURES if f["id"] == "it-relocation"))
@example(jd=next(f["jd"] for f in FIXTURES if f["id"] == "en-onsite-berlin"))
def test_property_hard_trigger_always_classifies_true(jd):
    """INVARIANT: a JD containing any hard-trigger phrase classifies true."""
    assert classify_location_hard(jd) is True


# ---------------------------------------------------------------------------
# Property 2 — a JD with ONLY a soft signal (no hard trigger, no hybrid
# cadence) always classifies false.
# ---------------------------------------------------------------------------

@st.composite
def _jd_with_soft_signal_only(draw):
    """An arbitrary JD with a SOFT signal and no HARD trigger / cadence."""
    signal = draw(st.sampled_from(SOFT_PHRASES))
    prefix = draw(st.text(alphabet=st.characters(whitelist_categories=("L", "Zs")),
                          max_size=40))
    suffix = draw(st.text(alphabet=st.characters(whitelist_categories=("L", "Zs")),
                          max_size=40))
    jd = f"{prefix} {signal} {suffix}"
    # Genuinely enforce the precondition "soft signal ONLY": discard any draw
    # that also contains a hard trigger. This happens not only via random
    # letters but structurally — some HYBRID_OPTIONAL_TRIGGERS phrases (e.g.
    # "if you prefer to work on-site") embed the substring "on-site", which is
    # itself an ONSITE_TRIGGERS hard trigger. `assume` discards such draws
    # instead of substituting an unchecked fallback that bypasses the check.
    assume(not matches_hard_trigger(jd))
    return jd


@given(jd=_jd_with_soft_signal_only())
@settings(max_examples=120, deadline=None)
@example(jd=next(f["jd"] for f in FIXTURES if f["id"] == "en-remote-pref"))
@example(jd=next(f["jd"] for f in FIXTURES if f["id"] == "en-remote-tz-only"))
@example(jd=next(f["jd"] for f in FIXTURES if f["id"] == "it-remote-tz-only"))
@example(jd=next(f["jd"] for f in FIXTURES if f["id"] == "en-fully-remote"))
@example(jd=next(f["jd"] for f in FIXTURES if f["id"] == "en-hybrid-optional"))
def test_property_soft_signal_only_classifies_false(jd):
    """INVARIANT: a JD with only a soft signal and no hard trigger is false."""
    assert classify_location_hard(jd) is False


# ---------------------------------------------------------------------------
# Property 3 — a JD with no trigger phrase at all falls through to rule 9
# (conservative default ⇒ true).
# ---------------------------------------------------------------------------

@given(
    jd=st.text(
        alphabet=st.characters(whitelist_categories=("L", "Zs")),
        max_size=80,
    )
)
@settings(max_examples=120, deadline=None)
@example(jd=next(f["jd"] for f in FIXTURES if f["id"] == "it-ambiguous"))
def test_property_no_signal_falls_through_to_conservative_default(jd):
    """INVARIANT: a JD with no hard/soft signal classifies true via rule 9."""
    if matches_hard_trigger(jd) or matches_soft_trigger(jd):
        return  # precondition: no trigger of any kind
    assert classify_location_hard(jd) is True


# ---------------------------------------------------------------------------
# Property 4 — the classifier is total and deterministic: it returns a bool
# for any string and the same input always yields the same output.
# ---------------------------------------------------------------------------

@given(jd=st.text(max_size=200))
@settings(max_examples=120, deadline=None)
def test_property_classifier_is_total_and_deterministic(jd):
    """INVARIANT: classifier returns a bool, deterministically, for any input."""
    first = classify_location_hard(jd)
    second = classify_location_hard(jd)
    assert isinstance(first, bool)
    assert first is second
