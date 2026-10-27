#!/usr/bin/env bash
# Daily discovery then processing for the always-on runner (#180).
#
# A user unit cannot order itself after the system manager's network
# targets, and a firing missed during a reboot (Persistent=true) starts as
# soon as the user manager is up. So the script first waits, for a bounded
# time, until production is reachable; `cs2a status` exits 1 with
# "Database unavailable" until it is. Only that probe is retried: the
# pipeline itself runs once, and a circuit-breaker halt (75) or a failed
# run (1) is reported, never re-run.
#
# Processing runs even when discovery fails, because pending rows never
# depend on discovery having caught up. The exit status reports the worst
# outcome so the unit's OnFailure= hook fires on either step.
set -u
cd "$(dirname "$0")/../.." || exit 1
UV="${UV:-$HOME/.local/bin/uv}"
READINESS_ATTEMPTS="${READINESS_ATTEMPTS:-10}"
READINESS_INTERVAL_SECONDS="${READINESS_INTERVAL_SECONDS:-30}"

attempt=1
until "$UV" run cs2a --env prod status > /dev/null 2>&1; do
  if [ "$attempt" -ge "$READINESS_ATTEMPTS" ]; then
    echo "cs2a-daily: production database unreachable after $attempt attempts" >&2
    exit 1
  fi
  echo "cs2a-daily: production not reachable yet (attempt $attempt); waiting" >&2
  attempt=$((attempt + 1))
  sleep "$READINESS_INTERVAL_SECONDS"
done

"$UV" run cs2a --env prod ingest discover
discover_status=$?
"$UV" run cs2a --env prod process --drain
process_status=$?

if [ "$discover_status" -ne 0 ]; then
  echo "cs2a-daily: discovery exited $discover_status" >&2
fi
if [ "$process_status" -ne 0 ]; then
  echo "cs2a-daily: processing exited $process_status" >&2
  exit "$process_status"
fi
exit "$discover_status"
