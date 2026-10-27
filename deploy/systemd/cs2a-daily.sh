#!/usr/bin/env bash
# Daily discovery then processing for the always-on runner (#180).
#
# Processing runs even when discovery fails, because pending rows never
# depend on discovery having caught up. The exit status reports the worst
# outcome so the unit's OnFailure= hook fires on either step: 75 is a
# circuit-breaker halt (the source pushed back), 1 is a failed discovery
# run or a stage in which every item failed.
set -u
cd "$(dirname "$0")/../.." || exit 1
UV="${UV:-$HOME/.local/bin/uv}"

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
