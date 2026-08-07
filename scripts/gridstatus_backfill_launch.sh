#!/bin/bash
# 5-min full-window backfill: 2023-02-07 -> 2026-06-30, 5 gridstatus.io accounts.
#
# Single-pass, one account per pnode plus a dedicated load account. Account 6
# is held as spare/retry budget and is NOT launched here.
#
# Free tier is 250 requests and 500K rows per account per calendar month, and
# requests are the binding constraint: 177 per pnode, 42 for load.
# See docs/superpowers/specs/2026-07-30-surg-recovery-design.md § "Quota arithmetic".
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
set -a; source .env; set +a

PY="$REPO_ROOT/.venv/bin/python"
START="${START:-2023-02-07T00:00:00Z}"
END="${END:-2026-06-30T00:00:00Z}"
DATA_ROOT="${DATA_ROOT:-data/raw/gridstatus}"
LOG_DIR="${LOG_DIR:-$HOME/surg-run-logs}"
mkdir -p "$LOG_DIR"

echo "=== backfill launched $(date) ==="
echo "repo=$REPO_ROOT window=$START -> $END data_root=$DATA_ROOT"

PIDS=()
LABELS=()
launch() {  # $1=account index  $2=label  $3...=extra args
  local idx="$1" label="$2"; shift 2
  local keyvar="GRIDSTATUS_API_KEY_${idx}"
  GRIDSTATUS_API_KEY="${!keyvar}" "$PY" -m surg.acquisition.gridstatus_pull \
    --start "$START" --end "$END" \
    --data-root "$DATA_ROOT" "$@" \
    > "$LOG_DIR/surg-gridstatus-backfill-account${idx}.log" 2>&1 &
  # Capture $! into a local BEFORE appending. Two constraints meet here:
  #   1. The obvious phrasing -- PID=$(launch ...) -- would put the background
  #      process in a subshell, making it a grandchild that `wait` cannot reap;
  #      every wait returns 127 instantly and the caller reports FAILED within a
  #      second while five pulls run on detached. A shell *function* does not
  #      fork, so $! and the array append below both land in the parent shell.
  #   2. ${PIDS[-1]} would be the natural way to echo it back, but negative
  #      array subscripts need bash >= 4.2 and macOS ships /bin/bash 3.2, where
  #      it is a hard "bad array subscript" error -- fatal under `set -u`.
  local pid=$!
  PIDS+=("$pid")
  LABELS+=("account${idx} (${label})")
  echo "account${idx} pid=${pid} (${label})"
}

launch 1 LOUDOUN      --pnodes 35010365   --skip-load
launch 2 PLEASANTVIEW --pnodes 35010371   --skip-load
launch 3 GOOSECRE     --pnodes 1356178195 --skip-load
launch 4 SKFFSCRK     --pnodes 1356178201 --skip-load
launch 5 LOAD         --skip-lmp

RC=0
for i in "${!PIDS[@]}"; do
  if ! wait "${PIDS[$i]}"; then
    echo "FAILED: ${LABELS[$i]} (pid ${PIDS[$i]})"
    RC=1
  fi
done

echo "=== backfill finished $(date): rc=$RC ==="
if [ "$RC" -eq 0 ]; then
  touch "$LOG_DIR/surg-gridstatus-backfill-DONE"
else
  touch "$LOG_DIR/surg-gridstatus-backfill-FAILED"
fi
