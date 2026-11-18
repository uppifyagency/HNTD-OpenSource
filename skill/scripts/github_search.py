#!/usr/bin/env python3
"""GitHub user search via gh CLI. Replaces github-hr-searcher agent.

Executes search strategies via `gh api`, deduplicates, removes bots, and writes output.
"""
import argparse
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

OUTPUT_DIR = Path(__file__).parent.parent / "output"
POOL_MULTIPLIER = 6

# ADR-021 Slice 03a: minimum inter-call delay between consecutive GitHub
# `search/users` calls. 60 s / 30 req-per-min Search-API limit = 2 s. This is
# the concrete throttle mechanism -- a deterministic stdlib time.sleep pause.
SEARCH_THROTTLE_SECONDS = 2

# ADR-021 Slice 03a: per-query pagination ceiling. GitHub serves at most
# 1000 results / 100-per-page = 10 pages for any one query; MAX_PAGES_PER_QUERY
# coincides with that hard ceiling so the loop never reads a page GitHub
# would not serve.
MAX_PAGES_PER_QUERY = 10
# ADR-021 Slice 03b: recursive-bisection follower-windowing depth ceiling. The
# bisection recurses no deeper than this; a band still over the per-query cap
# at this depth is accepted as an unrecoverable cap and logged.
MAX_WINDOW_DEPTH = 10

# ADR-020 5-tier model: priorityTier enum -> rank. Lower rank = more specific.
# priorityTier is the canonical trim key (ADR-020); the priority integer is
# the in-tier tiebreaker. TIER_RANK orders exact_city above keyword.
TIER_RANK = {"exact_city": 0, "country": 1, "major_city": 2,
             "extended_city": 3, "keyword": 4}
# ADR-021 B2a: the four LOCATION-SPECIFIC tiers. A location query is run with
# sort=repositories to avoid GitHub's celebrity-biased default ordering; the
# non-locational keyword tier is left on the default order.
LOCATION_TIERS = frozenset({"exact_city", "country", "major_city", "extended_city"})
# priority integer (1=highest) -> priorityTier. Used as the fallback when a
# strategy carries no explicit priorityTier (legacy strategies / older files).
PRIORITY_TO_TIER = {1: "exact_city", 2: "country", 3: "major_city",
                    4: "extended_city", 5: "keyword"}


def strategy_tier(strategy: dict) -> str:
    """Return a strategy's priorityTier, falling back to the priority mapping.

    ADR-020/022: build_strategies emits an explicit priorityTier on every
    strategy. A legacy strategy file without the field is mapped from its
    priority integer; an unknown priority falls back to the weakest tier so a
    missing field never crashes the search.
    """
    tier = strategy.get("priorityTier")
    if tier in TIER_RANK:
        return tier
    return PRIORITY_TO_TIER.get(strategy.get("priority", 99), "keyword")


def tier_rank(tier: str) -> int:
    """Rank of a priorityTier (lower = more specific). Unknown -> weakest."""
    return TIER_RANK.get(tier, len(TIER_RANK))


# ADR-021 Slice 03b: the per-task `search/users` call budget. Issuing more
# than this many GitHub search calls for one task is a hard stop -- the search
# finalises a partial pool from whatever was retrieved instead of crashing.
# SPIKE-measured worst case: 85 single-language / ~255 projected 3-language;
# 300 is the safety ceiling. The budget is enforced ACROSS the whole search_all
# run -- all strategies, all pages, all follower windows.
MAX_SEARCH_CALLS_PER_TASK = 300

# ADR-021 Slice 03b: HTTP-403 secondary-rate-limit back-off. On a 403
# secondary-rate-limit response the same call is retried after a 60 s wait,
# capped at this many retries; after the cap the call is abandoned and logged
# so recall degrades gracefully rather than crashing.
RATE_LIMIT_BACKOFF_SECONDS = 60
MAX_RATE_LIMIT_RETRIES = 3


class SearchCallBudget:
    """Task-level guard counting GitHub `search/users` calls (ADR-021 03b).

    `MAX_SEARCH_CALLS_PER_TASK` is a TASK-LEVEL ceiling enforced across the
    whole `search_all` run -- every strategy, every paginated page and every
    follower-windowed sub-query draws from the SAME budget. `consume()` returns
    False once the ceiling is reached; the searcher then stops issuing new
    calls and finalises a partial pool. A budget never crashes the search.
    """

    def __init__(self, limit: int = MAX_SEARCH_CALLS_PER_TASK):
        self.limit = limit
        self.calls = 0
        self.exhausted = False

    def consume(self) -> bool:
        """Reserve one call. Returns False (and logs once) when budget is spent."""
        if self.calls >= self.limit:
            if not self.exhausted:
                self.exhausted = True
                print(f"  [search] WARNING: per-task search-call budget "
                      f"{self.limit} reached -- stopping the search and "
                      f"finalising a partial pool")
            return False
        self.calls += 1
        return True


def _is_secondary_rate_limit(stderr: str) -> bool:
    """Detect a GitHub HTTP-403 secondary-rate-limit response in gh stderr."""
    text = stderr.lower()
    return "403" in text and ("secondary rate limit" in text
                              or "rate limit" in text)


def _fetch_search_page(query: str, page: int, per_page: int,
                       sort: str | None) -> tuple[list[dict], int]:
    """Issue one GitHub search_users call for a single page.

    Returns (items, total_count). On failure returns ([], 0) so the caller
    stops paginating cleanly rather than crashing.

    ADR-021 Slice 03b: an HTTP-403 secondary-rate-limit response is retried
    after a `RATE_LIMIT_BACKOFF_SECONDS` wait, capped at `MAX_RATE_LIMIT_RETRIES`
    retries; after the cap the call is abandoned and logged (recall degrades
    gracefully, never a crash).
    """
    encoded_query = quote(query, safe=":><=+")
    url = f"search/users?q={encoded_query}&per_page={per_page}"
    if sort:
        url += f"&sort={sort}&order=desc"
    if page > 1:
        url += f"&page={page}"
    cmd = ["gh", "api", url]
    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=30, encoding="utf-8",
                                    errors="replace")
            if result.returncode != 0:
                stderr = result.stderr.strip()
                if (_is_secondary_rate_limit(stderr)
                        and attempt < MAX_RATE_LIMIT_RETRIES):
                    print(f"  [search] WARNING: 403 secondary rate limit for "
                          f"query '{query}' page {page} -- backing off "
                          f"{RATE_LIMIT_BACKOFF_SECONDS}s "
                          f"(retry {attempt + 1}/{MAX_RATE_LIMIT_RETRIES})")
                    time.sleep(RATE_LIMIT_BACKOFF_SECONDS)
                    continue
                if _is_secondary_rate_limit(stderr):
                    print(f"  [search] WARNING: gh api abandoned for query "
                          f"'{query}' page {page} after "
                          f"{MAX_RATE_LIMIT_RETRIES} rate-limit retries: "
                          f"{stderr}")
                else:
                    print(f"  [search] WARNING: gh api failed for query "
                          f"'{query}' page {page}: {stderr}")
                return [], 0
            data = json.loads(result.stdout)
            return data.get("items", []), data.get("total_count", 0)
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            print(f"  [search] ERROR: {e}")
            return [], 0
    return [], 0


def _page_count_for(total_count: int, per_page: int) -> int:
    """Pages to read for `total_count` results, capped at MAX_PAGES_PER_QUERY.

    ADR-021 Slice 03a: page_count = min(ceil(total_count/per_page),
    MAX_PAGES_PER_QUERY) -- at least 1, never more than the per-query ceiling.
    """
    return min(max(1, math.ceil(total_count / per_page)), MAX_PAGES_PER_QUERY)


def _paginate_remaining_pages(query: str, first_items: list[dict],
                              total_count: int, per_page: int,
                              sort: str | None,
                              budget: "SearchCallBudget | None") -> list[dict]:
    """Read pages 2..page_count for a query whose page 1 is already retrieved.

    `first_items` is the page-1 result the caller already fetched (and, when a
    budget is supplied, already charged for); this reads the remaining pages.
    A minimum SEARCH_THROTTLE_SECONDS time.sleep delay is applied before every
    page fetch. Pagination stops early on an exhausted budget or an empty page;
    the items retrieved so far are returned (partial, never a crash).
    """
    items = list(first_items)
    for page in range(2, _page_count_for(total_count, per_page) + 1):
        if budget is not None and not budget.consume():
            break
        time.sleep(SEARCH_THROTTLE_SECONDS)
        page_items, _ = _fetch_search_page(query, page, per_page, sort)
        if not page_items:
            break
        items.extend(page_items)
    return items


def run_search(query: str, per_page: int = 100, sort: str | None = None,
               budget: "SearchCallBudget | None" = None) -> list[dict]:
    """Execute a GitHub search_users query, paginating to the per-query cap.

    ADR-021 Slice 03a: the first per_page=100 call reports total_count; while
    total_count > 100 the loop reads &page=2..N, stopping at
    page_count = min(ceil(total_count/100), MAX_PAGES_PER_QUERY) -- the GitHub
    1000/100 per-query ceiling and MAX_PAGES_PER_QUERY=10 coincide at 10 pages,
    whichever is hit first. A minimum SEARCH_THROTTLE_SECONDS inter-call delay
    is applied via time.sleep before every call after the first.

    ADR-021 Slice 03b: when a `SearchCallBudget` is supplied, every page draws
    one unit from the TASK-LEVEL budget; once the budget is spent pagination
    stops and the items retrieved so far are returned (partial, never a crash).
    """
    if budget is not None and not budget.consume():
        return []
    first_items, total_count = _fetch_search_page(query, 1, per_page, sort)
    print(f"  [search] total_count={total_count} for query '{query}'")
    return _paginate_remaining_pages(query, first_items, total_count,
                                     per_page, sort, budget)


# QT-11: well-known bot accounts that don't follow the "-bot"/"[bot]" convention.
# A bare endswith("bot") also dropped real humans (talbot, abbot, Cabot, ...).
KNOWN_BOT_LOGINS = frozenset({
    "bot", "dependabot", "renovate", "github-actions", "greenkeeper",
    "codecov", "imgbot", "allcontributors", "depfu", "snyk",
    "k8s-ci-robot", "goreleaserbot", "traviscibot", "mergify", "stale",
})


def is_bot(login: str) -> bool:
    """Check if login looks like a bot account.

    Restricted to the explicit conventions ("[bot]" tag, "-bot" suffix) plus a
    small list of well-known bots; a generic "...bot" suffix is a human surname
    more often than a bot (QT-11).
    """
    login_lower = login.lower()
    return ("[bot]" in login_lower
            or login_lower.endswith("-bot")
            or login_lower in KNOWN_BOT_LOGINS)


def _provenance_key(tier: str, priority: int) -> tuple[int, int]:
    """The (tier_rank, priority) provenance-strength key (ADR-020/022).

    Lower is stronger: the MOST-SPECIFIC tier wins, and within a tier the LOWER
    priority integer wins. Used both to rank a new search hit (the challenger)
    and to score the strategy already recorded for a login (the incumbent).
    """
    return (tier_rank(tier), priority)


def _trim_key(entry: dict) -> tuple[int, int, int]:
    """Pool-trim ordering key for a `seen` entry (lower wins).

    `(tier_rank, priority)` is the ADR-020/022 provenance strength; the third
    element is the candidate's repo-sorted position WITHIN its follower window.
    Within one tier+priority bucket the windowed search returns each follower
    band repo-sorted but concatenates the bands follower-ascending, so a plain
    stable sort kept the LOWEST-follower devs and silently trimmed the genuinely
    strongest (FINDINGS 2026-06-11: topdev1/TopDev2/topdev3 were top-40 by repos yet
    dropped, while low-follower weakdev1/weakdev2 survived). Ordering by within
    -window rank interleaves the bands -- the cap keeps the best-of-each window,
    not the first-fetched.

    This yields follower-band EQUITY (each band's head before any band's 2nd),
    NOT a global repo ranking: a small high-follower band's #0 can precede a
    large band's #50 that has more repos. That is deliberate -- a true global
    repo-sort is not obtainable here because GitHub's search/users payload omits
    public_repos, so a global ranking would cost one profile fetch PER candidate
    (~1462 for this one tier), far past the search-call budget. windowRank is
    the only zero-cost quality proxy, and sort=repositories makes it a faithful
    within-band one. (The unfetched tail of an over-1000 real band is the
    separate cap-blind issue #26, out of scope here.)

    `bestWindowRank` defaults to 0 so an entry recorded before the windowRank
    signal exists sorts exactly as the legacy (tier_rank, priority) key did.
    """
    return (*_provenance_key(entry["bestStrategyTier"],
                             entry["bestStrategyPriority"]),
            entry.get("bestWindowRank", 0))


def _register_candidate(seen: dict, item: dict, tier: str, priority: int,
                        exclude_logins: set[str]) -> None:
    """Filter one search hit and record it in `seen` if its provenance wins.

    Bots, organisations and excluded logins are dropped. For a surviving hit
    the dedup tiebreak (ADR-020/022, D-DESIGN-3) keeps the strongest provenance:
    when a developer is matched by several strategies the entry in `seen`
    carries the most-specific tier, then the lower priority integer, then the
    lower within-window repo rank (`windowRank`, FINDINGS 2026-06-11) -- the
    same `_trim_key` ordering used by the pool trim. Mutates `seen` in place.

    Note: on a same-(tier, priority) tie the stored id/avatarUrl/profileUrl now
    come from the lower-windowRank occurrence (was: first-seen). That is safe
    only because push_results carries those from the later fetch profile, not
    from this search record (SEARCH_PROVENANCE_FIELDS whitelist) -- a future
    consumer reading entry['id']/avatarUrl directly should know it may differ.
    """
    login = item.get("login", "")
    if not login:
        return
    if is_bot(login):
        # QT-11: bot drops were silent — log them so a wrongly-classified human is visible
        print(f"  [search] dropped bot-like login: {login}")
        return
    if login in exclude_logins or item.get("type") == "Organization":
        return
    # windowRank is the candidate's repo-sorted position within its follower
    # window (annotated at fetch, default 0 when absent). It joins provenance as
    # the in-tier tiebreaker so the dedup keeps the better-ranked occurrence and
    # the trim interleaves the bands instead of draining the first-fetched one.
    window_rank = item.get("windowRank", 0)
    challenger = (*_provenance_key(tier, priority), window_rank)
    incumbent = _trim_key(seen[login]) if login in seen else None
    if incumbent is None or challenger < incumbent:
        seen[login] = {
            "login": login,
            "id": item.get("id"),
            "avatarUrl": item.get("avatar_url", ""),
            "profileUrl": item.get("html_url", ""),
            "bestStrategyPriority": priority,
            "bestStrategyTier": tier,
            "bestWindowRank": window_rank,
        }


def _trim_pool(seen: dict, max_results: int) -> list[dict]:
    """Order the deduped candidates by trim key and cut to the pool size.

    Pure function of `seen` -- no I/O, no network. This is the testable seam
    for the cap: `search_all` does the impure fetch+dedup into `seen`, then
    hands the dict here. `_trim_key` defines the ordering; `POOL_MULTIPLIER`
    sizes the kept pool (max_results * POOL_MULTIPLIER, or all of them when
    max_results is 0).
    """
    developers = sorted(seen.values(), key=_trim_key)
    pool_size = max_results * POOL_MULTIPLIER if max_results else len(developers)
    if len(developers) > pool_size:
        developers = developers[:pool_size]
    return developers


def search_all(strategies: list[dict], max_results: int, exclude_logins: set[str]) -> tuple[list[dict], dict]:
    """Execute all strategies, dedup, filter, rank, trim.

    Returns (developers, stats) where stats tracks counts at each stage.
    """
    seen = {}  # login -> {dev_data, best_priority}
    total_raw = 0
    # ADR-021 Slice 03b: ONE task-level call budget shared across every
    # strategy, every page and every follower window of this search_all run.
    # When 300 search/users calls have been issued the search stops issuing
    # new calls and finalises a partial pool below (never a crash).
    budget = SearchCallBudget(MAX_SEARCH_CALLS_PER_TASK)

    for strategy in strategies:
        if budget.exhausted:
            break
        query = strategy["query"]
        priority = strategy.get("priority", 99)
        # ADR-020/022 5-tier provenance: priorityTier is the canonical trim
        # key, the priority integer is the in-tier tiebreaker.
        tier = strategy_tier(strategy)
        # ADR-021 B2a debiasing gate: keyed on priorityTier, NOT on the dead
        # `priority >= 20` condition. jd-parser/build_strategies emit
        # priorities 1..5 only, so the >=20 branch never fired and every
        # location query ran with GitHub's celebrity-biased default ("best
        # match") order. sort=repositories fires for the four location-
        # specific tiers; the non-locational keyword tier keeps the default.
        # D-DESIGN-5: sort is purely a debiasing lever, never a quality rank.
        sort = "repositories" if tier in LOCATION_TIERS else None
        sort_label = f" sort={sort}" if sort else ""
        print(f"  [search] Strategy p{priority} {tier}{sort_label}: {query}")

        # ADR-021 Slice 03b: the production search path runs every strategy
        # through run_search_windowed -- probe-before-window decides between
        # plain pagination (<= cap) and recursive-bisection follower-windowing
        # (> cap). The shared task-level `budget` halts the whole run at 300
        # search/users calls, finalising a partial pool.
        items = run_search_windowed(query, sort=sort, budget=budget)
        total_raw += len(items)
        print(f"  [search]   -> {len(items)} results")

        # Dedup tiebreak (ADR-020/022, D-DESIGN-3): each hit is filtered and
        # recorded keeping the strongest provenance across all matching
        # strategies (most-specific tier, then lower priority integer).
        for item in items:
            _register_candidate(seen, item, tier, priority, exclude_logins)

    after_dedup = len(seen)

    # ADR-020/022 trim: provenance (tier_rank, priority) is the PRIMARY ordering
    # -- exact-city (rank 0) ranks above country (1), major-city (2), extended
    # -city (3), keyword (4) -- and within a bucket the repo-sorted within
    # -window rank interleaves the follower bands (FINDINGS 2026-06-11). See
    # _trim_key. The cut to POOL_MULTIPLIER * max_results lives in _trim_pool.
    developers = _trim_pool(seen, max_results)

    stats = {
        "totalSearchResults": total_raw,
        "afterDedup": after_dedup,
        "finalCount": len(developers),
        # ADR-021 Slice 03b observability: how much of the call budget was
        # spent, and whether the per-task ceiling truncated the search.
        "searchCallsIssued": budget.calls,
        "budgetExhausted": budget.exhausted,
    }
    return developers, stats


# --- ADR-021 Slice 03b: recursive-bisection follower-windowing --------------
# The pagination, windowing-depth and per-task call ceilings are defined as
# named module constants near the top of this file (MAX_PAGES_PER_QUERY,
# MAX_WINDOW_DEPTH, MAX_SEARCH_CALLS_PER_TASK).

# ADR-021 per-query cap: GitHub serves at most 1000 results for any one query.
PER_QUERY_CAP = 1000
# ADR-021 initial bands: the bounded band starts at the min_followers default
# (2) and runs to 150; the open-ended band covers everything above 150.
MIN_FOLLOWERS = 2
INITIAL_BAND_SPLIT = 150

# Match the trailing `followers:` clause of a query so a windowed sub-query can
# substitute its own band. Covers `followers:>=2`, `followers:>150`,
# `followers:2..150` and a bare `followers:5`.
_FOLLOWERS_CLAUSE = re.compile(r"\bfollowers:\S+")


def _follower_clause(lo: int, hi: int | None) -> str:
    """Render a `followers:` query clause for a window.

    Bounded `[lo..hi]` -> `followers:lo..hi`; a degenerate `lo == hi` window
    -> the single-count `followers:N`; an open-ended window (hi is None)
    -> `followers:>=lo`.
    """
    if hi is None:
        return f"followers:>={lo}"
    if lo == hi:
        return f"followers:{lo}"
    return f"followers:{lo}..{hi}"


def windowed_query(query: str, lo: int, hi: int | None) -> str:
    """Return `query` with its `followers:` clause replaced by this window's.

    The base query already carries a `followers:` clause (the strategies emit
    `followers:>=2`); windowing swaps that clause for the window's band so the
    issued sub-query URL carries the assertable `followers:lo..hi` fragment.
    """
    clause = _follower_clause(lo, hi)
    if _FOLLOWERS_CLAUSE.search(query):
        return _FOLLOWERS_CLAUSE.sub(clause, query, count=1)
    return f"{query} {clause}"


def build_follower_windows(query: str, total_count: int) -> list[dict]:
    """Split a high-volume query into recursively-bisected follower windows.

    Probe-before-window (ADR-021): the `total_count` is the figure the 03a
    pagination loop already retrieved -- no extra probe call is issued. When
    `total_count <= PER_QUERY_CAP` the query needs no windowing, so a single
    non-windowed entry is returned.

    For `total_count > PER_QUERY_CAP` the query is re-issued as `followers:`
    -windowed sub-queries derived by recursive bisection from the initial
    bounded `followers:2..150` band plus the open-ended `followers:>150` band:
    a bounded `[lo..hi]` band still over the cap splits at `mid = (lo+hi)//2`
    into `[lo..mid]` + `[mid+1..hi]`; an open-ended `>=N` band splits into the
    bounded `[N..2N-1]` + the open-ended `>=2N`; a degenerate `lo == hi` band
    emits a width-1 `followers:N` window. Low bands are emitted first.

    Each window dict carries {query, lo, hi, open_ended, total_count, depth,
    unrecoverable}. `total_count` is the band's share of the parent's count
    (halved on each bisection) -- the per-window count probe-before-window
    keeps every final window's estimate at or below the cap.
    """
    if total_count <= PER_QUERY_CAP:
        return [{
            "query": query,
            "lo": MIN_FOLLOWERS,
            "hi": None,
            "open_ended": True,
            "total_count": total_count,
            "depth": 0,
            "unrecoverable": False,
            "windowed": False,
        }]

    windows: list[dict] = []
    # The two initial bands each carry, before any probe, an even share of the
    # parent total; bisection halves that share at every split.
    half = total_count / 2
    _bisect_band(query, MIN_FOLLOWERS, INITIAL_BAND_SPLIT, False, half, 1, windows)
    _bisect_band(query, INITIAL_BAND_SPLIT + 1, None, True, half, 1, windows)
    windows.sort(key=lambda w: w["lo"])
    return windows


def _bisect_band(query: str, lo: int, hi: int | None, open_ended: bool,
                 band_count: float, depth: int, windows: list[dict]) -> None:
    """Recursively bisect one follower band until its count is within the cap.

    A band whose estimated `band_count` is at or below `PER_QUERY_CAP` becomes a
    final window. The recursion terminates on three guards (ADR-021 Slice 03b):

    - **count guard** -- `band_count <= PER_QUERY_CAP`: the band is recoverable.
    - **width-1 guard** -- a degenerate `lo == hi` band cannot be split further;
      if its estimated count is still over the cap it is an ACCEPTED
      UNRECOVERABLE CAP -- the truncation is logged and the branch stops (no
      infinite recursion on a single follower count with >1000 developers).
    - **depth guard** -- `depth >= MAX_WINDOW_DEPTH=10`: the bisection recurses
      no deeper than the named cap; a band reaching it still over the per-query
      cap is likewise accepted as an unrecoverable cap and logged.

    A bounded band still over the cap splits at the midpoint; an open-ended band
    splits into a bounded `[N..2N-1]` plus an open-ended `>=2N`. Each split
    halves the estimated share and increments the depth, so the recursion always
    terminates -- by the count guard, the width-1 guard or the depth guard.
    """
    degenerate = hi is not None and lo == hi
    depth_capped = depth >= MAX_WINDOW_DEPTH
    over_cap = band_count > PER_QUERY_CAP
    if band_count <= PER_QUERY_CAP or degenerate or depth_capped:
        unrecoverable = over_cap and (degenerate or depth_capped)
        if unrecoverable:
            clause = _follower_clause(lo, hi)
            reason = ("width-1 band" if degenerate
                      else f"depth cap {MAX_WINDOW_DEPTH} reached")
            print(f"  [search] WARNING: unrecoverable follower window "
                  f"'{clause}' ({reason}): estimated total_count "
                  f"{int(round(band_count))} exceeds the {PER_QUERY_CAP}-result "
                  f"per-query cap -- truncating to the first {PER_QUERY_CAP} "
                  f"results")
        windows.append({
            "query": windowed_query(query, lo, hi),
            "lo": lo,
            "hi": hi,
            "open_ended": open_ended,
            "total_count": int(round(band_count)),
            "depth": depth,
            "unrecoverable": unrecoverable,
            "windowed": True,
        })
        return

    child_count = band_count / 2
    if open_ended:
        # open-ended `>=lo` -> bounded `[lo..2lo-1]` + open-ended `>=2lo`
        _bisect_band(query, lo, 2 * lo - 1, False, child_count, depth + 1, windows)
        _bisect_band(query, 2 * lo, None, True, child_count, depth + 1, windows)
        return
    mid = (lo + hi) // 2
    _bisect_band(query, lo, mid, False, child_count, depth + 1, windows)
    _bisect_band(query, mid + 1, hi, False, child_count, depth + 1, windows)


def _annotate_window_rank(items: list[dict]) -> None:
    """Tag each item with its 0-based position in this repo-sorted window.

    The windowed search returns each follower band repo-sorted but concatenates
    the bands follower-ascending, so a plain stable trim kept the lowest
    -follower devs and dropped the genuinely strongest (FINDINGS 2026-06-11).
    `windowRank` is the per-window quality position the trim uses to interleave
    the bands; it is recorded here at fetch time at zero API cost (a plain
    enumerate). For a non-windowed query the single repo-sorted result yields
    windowRank = global repo rank. Mutates each item in place.
    """
    for rank, item in enumerate(items):
        item["windowRank"] = rank


def run_search_windowed(query: str, per_page: int = 100,
                        sort: str | None = None,
                        budget: "SearchCallBudget | None" = None) -> list[dict]:
    """Execute a query, applying recursive-bisection follower-windowing.

    ADR-021 Slice 03b probe-before-window: the first per_page=100 call reports
    total_count -- that figure IS the windowing probe, so windowing adds no
    extra GitHub call on top of the pagination budget. When total_count is at
    or below the per-query cap the query is paginated normally by run_search
    (Slice 03a) -- it is NOT windowed. When total_count exceeds the cap the
    query is re-issued as recursively-bisected `followers:`-windowed
    sub-queries (low bands first); each window is itself wired through the
    run_search pagination loop. The throttle runs via time.sleep between
    windows.

    run_search is the unchanged Slice-03a pagination port; this is the Slice
    -03b windowing orchestration that sits above it.

    ADR-021 Slice 03b: when a `SearchCallBudget` is supplied, the probe call
    and every windowed sub-query draw from the SAME task-level budget; once it
    is spent windowing stops and the items retrieved so far are returned.
    """
    if budget is not None and not budget.consume():
        return []
    _first_items, total_count = _fetch_search_page(query, 1, per_page, sort)
    print(f"  [search] probe total_count={total_count} for query '{query}'")

    if total_count <= PER_QUERY_CAP:
        # Probe-before-window: at or below the cap -> no windowing. The probe
        # above already spent one budget unit and read page 1; paginate the
        # remaining pages from page 2 without re-charging that first page.
        items = _paginate_from_probe(query, _first_items, total_count,
                                     per_page, sort, budget)
        # Single repo-sorted result -> windowRank is the global repo rank.
        _annotate_window_rank(items)
        return items

    # Over the cap -> re-issue as recursive-bisection follower windows, low
    # bands first. Each windowed sub-query is paginated through run_search and
    # draws from the shared task-level budget.
    windowed_items: list[dict] = []
    for window in build_follower_windows(query, total_count):
        if budget is not None and budget.exhausted:
            break
        time.sleep(SEARCH_THROTTLE_SECONDS)
        window_items = run_search(window["query"], per_page=per_page,
                                  sort=sort, budget=budget)
        # Tag each band's items with their within-window repo rank BEFORE the
        # bands are concatenated, so the trim can interleave them (FINDINGS
        # 2026-06-11) instead of keeping this low-follower band's whole head.
        _annotate_window_rank(window_items)
        windowed_items.extend(window_items)
    return windowed_items


def _paginate_from_probe(query: str, first_items: list[dict],
                         total_count: int, per_page: int, sort: str | None,
                         budget: "SearchCallBudget | None") -> list[dict]:
    """Continue pagination from page 2 reusing the probe's page-1 result.

    The probe call in run_search_windowed already issued page 1 and (when a
    budget is supplied) charged one unit for it; this finishes the paginated
    read for an at-or-below-cap query without double-counting that first page.
    Pagination of pages 2..N is the same loop run_search uses.
    """
    return _paginate_remaining_pages(query, first_items, total_count,
                                     per_page, sort, budget)


def main():
    parser = argparse.ArgumentParser(description="GitHub user search")
    parser.add_argument("--task-id", required=True, help="Task ID")
    parser.add_argument("--strategies", required=True, help="Path to strategies JSON file")
    parser.add_argument("--max-results", type=int, default=25, help="Max developers to return")
    parser.add_argument("--exclude-logins", default="", help="Comma-separated logins to exclude (pass2)")
    parser.add_argument("--output-file", help="Override output file name")
    args = parser.parse_args()

    import pipeline_logger as plog
    plog.init(args.task_id)
    plog.start_timer("search")

    with open(args.strategies) as f:
        strategies = json.load(f)

    # Lowercased on BOTH sides: GitHub logins are case-insensitive, the GDPR exclusion list
    # stores them lowercase, and 171 of 707 indexed logins are not lowercase — comparing raw
    # would miss 24% of exclusions here and only catch them at the Convex write guard, after
    # the profile had already been fetched and scored.
    exclude = set(l.strip().lower() for l in args.exclude_logins.split(",") if l.strip())

    plog.log("search", f"Search started: {len(strategies)} strategies, max {args.max_results} results")
    print(f"[search] Running {len(strategies)} strategies, max {args.max_results} results, excluding {len(exclude)} logins")
    developers, search_stats = search_all(strategies, args.max_results, exclude)

    output_name = args.output_file or f"search-{args.task_id}.json"
    output = {
        "taskId": args.task_id,
        "totalSearchResults": search_stats["totalSearchResults"],
        "afterDedup": search_stats["afterDedup"],
        "finalCount": search_stats["finalCount"],
        "strategies_executed": len(strategies),
        "developers": developers,
    }

    out_path = OUTPUT_DIR / output_name
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    duration = plog.end_timer("search")
    plog.log("search", f"Search complete: {len(developers)} developers found",
             metadata={"duration_ms": duration, "output_count": len(developers),
                       "strategies": len(strategies)})
    print(f"[search] Wrote {len(developers)} developers to {out_path.name}")


if __name__ == "__main__":
    main()
