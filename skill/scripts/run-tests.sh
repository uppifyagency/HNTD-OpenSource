#!/usr/bin/env bash
# Run the pipeline's Python tests. Usage: skill/scripts/run-tests.sh [python]
# Install the test dependencies first: pip install -r skill/scripts/requirements-dev.txt
# The acceptance suites run one directory at a time: their step modules share names and
# collide when pytest collects them together.
set -euo pipefail
cd "$(dirname "$0")"
PY=${1:-.venv/bin/python}
# Tests must never reach a real deployment.
export CONVEX_SITE_URL=http://127.0.0.1:9 API_SECRET=test

"$PY" -m pytest -q test_*.py
"$PY" -m pytest -q tests/jd_pipeline
"$PY" -m pytest -q tests/acceptance/search-priority-fix
"$PY" -m pytest -q tests/acceptance/ranking-pipeline-rwia-fixes
"$PY" -m pytest -q tests/acceptance/search-pipeline-fix/steps/test_slice1_search_pool.py \
  tests/acceptance/search-pipeline-fix/steps/test_slice3_prefilter_fallbacks.py
