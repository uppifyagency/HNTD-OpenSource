"""
Phase 2.7.1 — Triage: identify clusters of developers with similar scores.

Reads all score batch files for a task, sorts by score, groups developers
within ±10 points into clusters. Clusters >8 are split into sub-clusters.

Usage: python triage_clusters.py <TASK_ID>
"""
import json
import sys
import os

import pass_io

TASK_ID = sys.argv[1] if len(sys.argv) > 1 else None
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
MAX_CLUSTER_SIZE = 8


def calculate_threshold(scores: list[int]) -> int:
    """
    Adaptive threshold based on score distribution.
    Uses IQR (interquartile range) / 4, clamped to [5, 15].

    Tight distributions (most scores 40-60) → smaller threshold (5-8)
    Wide distributions (scores 10-90) → larger threshold (10-15)
    Floor of 5: below this, clustering is meaningless
    Ceiling of 15: above this, clusters become too large
    """
    if len(scores) < 3:
        return 10

    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    q1 = sorted_scores[n // 4]
    q3 = sorted_scores[3 * n // 4]
    iqr = q3 - q1

    threshold = max(5, min(15, iqr // 4))
    return threshold


def load_all_scores(task_id=None, output_dir=None):
    """Load all score batch files into a deduplicated list of {login, score, ...}.

    Delegates to the shared pass_io loader (canonical precedence: pass1 wins).
    JD-08/MATH-04: previously this returned raw duplicates and main() kept the
    MAX score across passes — a third dedup policy unique to this script.
    """
    return pass_io.load_score_entries(task_id or TASK_ID, output_dir or OUTPUT_DIR)


def build_clusters(sorted_devs, threshold=10):
    """
    Walk the sorted list (DESC by score). Two consecutive devs are 'ambiguous'
    if |scoreA - scoreB| <= threshold. Group chains into clusters.
    """
    if not sorted_devs:
        return [], []

    clusters = []
    isolated = []
    current_chain = [sorted_devs[0]]

    for i in range(1, len(sorted_devs)):
        prev_score = sorted_devs[i - 1].get("score", 0)
        curr_score = sorted_devs[i].get("score", 0)

        if abs(prev_score - curr_score) <= threshold:
            current_chain.append(sorted_devs[i])
        else:
            # Flush current chain
            if len(current_chain) == 1:
                dev = current_chain[0]
                isolated.append({
                    "login": dev["login"],
                    "score": dev.get("score", 0),
                    "normalizedScore": dev.get("score", 0),
                })
            else:
                clusters.append(current_chain)
            current_chain = [sorted_devs[i]]

    # Flush last chain
    if len(current_chain) == 1:
        dev = current_chain[0]
        isolated.append({
            "login": dev["login"],
            "score": dev.get("score", 0),
            "normalizedScore": dev.get("score", 0),
        })
    else:
        clusters.append(current_chain)

    return clusters, isolated


def chunk_without_singletons(items, max_size=MAX_CLUSTER_SIZE):
    """Split items into chunks of <= max_size where NO chunk has size 1 (QT-02).

    With len % max_size == 1 the naive chunking left a singleton chunk that
    was silently dropped (the developer vanished from normalized output);
    rebalance the last two chunks to (max_size-1, 2) instead. A single item
    (len==1) cannot be rebalanced — caller routes it to `isolated`.
    """
    n = len(items)
    if n <= max_size:
        return [items]
    chunks = []
    start = 0
    while n - start > max_size:
        take = max_size
        if n - start - max_size == 1:  # would leave a final singleton
            take = max_size - 1
        chunks.append(items[start:start + take])
        start += take
    chunks.append(items[start:])
    return chunks


def split_large_clusters(clusters):
    """Split clusters with >MAX_CLUSTER_SIZE into sub-clusters.

    Boundary developers (last of chunk N, first of chunk N+1) are NOT
    compared by the same ranker. See OPEN-ISSUES.md and
    root-cause-analysis-all-findings.md#e-05 for the overlap
    implementation backlog item (deferred — User chose Option B).
    QT-02: chunking never produces a droppable singleton (rebalanced).
    """
    result = []
    for chain in clusters:
        result.extend(chunk_without_singletons(chain))
    return result


def load_rankings(task_id=None, output_dir=None):
    """Load deterministic rankings. Falls back to raw scores if not available."""
    task_id = task_id or TASK_ID
    output_dir = output_dir or OUTPUT_DIR
    rank_path = os.path.join(output_dir, f"deterministic-rank-{task_id}.json")
    if os.path.exists(rank_path):
        with open(rank_path) as f:
            data = json.load(f)
        result = [
            {"login": r["login"], "score": r.get("deterministicRank"), "forcedAI": r.get("forcedAI", False)}
            for r in data.get("rankings", [])
        ]
        print(f"[triage] Using deterministic rankings ({len(result)} developers)")
        return result
    print("[triage] No deterministic-rank file, falling back to raw scores")
    return load_all_scores(task_id, output_dir)


def main():
    if not TASK_ID:
        print("Usage: python triage_clusters.py <TASK_ID>")
        sys.exit(1)

    scores = load_rankings()
    if not scores:
        print(f"[triage] No scores found for task {TASK_ID}")
        sys.exit(1)

    # Separate forced-AI devs (no code quality score — need AI ranking)
    forced_ai = [s for s in scores if s.get("forcedAI", False)]
    regular = [s for s in scores if not s.get("forcedAI", False)]

    # Sources are already deduplicated by the shared loaders (pass1 wins);
    # keep a first-wins guard so no alternate policy can sneak back in (JD-08).
    seen = {}
    for s in regular:
        if s["login"] not in seen:
            seen[s["login"]] = s
    unique_scores = sorted(seen.values(), key=lambda x: x.get("score", 0), reverse=True)

    print(f"[triage] {len(unique_scores)} developers to triage")

    score_values = [s.get("score", 0) for s in unique_scores]
    if not score_values:
        print("[triage] No scores to triage — skipping to forced-AI only")
        threshold = 0
    else:
        threshold = calculate_threshold(score_values)
        print(f"[triage] Adaptive threshold: {threshold} (IQR-based, range {min(score_values)}-{max(score_values)})")

    clusters, isolated = build_clusters(unique_scores, threshold)
    clusters = split_large_clusters(clusters)

    # Build output
    cluster_output = []
    for idx, chain in enumerate(clusters):
        logins = [d["login"] for d in chain]
        scores_in_cluster = [d.get("score", 0) for d in chain]
        cluster_output.append({
            "id": idx,
            "logins": logins,
            "scoreRange": [min(scores_in_cluster), max(scores_in_cluster)],
        })

    # Add forced-AI devs as dedicated cluster(s), score-stratified (D3 fix).
    # QT-02: chunking is singleton-free; a lone forced-AI dev goes to isolated
    # with normalizedScore = score instead of silently disappearing.
    if forced_ai:
        sorted_forced = sorted(forced_ai, key=lambda x: x.get("score", 0), reverse=True)
        for chunk in chunk_without_singletons(sorted_forced):
            if len(chunk) == 1:
                dev = chunk[0]
                isolated.append({
                    "login": dev["login"],
                    "score": dev.get("score", 0),
                    "normalizedScore": dev.get("score", 0),
                })
                print(f"[triage] Lone forced-AI dev {dev['login']} routed to isolated (QT-02)")
                continue
            chunk_logins = [d["login"] for d in chunk]
            chunk_scores = [d.get("score", 0) for d in chunk]
            cluster_output.append({
                "id": len(cluster_output),
                "logins": chunk_logins,
                "scoreRange": [min(chunk_scores), max(chunk_scores)],
                "forcedAI": True,
            })
        print(f"[triage] {len(forced_ai)} forced-AI developers split into stratified clusters")

    output = {
        "clusters": cluster_output,
        "isolated": isolated,
    }

    out_path = os.path.join(OUTPUT_DIR, f"triage-{TASK_ID}.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[triage] {len(cluster_output)} clusters, {len(isolated)} isolated developers")
    for c in cluster_output:
        print(f"  Cluster {c['id']}: {len(c['logins'])} devs, score range {c['scoreRange']}")
    for iso in isolated:
        print(f"  Isolated: {iso['login']} (score={iso['score']})")
    print(f"[triage] Output: {out_path}")


if __name__ == "__main__":
    main()
