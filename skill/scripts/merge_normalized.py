"""
Phase 2.7.3 — Merge: combine cluster re-evaluation results with isolated developer scores.

Reads triage output + all rank-<TASK_ID>-cluster-*.json files.
Produces normalized-<TASK_ID>.json with normalizedScore for every developer.

Usage: python merge_normalized.py <TASK_ID>
"""
import json
import sys
import os

import pass_io

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

_EXPECTED_TOP_KEYS = {"clusterId", "rankings"}
_ALLOWED_ENTRY_KEYS = {"login", "normalizedScore", "rankComment"}

# --- hrScore constants ---
HR_SCORE_REPO_WEIGHT = 20
HR_SCORE_REPO_CAP = 100
HR_SCORE_HIREABLE_BONUS = 20
HR_SCORE_ACTIVE_THRESHOLD = 180
HR_SCORE_ACTIVE_BONUS = 10
CELEBRITY_STAR_THRESHOLD = 50000
HR_SCORE_CELEBRITY_PENALTY = 10

# --- JD penalty constants (E-02) ---
# Linear decay from mc=0 (floor 0.3) to mc=20 (no penalty), replacing binary cliff at mc=10.
JD_PENALTY_THRESHOLD = 20
JD_PENALTY_FLOOR = 0.3


def jd_penalty_factor(match_confidence) -> float:
    """Return the JD mismatch penalty factor for compositeScore.

    Linear decay: max(JD_PENALTY_FLOOR, mc/JD_PENALTY_THRESHOLD) for mc < threshold.
    Returns 1.0 (no penalty) when match_confidence is None (manual mode) or >= threshold.

    Args:
        match_confidence: integer 0-100 or None (manual-mode tasks have no JD fit signal).

    Examples:
        jd_penalty_factor(0)   → 0.3   (floor, true mismatch)
        jd_penalty_factor(5)   → 0.3   (floor, 5/20 = 0.25 < 0.3)
        jd_penalty_factor(10)  → 0.5   (10/20)
        jd_penalty_factor(19)  → 0.95  (19/20)
        jd_penalty_factor(20)  → 1.0   (at threshold, no penalty)
        jd_penalty_factor(None)→ 1.0   (manual mode, no penalty)
    """
    if match_confidence is None or match_confidence >= JD_PENALTY_THRESHOLD:
        return 1.0
    return max(JD_PENALTY_FLOOR, match_confidence / JD_PENALTY_THRESHOLD)


def compute_hr_score(dev: dict) -> int:
    """Compute hiring-potential score for ranking.

    Formula: min(tr*REPO_WEIGHT, REPO_CAP) + hireable_bonus + active_bonus - celebrity_penalty
    Pure function, no I/O.
    """
    tr = dev.get("targetLanguageRepoCount", 0) or 0
    hireable = dev.get("isHireable", False) or False
    cd = dev.get("contributionDays", 0) or 0
    stars = dev.get("totalStarsReceived", 0) or 0

    score = min(tr * HR_SCORE_REPO_WEIGHT, HR_SCORE_REPO_CAP)
    if hireable:
        score += HR_SCORE_HIREABLE_BONUS
    if cd >= HR_SCORE_ACTIVE_THRESHOLD:
        score += HR_SCORE_ACTIVE_BONUS
    if stars > CELEBRITY_STAR_THRESHOLD:
        score -= HR_SCORE_CELEBRITY_PENALTY
    return max(score, 0)


def _load_rank_file(rank_path: str) -> tuple:
    """Load a cluster rank file.

    Returns (rankings: list, warnings: list[str]).
    Warns on unexpected top-level keys (schema drift) but does not fail.
    Strips unexpected keys from individual ranking entries.
    """
    with open(rank_path) as f:
        rank_data = json.load(f)

    warnings = []
    extra_top_keys = set(rank_data.keys()) - _EXPECTED_TOP_KEYS
    if extra_top_keys:
        warnings.append(
            f"Unexpected top-level keys in {os.path.basename(rank_path)}: "
            f"{sorted(extra_top_keys)} — strip and ignore"
        )

    rankings = []
    for entry in rank_data.get("rankings", []):
        filtered = {k: entry[k] for k in _ALLOWED_ENTRY_KEYS if k in entry}
        rankings.append(filtered)

    return rankings, warnings


def main():
    TASK_ID = sys.argv[1] if len(sys.argv) > 1 else None
    if not TASK_ID:
        print("Usage: python merge_normalized.py <TASK_ID>")
        sys.exit(1)

    triage_path = os.path.join(OUTPUT_DIR, f"triage-{TASK_ID}.json")
    if not os.path.exists(triage_path):
        print(f"[merge] ERROR: triage-{TASK_ID}.json not found. Run triage first.")
        sys.exit(1)

    with open(triage_path) as f:
        triage = json.load(f)

    # Start with isolated developers (already have normalizedScore)
    normalized = {}
    for iso in triage.get("isolated", []):
        normalized[iso["login"]] = {
            "login": iso["login"],
            "normalizedScore": iso["normalizedScore"],
            "rankComment": None,
            "rankingMethod": "deterministic",
        }

    # Load cluster results
    clusters_succeeded = 0
    clusters_failed = 0
    for cluster in triage.get("clusters", []):
        cluster_id = cluster["id"]
        rank_path = os.path.join(OUTPUT_DIR, f"rank-{TASK_ID}-cluster-{cluster_id}.json")

        if os.path.exists(rank_path):
            try:
                rankings, schema_warnings = _load_rank_file(rank_path)
                for w in schema_warnings:
                    print(f"[merge] SCHEMA WARNING: {w}")
                is_forced_ai = cluster.get("forcedAI", False)
                for entry in rankings:
                    normalized[entry["login"]] = {
                        "login": entry["login"],
                        "normalizedScore": entry["normalizedScore"],
                        "rankComment": entry.get("rankComment"),
                        "rankingMethod": "ai_forced" if is_forced_ai else "ai_cluster",
                    }
                clusters_succeeded += 1
                # QT-03: a rank file can come back PARTIAL (fewer logins than the
                # cluster) — previously the missing devs silently vanished from
                # the normalized output. Reconcile: raw-score fallback + warning.
                ranked_logins = {e["login"] for e in rankings}
                missing = [l for l in cluster.get("logins", []) if l not in ranked_logins]
                if missing:
                    print(f"[merge] WARNING: cluster {cluster_id} rank file is partial — "
                          f"{len(missing)} of {len(cluster.get('logins', []))} logins missing "
                          f"({missing[:5]}{'...' if len(missing) > 5 else ''}); raw-score fallback")
                    _fallback_logins(missing, normalized, TASK_ID)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[merge] WARNING: Failed to parse rank file for cluster {cluster_id}: {e}")
                clusters_failed += 1
                _fallback_cluster(cluster, normalized, TASK_ID)
        else:
            print(f"[merge] WARNING: rank-{TASK_ID}-cluster-{cluster_id}.json not found. Using raw scores.")
            clusters_failed += 1
            _fallback_cluster(cluster, normalized, TASK_ID)

    # Load prefilter data for tiebreaker (optional).
    # JD-07/MATH-05 fix: shared loader reads BOTH pass1 and pass2 files —
    # previously pass2-only developers had no boost and hrScore=0, a flat
    # −15 pt composite handicap uncorrelated with merit.
    boost_map = {}
    for login, s in pass_io.load_prefilter_survivor_map(TASK_ID, OUTPUT_DIR).items():
        boost_map[login] = s.get("prefilterBoost", 0)
    if boost_map:
        print(f"[merge] Prefilter loaded: {len(boost_map)} survivors with boost data")

    # Load graphql data (pass1 + pass2) and compute hrScore for each developer
    hr_score_map = {}
    for login, dev in pass_io.load_graphql_map(TASK_ID, OUTPUT_DIR).items():
        if login in normalized:
            hr_score_map[login] = compute_hr_score(dev)
    print(f"[merge] hrScore computed for {len(hr_score_map)} developers")

    # Enrich normalized entries with prefilter adjustments and hrScore
    for login, entry in normalized.items():
        if login in boost_map:
            entry["prefilterAdjustments"] = [f"boost:{boost_map[login]}"]
        if login in hr_score_map:
            entry["hrScore"] = hr_score_map[login]

    # Load matchConfidence from score batches for JD penalty (D2)
    all_raw_scores = _load_all_raw_scores(TASK_ID)
    match_confidence_map = {}
    for login, score_data in all_raw_scores.items():
        mc = score_data.get("matchConfidence")
        if mc is not None:
            match_confidence_map[login] = mc

    # Blend hrScore into composite for final ranking.
    # normalizedScore is 0-100 (AI), hrScore is 0-130 (HR signal).
    # Normalize hrScore to 0-100 range, then blend 85/15.
    HR_SCORE_MAX = HR_SCORE_REPO_CAP + HR_SCORE_HIREABLE_BONUS + HR_SCORE_ACTIVE_BONUS  # 130
    BLEND_AI = 0.85
    BLEND_HR = 0.15
    for login, entry in normalized.items():
        ns = entry["normalizedScore"]
        hrs = hr_score_map.get(login, 0)
        hrs_normalized = (hrs / HR_SCORE_MAX) * 100 if HR_SCORE_MAX > 0 else 0
        entry["compositeScore"] = round(BLEND_AI * ns + BLEND_HR * hrs_normalized, 2)

        # D2: JD mismatch penalty — linear decay max(0.3, mc/20) for mc < 20 (E-02)
        # Replaces previous binary cliff at mc=10 with graduated decay.
        mc = match_confidence_map.get(login)
        factor = jd_penalty_factor(mc)
        if factor != 1.0:
            entry["compositeScore"] = round(entry["compositeScore"] * factor, 2)

    # Write output — sort by compositeScore DESC; tiebreakers: objectiveScore
    # (N1/MATH-09: among equally-penalized devs the intrinsically better code
    # must rank first), then prefilterBoost
    obj_map = {}
    for login, score_data in all_raw_scores.items():
        bd = score_data.get("scoreBreakdown") or {}
        dims = [v for v in bd.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if dims:
            obj_map[login] = sum(dims)
    result = sorted(
        normalized.values(),
        key=lambda x: (x.get("compositeScore", x["normalizedScore"]),
                       obj_map.get(x["login"], 0),
                       boost_map.get(x["login"], 0)),
        reverse=True,
    )
    out_path = os.path.join(OUTPUT_DIR, f"normalized-{TASK_ID}.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[merge] {len(result)} developers normalized")
    print(f"[merge] Clusters: {clusters_succeeded} succeeded, {clusters_failed} failed (fallback)")
    print(f"[merge] Output: {out_path}")


def _fallback_cluster(cluster, normalized, TASK_ID):
    """Fallback: use raw scores from the original score batches for failed clusters."""
    _fallback_logins(cluster.get("logins", []), normalized, TASK_ID)


def _fallback_logins(logins, normalized, TASK_ID):
    """Raw-score fallback for specific logins (whole failed cluster, or the
    logins a partial rank file omitted — QT-03)."""
    all_scores = _load_all_raw_scores(TASK_ID)
    for login in logins:
        raw = all_scores.get(login, {})
        normalized[login] = {
            "login": login,
            "normalizedScore": raw.get("score", 0),
            "rankComment": None,
            "rankingMethod": "ai_cluster_fallback",
        }


def _load_all_raw_scores(TASK_ID):
    """Load all raw score batch files into a login -> score_data map.

    Delegates to the shared pass_io loader (canonical precedence: pass1 wins).
    """
    return pass_io.load_score_map(TASK_ID, OUTPUT_DIR)


if __name__ == "__main__":
    main()
