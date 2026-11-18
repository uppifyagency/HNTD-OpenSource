"""
E-13: Add batching limit to Phase 5 ranker dispatch.

Driving port: skill/skills/github-hr-run/SKILL.md (orchestrator instructions)
Observable outcome: Phase 5 dispatch section contains an explicit limit of
"max 5 parallel agents per turn" so the orchestrator does not launch 26
ranker subagents simultaneously (as happened in the 309-dev task where
77% of clusters failed to produce rank files).

This is a STRUCTURAL test: the fix is a documentation/instruction change
in SKILL.md that the Claude Code orchestrator reads at runtime. A runtime
behavior test is not meaningful — the structural assertion IS the contract.

Bug reference: BUG E-13 — Phase 5 had no parallelism limit, 20/26 clusters
failed in the 309-dev task.
Root cause: docs/analysis/root-cause-analysis-all-findings.md#e-13
"""
import os
import re

import pytest

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "..")
)
SKILL_MD = os.path.join(
    REPO_ROOT, "skill", "skills", "github-hr-run", "SKILL.md"
)


@pytest.fixture(scope="module")
def skill_source() -> str:
    assert os.path.exists(SKILL_MD), f"SKILL.md not found at {SKILL_MD}"
    with open(SKILL_MD, "r", encoding="utf-8") as f:
        return f.read()


def _extract_section(source: str, header: str, next_header_pattern: str) -> str:
    """Extract text from a markdown section header until the next section."""
    start = source.find(header)
    assert start != -1, f"Section header not found: {header!r}"
    rest = source[start:]
    next_match = re.search(next_header_pattern, rest[len(header):])
    if next_match is None:
        return rest
    return rest[: len(header) + next_match.start()]


# --- Scenario 1: Phase 5 section has an explicit batching limit of 5 ---

def test_phase_5_has_batching_limit(skill_source: str):
    """
    Given the Phase 5 Triage + AI Ranking section of SKILL.md,
    When the text is parsed for dispatch instructions,
    Then it MUST contain an explicit limit of "max 5 parallel agents per turn"
    (case insensitive), adapted from the Phase 4.1 pattern (which uses 10).

    Phase 5 is STRICTER than Phase 4.1 because each ranker subagent receives
    heavier context per cluster (up to 8 developer profiles vs. 1 per scorer).
    """
    phase_5_section = _extract_section(
        skill_source,
        "### Phase 5: Triage + AI Ranking",
        r"\n### Phase \d",
    )

    pattern = re.compile(
        r"max\s+5\s+parallel\s+agents?\s+per\s+turn",
        re.IGNORECASE,
    )
    assert pattern.search(phase_5_section), (
        "Phase 5 ranking section does not contain the required batching "
        "limit 'max 5 parallel agents per turn'. Without this, the "
        "orchestrator launches all clusters simultaneously and ~77% of "
        "ranker subagents fail at scale (309-dev task / 26 clusters). "
        "See docs/analysis/root-cause-analysis-all-findings.md#e-13."
    )


# --- Scenario 2: Phase 4.1 batching limit regression guard ---

def test_phase_4_1_batching_limit_still_present(skill_source: str):
    """
    Regression guard: Phase 4.1 already had a 'max 10 parallel agents per turn'
    safeguard. When adding Phase 5's stricter limit, we MUST NOT accidentally
    damage or remove the Phase 4.1 safeguard.
    """
    phase_4_1_section = _extract_section(
        skill_source,
        "### Phase 4.1",
        r"\n### Phase \d",
    )

    pattern = re.compile(
        r"max\s+10\s+parallel\s+agents?\s+per\s+turn",
        re.IGNORECASE,
    )
    assert pattern.search(phase_4_1_section), (
        "Phase 4.1 scoring section no longer contains the 'max 10 parallel "
        "agents per turn' safeguard. This is a regression — do not remove "
        "the Phase 4.1 limit when adding the Phase 5 limit."
    )
