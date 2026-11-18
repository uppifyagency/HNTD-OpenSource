"""
E-04: Kotlin mobile classification guarded by backend co-occurrence.

Driving port: push_results.derive_category() — pure function, its signature IS the port.
Observable outcome: return value of derive_category for each topLanguages input.

Bug reference: E-04 — Kotlin is intentionally in BOTH backend and mobile CATEGORY_MAP sets
(Kotlin/JVM server vs Kotlin Android). The mobile check fires unconditionally, so any
developer with Kotlin in topLanguages is classified as "mobile" even when co-occurring
with explicit backend languages like Go or Java.

Fix: introduce mobile-exclusive set {Swift, Dart} checked BEFORE backend logic (strong
mobile signal wins), and guard the mobile fallback with `not has_backend` so pure Kotlin
and backend+Kotlin combinations classify as backend.

Root cause: docs/analysis/root-cause-analysis-all-findings.md#e-04
User decision: pure Kotlin → "backend" (option 1 accepted).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


@pytest.mark.parametrize(
    "top_languages,expected_category",
    [
        # Backend co-occurrence → backend (Kotlin is a JVM server language here)
        (["Go", "Kotlin"], "backend"),
        (["Java", "Kotlin"], "backend"),
        # Pure Kotlin — no disambiguating signal, user accepted tradeoff → backend
        (["Kotlin"], "backend"),
        # Mobile-exclusive language co-occurs → mobile (Kotlin is Android here)
        (["Swift", "Kotlin"], "mobile"),
        (["Dart", "Kotlin"], "mobile"),
    ],
    ids=[
        "go-kotlin-is-backend",
        "java-kotlin-is-backend",
        "pure-kotlin-is-backend",
        "swift-kotlin-is-mobile",
        "dart-kotlin-is-mobile",
    ],
)
def test_derive_category_kotlin_context_aware(top_languages, expected_category):
    """derive_category classifies Kotlin by the company it keeps.

    Given topLanguages containing Kotlin plus a disambiguating signal
    When derive_category is called
    Then it returns the category implied by the co-occurring language
    """
    from push_results import derive_category

    result = derive_category(top_languages)

    assert result == expected_category, (
        f"derive_category({top_languages}) = {result!r}, "
        f"expected {expected_category!r} (E-04)"
    )
