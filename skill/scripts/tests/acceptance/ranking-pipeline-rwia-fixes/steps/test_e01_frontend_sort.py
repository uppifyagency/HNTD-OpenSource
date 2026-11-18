"""
E-01: compositeScore must drive the frontend leaderboard sort.

RETIRED 2026-08-02. The three structural scenarios that lived here are gone; this file is kept
so the retirement is discoverable instead of looking like a silent deletion.

What they did: regex-matched the SOURCE TEXT of src/app/dashboard/tasks/[id]/page.tsx.
Scenarios 1 and 2 asserted the PRESENCE of an inline comparator (`effectiveSortBy ===
"normalized"` and the literal chain `a?.compositeScore ?? a?.normalizedScore ?? a?.score ?? 0`);
scenario 3 asserted the ABSENCE of a hardcoded `sortBy="normalizedScore"`.

Why 1 and 2 had to go: the editorial migration moved that comparator into
src/lib/taskResults/taskResultsViewModel.ts. The tests then looked for code in a file that no
longer contains it, so they failed on a healthy tree — and because verify.sh runs with `set -e`
they aborted the whole gate before vitest and the build ever ran. Authored 2026-04-12, red from
the editorial migration until 2026-08-02. A test that pins the SHAPE of a source file cannot
survive a refactor of that file, and this one did not: it went red for the one reason that is
never a defect.

Where the intent lives now — as BEHAVIOUR, in
src/lib/taskResults/__tests__/taskResultsViewModel.test.ts:
  - "normalized mode consults compositeScore before normalizedScore"     (scenario 1)
  - "normalized mode falls back compositeScore -> normalizedScore -> score for legacy rows"
                                                                          (scenario 2)
Those two were verified to DISCRIMINATE: reverting the fix kills 5 of the 21 assertions there,
whereas the regex versions passed against the sort/display divergence (finding #8) for the whole
four months they existed, because they only ever checked which characters were present.

Scenario 3 was still GREEN when retired, and its coverage is NOT reproduced by an equivalent
assertion — an honest gap, not a substitution. It asserted something about the CALL SITE (that
page.tsx passes a non-hardcoded value); the vitest suite asserts the CONTENT of the
EXPORT_SORT_KEY constant, which is a different claim. What replaces it is stronger but
structural rather than behavioural: `ResultRow` no longer carries the per-signal fields a caller
would need to re-derive its own headline, and `ExportButtons.sortBy` is typed as `ExportSortKey`,
so re-introducing either the hardcoded value or a re-derived headline is a TypeScript error that
`npm run build` rejects. That guard was verified by re-applying both original defects: the build
fails with "Property 'normalizedScore' does not exist on type 'ResultRow'".
"""


def test_e01_scenarios_retired_see_module_docstring():
    """Keeps pytest from exiting 5 (no tests collected) if this file is ever run alone.

    Under `set -e` in verify.sh an exit-5 would abort the gate — the same failure mode the
    retired tests caused, which is a poor way to commemorate them.
    """
    assert __doc__ and "RETIRED 2026-08-02" in __doc__
