#!/bin/bash
# Proves the cron's mutual-exclusion actually excludes -- and, more importantly, that it
# lets the FIRST run through. The predecessor (flock) does not exist on macOS: it exited
# 127, the `|| exit 0` branch fired, and the daily job silently did nothing for as long
# as it was installed. A lock that always says "already running" looks identical in the
# log to a machine that was simply asleep, which is why this file exists.
#
#   ./test-cron-lock.sh   -> prints PASS/FAIL per case, exits non-zero on any failure
set -u

LOCK="$(mktemp -d)/cron.lock"
fails=0
check() {  # check <description> <expected> <actual>
  if [ "$2" = "$3" ]; then printf 'PASS  %s\n' "$1"
  else printf 'FAIL  %s (atteso %s, ottenuto %s)\n' "$1" "$2" "$3"; fails=$((fails + 1)); fi
}

/usr/bin/lockf -t 0 "$LOCK" true
check "il primo run acquisisce il lock ed esegue" 0 $?

/usr/bin/lockf "$LOCK" sleep 3 &
holder=$!
sleep 0.4
/usr/bin/lockf -t 0 "$LOCK" true 2>/dev/null
check "un run concorrente viene respinto (75 = EX_TEMPFAIL)" 75 $?
wait $holder 2>/dev/null

/usr/bin/lockf -t 0 "$LOCK" true
check "rilasciato il lock, il run successivo passa" 0 $?

# The case shlock got wrong: an owner killed outright must not wedge every future run.
/usr/bin/lockf "$LOCK" sleep 30 &
victim=$!
sleep 0.4
kill -9 $victim 2>/dev/null
wait $victim 2>/dev/null
/usr/bin/lockf -t 0 "$LOCK" true
check "dopo kill -9 del detentore il lock e' libero" 0 $?

[ "$fails" -eq 0 ] || exit 1
echo "tutti i casi verdi"
