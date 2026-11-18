"""
Deterministic search strategy builder for manual mode.

Produces the same {query, priority, rationale} format as jd-parse,
using the location alias map from search-strategies.md.

Usage:
    python build_strategies.py --task-id <ID> --languages python --locations italy
    python build_strategies.py --task-id <ID> --languages python java --locations vercelli --keywords django --min-followers 0
"""
import argparse
import json
import os
import sys

# Location alias map — sourced from skill/github-hr/references/search-strategies.md
#
# ADR-022 BLK-4 restructure: each country maps to
#     {"country_names": [<English + local spellings>],
#      "cities": [[<spelling-variant group>], ...]}
# A city-group bundles every spelling of one canonical city (e.g.
# ["naples", "napoli"]) so classify_tier can decide deterministically whether
# a query location is a spelling of the *requested* city or of a different
# one. The cities[] ORDER is load-bearing: classify_tier ranks cities[0:2] as
# major_city and cities[2:] as extended_city (ADR-022 BLK-NEW-1, N=2). Every
# city present in the pre-restructure flat map is preserved here as a group.
LOCATION_ALIASES = {
    "italy": {
        "country_names": ["italy", "italia"],
        "cities": [
            ["rome", "roma"],
            ["milan", "milano"],
            ["turin", "torino"],
            ["naples", "napoli"],
            ["florence", "firenze"],
            ["bologna"],
            ["venice", "venezia"],
            ["genoa", "genova"],
            ["palermo"],
            ["bari"],
            ["catania"],
        ],
    },
    "germany": {
        "country_names": ["germany", "deutschland"],
        "cities": [
            ["berlin"],
            ["munich", "münchen", "munchen"],
            ["hamburg"],
            ["frankfurt"],
            ["cologne", "köln", "koln"],
            ["stuttgart"],
            ["düsseldorf", "dusseldorf"],
        ],
    },
    "france": {
        "country_names": ["france"],
        "cities": [
            ["paris"],
            ["lyon"],
            ["marseille"],
            ["toulouse"],
            ["nice"],
            ["nantes"],
            ["strasbourg"],
            ["bordeaux"],
            ["lille"],
        ],
    },
    "spain": {
        "country_names": ["spain", "españa", "espana"],
        "cities": [
            ["madrid"],
            ["barcelona"],
            ["valencia"],
            ["seville", "sevilla"],
            ["bilbao"],
            ["malaga"],
        ],
    },
    "uk": {
        "country_names": ["uk", "united kingdom", "england"],
        "cities": [
            ["london"],
            ["manchester"],
            ["birmingham"],
            ["leeds"],
            ["glasgow"],
            ["edinburgh"],
            ["bristol"],
            ["liverpool"],
        ],
    },
    "netherlands": {
        "country_names": ["netherlands", "holland"],
        "cities": [
            ["amsterdam"],
            ["rotterdam"],
            ["the hague", "den haag"],
            ["utrecht"],
            ["eindhoven"],
        ],
    },
    "portugal": {
        "country_names": ["portugal"],
        "cities": [
            ["lisbon", "lisboa"],
            ["porto"],
        ],
    },
    "poland": {
        "country_names": ["poland", "polska"],
        "cities": [
            ["warsaw", "warszawa"],
            ["krakow", "kraków"],
            ["wroclaw", "wrocław"],
            ["gdansk", "gdańsk"],
        ],
    },
    "switzerland": {
        "country_names": ["switzerland", "schweiz", "suisse", "svizzera"],
        "cities": [
            ["zurich", "zürich"],
            ["geneva", "genève"],
            ["bern"],
            ["basel"],
        ],
    },
}

# GitHub Linguist language map — resolves recruiter terms to valid search queries.
# Terms not in this map are treated as keywords.
GITHUB_LANGUAGE_MAP = {
    # Actual languages (pass through)
    "python": {"languages": ["python"], "keywords": []},
    "javascript": {"languages": ["javascript"], "keywords": []},
    "typescript": {"languages": ["typescript"], "keywords": []},
    "java": {"languages": ["java"], "keywords": []},
    "go": {"languages": ["go"], "keywords": []},
    "ruby": {"languages": ["ruby"], "keywords": []},
    "rust": {"languages": ["rust"], "keywords": []},
    "c#": {"languages": ["c#"], "keywords": []},
    "csharp": {"languages": ["c#"], "keywords": []},
    "php": {"languages": ["php"], "keywords": []},
    "scala": {"languages": ["scala"], "keywords": []},
    "kotlin": {"languages": ["kotlin"], "keywords": []},
    "swift": {"languages": ["swift"], "keywords": []},
    "dart": {"languages": ["dart"], "keywords": []},
    "c++": {"languages": ["c++"], "keywords": []},
    "c": {"languages": ["c"], "keywords": []},
    "elixir": {"languages": ["elixir"], "keywords": []},
    "r": {"languages": ["r"], "keywords": []},
    "shell": {"languages": ["shell"], "keywords": []},
    "vue": {"languages": ["vue"], "keywords": []},
    # Frameworks / tools → map to real languages + keywords
    "docker": {"languages": ["dockerfile"], "keywords": ["docker"]},
    "dockerfile": {"languages": ["dockerfile"], "keywords": ["docker"]},
    "kubernetes": {"languages": ["go", "shell"], "keywords": ["kubernetes", "k8s"]},
    "k8s": {"languages": ["go", "shell"], "keywords": ["kubernetes", "k8s"]},
    "terraform": {"languages": ["hcl"], "keywords": ["terraform"]},
    "ansible": {"languages": ["python", "shell"], "keywords": ["ansible"]},
    "react": {"languages": ["javascript", "typescript"], "keywords": ["react"]},
    "react native": {"languages": ["javascript", "typescript"], "keywords": ["react-native"]},
    "angular": {"languages": ["typescript"], "keywords": ["angular"]},
    "vue.js": {"languages": ["vue", "javascript", "typescript"], "keywords": ["vue"]},
    "node.js": {"languages": ["javascript", "typescript"], "keywords": ["nodejs"]},
    "node": {"languages": ["javascript", "typescript"], "keywords": ["nodejs"]},
    "nodejs": {"languages": ["javascript", "typescript"], "keywords": ["nodejs"]},
    "spring boot": {"languages": ["java", "kotlin"], "keywords": ["spring-boot"]},
    "spring": {"languages": ["java", "kotlin"], "keywords": ["spring"]},
    "django": {"languages": ["python"], "keywords": ["django"]},
    "flask": {"languages": ["python"], "keywords": ["flask"]},
    ".net": {"languages": ["c#"], "keywords": ["dotnet", ".net"]},
    "dotnet": {"languages": ["c#"], "keywords": ["dotnet"]},
    "ios": {"languages": ["swift", "objective-c"], "keywords": ["ios"]},
    "android": {"languages": ["kotlin", "java"], "keywords": ["android"]},
    "machine learning": {"languages": ["python"], "keywords": ["machine-learning"]},
    "ml": {"languages": ["python"], "keywords": ["machine-learning", "ml"]},
    "ai": {"languages": ["python"], "keywords": ["ai", "machine-learning"]},
    "data science": {"languages": ["python", "r"], "keywords": ["data-science"]},
    "aws": {"languages": ["python", "hcl"], "keywords": ["aws"]},
    "devops": {"languages": ["dockerfile", "hcl", "shell"], "keywords": ["devops"]},
    "flutter": {"languages": ["dart"], "keywords": ["flutter"]},
}


# ADR-022 BLK-NEW-1: non-requested city-group boundary. Index < this value in
# a country's cities[] list -> major_city; index >= it -> extended_city.
# N=2 is the worked-example boundary (Italy: rome,milan major; rest extended).
# A wrong N (e.g. 4) is an off-by-one trap an enum-only test cannot catch.
MAJOR_CITY_BOUNDARY = 2

# ADR-020 5-tier model: priority integer (1=highest) <-> priorityTier enum.
# build_strategies emits priorityTier on every strategy; classify_tier derives
# the tier from the location at generation time and the result is consistent
# with this mapping (the priority block already fixes which tier applies).
PRIORITY_TO_TIER = {1: "exact_city", 2: "country", 3: "major_city",
                    4: "extended_city", 5: "keyword"}


def sanitize_languages(raw_languages: list[str], raw_keywords: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Sanitize language input: split combined strings, reclassify non-languages as keywords.

    Returns (valid_languages, merged_keywords).
    """
    import re
    keywords = list(raw_keywords or [])
    valid_languages = []

    for raw in raw_languages:
        # Split on 'and', commas, semicolons, plus signs
        parts = re.split(r'\s+and\s+|,|;|\+', raw, flags=re.IGNORECASE)
        for part in parts:
            term = part.strip().lower()
            if not term:
                continue
            mapping = GITHUB_LANGUAGE_MAP.get(term)
            if mapping:
                valid_languages.extend(mapping["languages"])
                keywords.extend(mapping["keywords"])
                if mapping["keywords"]:
                    print(f"  [strategies] Resolved '{term}' -> languages={mapping['languages']}, keywords={mapping['keywords']}")
            else:
                # Unknown term — treat as keyword
                keywords.append(term)
                print(f"  [strategies] Unknown term '{term}' moved to keywords")

    # Deduplicate
    valid_languages = list(dict.fromkeys(valid_languages))
    keywords = list(dict.fromkeys(keywords))
    return valid_languages, keywords


def _location_query(language: str, location: str, min_followers: int) -> str:
    """Render a `language:.. location:.. followers:>=..` GitHub search query."""
    return f"language:{language} location:{location} followers:>={min_followers}"


def _keyword_query(keyword: str, language: str, min_followers: int) -> str:
    """Render a quoted-keyword `"kw" language:.. followers:>=..` search query."""
    return f'"{keyword}" language:{language} followers:>={min_followers}'


def _emit_city_groups(strategies, seen_queries, city_groups, lang, lang_lower,
                      min_followers, priority, tier_label, tier_for,
                      skip_group=None):
    """Emit one strategy per spelling variant across a list of city-groups.

    `city_groups` is a slice of a country's cities[][] (cities[0:2] for the P3
    major-city band, cities[2:] for the P4 extended-city band). For every city
    in every group a `location:` strategy is added at `priority` with the
    `tier_label` rationale prefix; `tier_for(city)` derives its priorityTier.
    `skip_group` (the requested city's group) is skipped so a major/extended
    slot never re-emits the exact-city target. The query uses the lower-cased
    language, the rationale the recruiter's original casing -- matching the
    pre-extraction behaviour exactly.
    """
    for group in city_groups:
        if skip_group is not None and group is skip_group:
            continue
        for alias_city in group:
            _add(strategies, seen_queries,
                 query=_location_query(lang_lower, alias_city, min_followers),
                 priority=priority,
                 rationale=f"{tier_label}: {lang} + {alias_city}",
                 priority_tier=tier_for(alias_city))


def build_strategies(
    languages: list[str],
    locations: list[str],
    keywords: list[str] | None = None,
    min_followers: int = 2,
    country: str | None = None,
    city: str | None = None,
) -> list[dict]:
    """Build search strategies from manual mode params.

    Returns list of {query, priority, rationale} dicts, sorted by priority ASC.

    When `country` is provided it takes precedence over `locations` and uses
    structured geo-expansion (ADR-022 city-group LOCATION_ALIASES):
      P1 – exact city (if `city` is given)
      P2 – country names (English + local spellings)
      P3 – major cities (cities[0:2])
      P4 – extended cities (cities[2:])
      P5 – keywords (no location)
    """
    # Sanitize: resolve non-language terms, split combined strings
    languages, keywords_merged = sanitize_languages(languages, keywords)
    keywords = keywords_merged

    strategies = []
    seen_queries = set()

    if country:
        country_lower = country.lower()
        # ADR-022 city-group structure: country_names + cities[][]. An unknown
        # country yields an empty entry so the loops below simply produce no
        # geo-expansion (the raw country name is still emitted at P2).
        entry = LOCATION_ALIASES.get(country_lower)
        country_names = entry["country_names"] if entry else [country_lower]
        cities = entry["cities"] if entry else []

        for lang in languages:
            lang_lower = lang.lower()

            # P1: exact city (split comma-separated cities into individual queries)
            if city:
                for single_city in [c.strip() for c in city.split(",")]:
                    city_lower = single_city.lower()
                    _add(strategies, seen_queries,
                         query=_location_query(lang_lower, city_lower, min_followers),
                         priority=1,
                         rationale=f"Exact city: {lang} + {city_lower}",
                         priority_tier=classify_tier(city_lower, city, country))

            # P2: country names (English + local spellings) -- old country_lower
            # plus old aliases[0] are both members of country_names now.
            for country_name in country_names:
                _add(strategies, seen_queries,
                     query=_location_query(lang_lower, country_name, min_followers),
                     priority=2,
                     rationale=f"Country: {lang} + {country_name}",
                     priority_tier=classify_tier(country_name, city, country))

            # The requested city's spelling-variant group is already covered
            # at P1 (exact_city). Skip it in the P3/P4 loops so no major/
            # extended slot re-emits the requested city -- that would emit a
            # priorityTier ("exact_city" from classify_tier) inconsistent with
            # the P3/P4 priority number (ADR-022 BLK-NEW-1 + ADR-020).
            requested_group = _requested_city_group(city, entry)
            classify = lambda loc: classify_tier(loc, city, country)

            # P3: major cities -- cities[0:2] (old aliases[1:5] slice).
            _emit_city_groups(strategies, seen_queries,
                              cities[0:MAJOR_CITY_BOUNDARY], lang, lang_lower,
                              min_followers, 3, "Major city", classify,
                              skip_group=requested_group)

            # P4: extended cities -- cities[2:] (old aliases[5:] slice).
            _emit_city_groups(strategies, seen_queries,
                              cities[MAJOR_CITY_BOUNDARY:], lang, lang_lower,
                              min_followers, 4, "Extended city", classify,
                              skip_group=requested_group)

            # P5: keywords -- non-locational, always the keyword tier.
            for kw in keywords:
                _add(strategies, seen_queries,
                     query=_keyword_query(kw, lang_lower, min_followers),
                     priority=5,
                     rationale=f"Keyword match: {lang} + {kw}",
                     priority_tier=PRIORITY_TO_TIER[5])

        strategies.sort(key=lambda s: s["priority"])
        return strategies

    for lang in languages:
        lang_lower = lang.lower()

        for loc in locations:
            loc_lower = loc.lower()

            # P1: Direct match — the exact location the recruiter typed.
            # The typed location IS the recruiter's exact target, so it takes
            # the exact_city tier (priority slot 1). The legacy locations path
            # carries no requested-city context for classify_tier, so the
            # priorityTier is derived from the priority slot via the canonical
            # PRIORITY_TO_TIER mapping (ADR-020) -- keeping every strategy's
            # priorityTier consistent with its priority.
            _add(strategies, seen_queries,
                 query=_location_query(lang_lower, loc_lower, min_followers),
                 priority=1,
                 rationale=f"Direct match: {lang} + {loc}",
                 priority_tier=PRIORITY_TO_TIER[1])

            # Expand aliases if this is a known country key (ADR-022 city-group
            # structure). Unknown loc -> no entry -> no expansion (raw P1 only).
            entry = LOCATION_ALIASES.get(loc_lower)
            country_names = entry["country_names"] if entry else []
            cities = entry["cities"] if entry else []

            # P2: Other country-name spellings (e.g. "italia" for "italy").
            # The typed loc is already emitted at P1, so skip it here.
            for country_name in country_names:
                if country_name == loc_lower:
                    continue
                _add(strategies, seen_queries,
                     query=_location_query(lang_lower, country_name, min_followers),
                     priority=2,
                     rationale=f"Local spelling: {lang} + {country_name}",
                     priority_tier=PRIORITY_TO_TIER[2])

            # P3/P4: major + extended city expansion. The legacy locations path
            # carries no requested-city context, so priorityTier is the fixed
            # PRIORITY_TO_TIER slot for the priority band (ADR-020).
            _emit_city_groups(strategies, seen_queries,
                              cities[0:MAJOR_CITY_BOUNDARY], lang, lang_lower,
                              min_followers, 3, "Major city",
                              lambda _: PRIORITY_TO_TIER[3])
            _emit_city_groups(strategies, seen_queries,
                              cities[MAJOR_CITY_BOUNDARY:], lang, lang_lower,
                              min_followers, 4, "Extended city",
                              lambda _: PRIORITY_TO_TIER[4])

        # P5: Keyword strategies (language + keyword, no location — widens the net)
        for kw in keywords:
            _add(strategies, seen_queries,
                 query=_keyword_query(kw, lang_lower, min_followers),
                 priority=5,
                 rationale=f"Keyword match: {lang} + {kw}",
                 priority_tier=PRIORITY_TO_TIER[5])

    strategies.sort(key=lambda s: s["priority"])
    return strategies


# --- ADR-022: shared 5-tier location classifier -----------------------------
# Lives inside build_strategies.py per ADR-022 (no separate strategy_tiers.py:
# there is no circular-import constraint forcing one). build_strategies and
# the jd-parser contract mirror (step 02-02) both call this single function.
# MAJOR_CITY_BOUNDARY and PRIORITY_TO_TIER are defined as named module
# constants near the top of this file.


def classify_tier(query_location, requested_city, requested_country):
    """Map a location to a priorityTier enum (ADR-022 5-step rule).

    Returns one of: exact_city | country | major_city | extended_city | keyword.

    The 5-step rule, evaluated in order:
      1. query_location is a spelling of the requested city  -> "exact_city"
      2. query_location is a spelling of the requested country-> "country"
      3. query_location is a city-group at cities[0:2]        -> "major_city"
      4. query_location is a city-group at cities[2:]         -> "extended_city"
      5. query_location matches nothing locational            -> "keyword"

    Spelling is irrelevant: any variant within a city-group (or country_names)
    resolves identically. `requested_city` is explicit so the exact_city vs
    major_city decision is deterministic.
    """
    location = (query_location or "").strip().lower()
    country_key = (requested_country or "").strip().lower()
    entry = LOCATION_ALIASES.get(country_key)

    # Step 1: any spelling of the requested city -> exact_city. Resolve the
    # requested city to its spelling-variant group, then test membership.
    requested_group = _requested_city_group(requested_city, entry)
    if requested_group is not None and location in requested_group:
        return "exact_city"

    if entry is None:
        return "keyword"

    # Step 2: any spelling of the requested country -> country.
    if location in entry["country_names"]:
        return "country"

    # Steps 3 & 4: a non-requested city-group. Its index in cities[] decides
    # major (cities[0:2]) vs extended (cities[2:]) -- ADR-022 BLK-NEW-1.
    for index, group in enumerate(entry["cities"]):
        if location in group:
            if index < MAJOR_CITY_BOUNDARY:
                return "major_city"
            return "extended_city"

    # Step 5: nothing locational matched.
    return "keyword"


def _requested_city_group(requested_city, entry):
    """Return the spelling-variant group of the requested city, or None.

    Matches the recruiter's requested_city -- in ANY spelling -- against the
    country's city-groups so that exact_city detection is spelling-agnostic.
    """
    if not requested_city or entry is None:
        return None
    requested = requested_city.strip().lower()
    for group in entry["cities"]:
        if requested in group:
            return group
    return None


def _add(strategies, seen, query, priority, rationale, priority_tier):
    """Add strategy if query is not a duplicate.

    ADR-020 / ADR-022: every emitted strategy carries a required priorityTier
    string -- the canonical trim key derived by classify_tier at generation
    time. priorityTier is consistent with priority via PRIORITY_TO_TIER
    (1->exact_city .. 5->keyword).
    """
    if query not in seen:
        seen.add(query)
        strategies.append({
            "query": query,
            "priority": priority,
            "rationale": rationale,
            "priorityTier": priority_tier,
        })


def main():
    parser = argparse.ArgumentParser(description="Build search strategies for manual mode")
    parser.add_argument("--task-id", required=True, help="Convex task ID")
    parser.add_argument("--languages", nargs="+", required=True)
    parser.add_argument("--locations", nargs="*", default=[])
    parser.add_argument("--keywords", nargs="*", default=[])
    parser.add_argument("--min-followers", type=int, default=2)
    parser.add_argument("--country", default=None,
                        help="Country for structured geo-expansion (takes precedence over --locations)")
    parser.add_argument("--city", default=None,
                        help="Specific city within the country (produces P1 exact-city strategy)")
    parser.add_argument("--output-dir", default=os.path.join(
        os.path.dirname(__file__), "..", "output"))
    args = parser.parse_args()

    import pipeline_logger as plog
    plog.init(args.task_id)
    plog.start_timer("strategies")

    strategies = build_strategies(
        languages=args.languages,
        locations=args.locations,
        keywords=args.keywords,
        min_followers=args.min_followers,
        country=args.country,
        city=args.city,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f"strategies-{args.task_id}.json")
    with open(out_path, "w") as f:
        json.dump(strategies, f, indent=2)

    duration = plog.end_timer("strategies")
    plog.log("strategies", f"Generated {len(strategies)} strategies for {args.languages}",
             metadata={"duration_ms": duration, "count": len(strategies),
                       "languages": args.languages, "locations": args.locations})

    print(f"Generated {len(strategies)} strategies -> {out_path}")
    for s in strategies:
        print(f"  P{s['priority']}: {s['query']}")

    return strategies


if __name__ == "__main__":
    main()
