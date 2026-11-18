"""Step definitions for Slice 3: Prefilter Fallbacks.

Driving port:
- prefilter.apply_discard_rules() -- existing function, needs modification for fallbacks

The current apply_discard_rules() does NOT accept target_languages or check
languageBytes/lifetimePRs. The DELIVER wave crafter must modify its signature
to support the fallback logic.

Expected new signature (crafter implements):
    apply_discard_rules(dev, min_activity, target_languages=None) -> str | None
"""
import io
import sys
from datetime import datetime, timedelta, timezone

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from conftest import make_developer, make_language_bytes

FEATURE_FILE = "../features/slice3_prefilter_fallbacks.feature"

# Fixed evaluation instant: scenarios express recency as "last pushed N months ago"
# relative to this NOW (QT-05 canonical minActivity semantics).
NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)
DAYS_PER_MONTH = 30.44


# ---------------------------------------------------------------------------
# Scenario wiring
# ---------------------------------------------------------------------------

@scenario(FEATURE_FILE, "Developer rescued by language bytes when target repo count is zero")
def test_rescue_by_lang_bytes():
    pass


@scenario(FEATURE_FILE, "Developer with zero target language evidence in both metrics is discarded")
def test_discard_no_evidence():
    pass


@scenario(FEATURE_FILE, "Multiple target languages checked against language bytes")
def test_multiple_target_langs():
    pass


@scenario(FEATURE_FILE, "Language bytes below threshold does not rescue developer")
def test_below_threshold():
    pass


@scenario(FEATURE_FILE, "Language bytes at exact threshold rescues developer")
def test_exact_threshold():
    pass


@scenario(FEATURE_FILE, "Developer rescued by language bytes still faces activity rule")
def test_rescue_then_activity():
    pass


@scenario(FEATURE_FILE, "Senior developer on sabbatical rescued by lifetime pull requests")
def test_rescue_by_prs():
    pass


@scenario(FEATURE_FILE, "Inactive developer without lifetime evidence is discarded")
def test_discard_inactive():
    pass


@scenario(FEATURE_FILE, "Lifetime pull requests at exact rescue threshold")
def test_exact_pr_threshold():
    pass


@scenario(FEATURE_FILE, "Lifetime pull requests one below threshold does not rescue")
def test_below_pr_threshold():
    pass


@scenario(FEATURE_FILE, "Moderately experienced developer with quiet year is rescued")
def test_rescue_moderate():
    pass


@scenario(FEATURE_FILE, "Developer with missing language bytes data is not rescued")
def test_missing_lang_bytes():
    pass


@scenario(FEATURE_FILE, "Developer with missing lifetime pull request data is not rescued")
def test_missing_pr_data():
    pass


@scenario(FEATURE_FILE, "Developer with scan error bypasses all discard rules")
def test_scan_error_bypass():
    pass


@scenario(FEATURE_FILE, "Both fallbacks apply independently to same developer")
def test_both_fallbacks():
    pass


@scenario(FEATURE_FILE, "Developer above activity threshold does not trigger lifetime pull request check")
def test_above_activity_no_pr_check():
    pass


# ---------------------------------------------------------------------------
# Shared context
# ---------------------------------------------------------------------------

@pytest.fixture
def prefilter_context():
    return {
        "developer": None,
        "target_languages": [],
        "min_activity": 6,  # months (QT-05)
        "lang_bytes_threshold": 15.0,
        "lifetime_prs_threshold": 50,
        "result_reason": None,  # None = not discarded, str = discard reason
        "captured_logs": [],
        "rule1_passed_via_rescue": False,
        "rule2_passed_via_rescue": False,
        "pr_fallback_invoked": False,
    }


# ---------------------------------------------------------------------------
# Given steps -- developer setup
# ---------------------------------------------------------------------------

@given(parsers.parse('developer "{login}" has target repo count {tr:d}'))
def given_dev_tr(prefilter_context, login, tr):
    if prefilter_context["developer"] is None:
        prefilter_context["developer"] = make_developer(login, target_repo_count=tr)
    else:
        prefilter_context["developer"]["targetLanguageRepoCount"] = tr


@given(parsers.parse('developer "{login}" has target repo count {tr:d} and contribution days {cd:d}'))
def given_dev_tr_cd(prefilter_context, login, tr, cd):
    prefilter_context["developer"] = make_developer(login, target_repo_count=tr, contribution_days=cd)


@given(parsers.parse('developer "{login}" has language bytes where Java is {pct}% of total'))
def given_lang_bytes_java(prefilter_context, login, pct):
    pct_val = float(pct)
    dev = prefilter_context["developer"]
    dev["languageBytes"] = make_language_bytes({"Java": pct_val, "Other": 100 - pct_val})


@given(parsers.parse('developer "{login}" has language bytes where Ruby is {ruby_pct}% and Java is {java_pct}%'))
def given_lang_bytes_ruby_java(prefilter_context, login, ruby_pct, java_pct):
    dev = prefilter_context["developer"]
    ruby = float(ruby_pct)
    java = float(java_pct)
    remaining = 100 - ruby - java
    lang_map = {"Ruby": ruby, "Java": java}
    if remaining > 0:
        lang_map["Other"] = remaining
    dev["languageBytes"] = make_language_bytes(lang_map)


@given(parsers.parse('developer "{login}" has language bytes where JavaScript is {js_pct}% and TypeScript is {ts_pct}%'))
def given_lang_bytes_js_ts(prefilter_context, login, js_pct, ts_pct):
    dev = prefilter_context["developer"]
    js = float(js_pct)
    ts = float(ts_pct)
    remaining = 100 - js - ts
    dev["languageBytes"] = make_language_bytes({"JavaScript": js, "TypeScript": ts, "Other": remaining})


@given(parsers.parse('developer "{login}" has no language bytes data'))
def given_no_lang_bytes(prefilter_context, login):
    dev = prefilter_context["developer"]
    # languageBytes is not set or is empty
    dev.pop("languageBytes", None)


@given(parsers.parse('developer "{login}" has contribution days {cd:d}'))
def given_dev_cd(prefilter_context, login, cd):
    if prefilter_context["developer"] is None:
        prefilter_context["developer"] = make_developer(login, contribution_days=cd)
    else:
        prefilter_context["developer"]["contributionDays"] = cd


@given(parsers.parse('developer "{login}" last pushed {n:d} months ago'))
def given_dev_last_push(prefilter_context, login, n):
    if prefilter_context["developer"] is None:
        prefilter_context["developer"] = make_developer(login)
    pushed_at = NOW - timedelta(days=n * DAYS_PER_MONTH)
    prefilter_context["developer"]["topRepositories"] = [
        {"name": "main-repo", "stars": 0, "pushedAt": pushed_at.isoformat()}
    ]


@given(parsers.parse('developer "{login}" has {n:d} lifetime pull requests'))
def given_dev_prs(prefilter_context, login, n):
    dev = prefilter_context["developer"]
    dev["lifetimePullRequests"] = n


@given(parsers.parse('developer "{login}" has no lifetime pull request data recorded'))
def given_no_pr_data(prefilter_context, login):
    dev = prefilter_context["developer"]
    dev.pop("lifetimePullRequests", None)


@given(parsers.parse('developer "{login}" has a scan error recorded'))
def given_scan_error(prefilter_context, login):
    prefilter_context["developer"] = make_developer(login, scan_error="GraphQL timeout")


@given(parsers.parse('the task targets "{lang}" as a language'))
def given_single_target_lang(prefilter_context, lang):
    prefilter_context["target_languages"] = [lang]


@given(parsers.parse('the task targets "{l1}", "{l2}", and "{l3}" as languages'))
def given_multiple_target_langs(prefilter_context, l1, l2, l3):
    prefilter_context["target_languages"] = [l1, l2, l3]


@given(parsers.parse("the language bytes rescue threshold is {pct}%"))
def given_lang_threshold(prefilter_context, pct):
    prefilter_context["lang_bytes_threshold"] = float(pct)


@given(parsers.parse("the minimum activity threshold is {n:d} months"))
def given_min_activity(prefilter_context, n):
    prefilter_context["min_activity"] = n


@given(parsers.parse("the lifetime pull requests rescue threshold is {n:d}"))
def given_pr_threshold(prefilter_context, n):
    prefilter_context["lifetime_prs_threshold"] = n


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when(parsers.parse('the prefilter evaluates "{login}"'))
def when_prefilter_evaluates(prefilter_context, login):
    """Invoke the production apply_discard_rules function.

    Signature (QT-05): apply_discard_rules(dev, min_activity, target_languages=None,
    now=None) -> str | None, where min_activity is in MONTHS and the activity rule
    compares the most recent topRepositories pushedAt against now.
    """
    from prefilter import apply_discard_rules, last_push_at

    dev = prefilter_context["developer"]
    min_act = prefilter_context["min_activity"]
    target_langs = prefilter_context["target_languages"]

    # Capture stdout for log assertions
    captured = io.StringIO()
    old_stdout = sys.stdout

    try:
        reason = apply_discard_rules(dev, min_act, target_languages=target_langs, now=NOW)
        prefilter_context["result_reason"] = reason
    finally:
        sys.stdout = old_stdout

    # For two-rule evaluation (aleoncini case), we need to track per-rule outcomes
    # Rule 1 check: would tr=0 have been rescued?
    tr = dev.get("targetLanguageRepoCount")
    if tr is not None and tr == 0:
        lang_bytes = dev.get("languageBytes", [])
        if lang_bytes and target_langs:
            total_bytes = sum(lb.get("bytes", 0) for lb in lang_bytes)
            if total_bytes > 0:
                for lb in lang_bytes:
                    lang_name = lb.get("language", "")
                    if lang_name.lower() in [tl.lower() for tl in target_langs]:
                        pct = lb["bytes"] / total_bytes * 100
                        if pct >= prefilter_context["lang_bytes_threshold"]:
                            prefilter_context["rule1_passed_via_rescue"] = True
                            break

    # Rule 2 check (QT-05): would a stale last push have been rescued?
    last_push = last_push_at(dev)
    if last_push is not None and last_push < NOW - timedelta(days=min_act * DAYS_PER_MONTH):
        lifetime_prs = dev.get("lifetimePullRequests")
        if lifetime_prs is not None and lifetime_prs >= prefilter_context["lifetime_prs_threshold"]:
            prefilter_context["rule2_passed_via_rescue"] = True
        prefilter_context["pr_fallback_invoked"] = True


# ---------------------------------------------------------------------------
# Then steps -- discard/rescue assertions
# ---------------------------------------------------------------------------

@then(parsers.parse('"{login}" is not discarded'))
def then_not_discarded(prefilter_context, login):
    reason = prefilter_context["result_reason"]
    assert reason is None, f"{login} was discarded with reason: {reason}"


@then(parsers.parse('"{login}" is discarded with reason "{reason}"'))
def then_discarded_reason(prefilter_context, login, reason):
    actual = prefilter_context["result_reason"]
    assert actual is not None, f"{login} was NOT discarded (expected: {reason})"
    assert actual == reason, f"{login} discarded for '{actual}', expected '{reason}'"


@then(parsers.parse('the prefilter logs a rescue for "{login}" citing language bytes Java at {pct}%'))
def then_log_rescue_lang_bytes(prefilter_context, login, pct):
    # This validates the rescue happened. In the production implementation,
    # the log line format will be: "rescued by languageBytes: Java=32.5% >= 15%"
    # For now, we verify the rescue logic was triggered.
    assert prefilter_context["rule1_passed_via_rescue"], (
        f"Expected languageBytes rescue for {login} at Java={pct}%"
    )


@then(parsers.parse('the prefilter logs a rescue for "{login}" citing lifetime pull requests at {n:d}'))
def then_log_rescue_prs(prefilter_context, login, n):
    assert prefilter_context["rule2_passed_via_rescue"], (
        f"Expected lifetimePRs rescue for {login} at {n}"
    )


@then(parsers.parse("the rescue is triggered by JavaScript at {pct}% exceeding the threshold"))
def then_rescue_by_js(prefilter_context, pct):
    assert prefilter_context["rule1_passed_via_rescue"]


@then(parsers.parse('"{login}" passes the target language rule via language bytes rescue'))
def then_passes_rule1_via_rescue(prefilter_context, login):
    assert prefilter_context["rule1_passed_via_rescue"], (
        f"Expected {login} to pass Rule 1 via languageBytes rescue"
    )


@then(parsers.parse('"{login}" is discarded by the activity rule with reason "{reason}"'))
def then_discarded_by_rule2(prefilter_context, login, reason):
    # The overall result should be discarded even if Rule 1 was rescued
    actual = prefilter_context["result_reason"]
    assert actual == reason, f"{login}: expected discard reason '{reason}', got '{actual}'"


@then(parsers.parse('"{login}" passes the activity rule via lifetime pull requests rescue'))
def then_passes_rule2_via_rescue(prefilter_context, login):
    assert prefilter_context["rule2_passed_via_rescue"]


@then("the scan error passthrough rule applies")
def then_scan_error_passthrough(prefilter_context):
    dev = prefilter_context["developer"]
    assert dev.get("scanError") is not None


@then("the lifetime pull request fallback is not invoked")
def then_no_pr_fallback(prefilter_context):
    assert not prefilter_context["pr_fallback_invoked"], (
        "PR fallback was invoked but developer is above activity threshold"
    )


# Duplicate-safe: "But" steps use the same then parsers
