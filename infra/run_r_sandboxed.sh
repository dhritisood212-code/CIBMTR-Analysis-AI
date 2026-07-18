#!/usr/bin/env bash
# Hardened runner for UNTRUSTED, agent-produced R.
#
# The orchestrator calls this with the contract:
#   run_r_sandboxed.sh --script <path.R> --workdir <run_dir> --timeout <s> --max-memory-mb <mb>
#
# Isolation applied here (whatever the host permits):
#   * Ephemeral, per-run working directory; HOME/TMPDIR are pinned inside it so the script can
#     only write there. `Rscript --vanilla` => no profile/site file, nothing saved or restored.
#   * Wall-clock timeout via coreutils `timeout` (SIGKILL on expiry).
#   * Address-space (memory), CPU-time, and file-size caps via `ulimit`.
#   * Best-effort NETWORK ISOLATION via `unshare --net` when the container has the privilege
#     (our backend image runs as root, so this normally succeeds). If it's not permitted we
#     warn and continue resource-capped but not network-isolated. infra/README.md documents the
#     hardening ladder (container-per-run / gVisor / Firecracker) that closes that gap fully.
#
# Exit code is R's own (124 = timed out, 137 = killed). Non-zero => the orchestrator treats the
# run as invalid and does not score it.
set -uo pipefail

SCRIPT=""; WORKDIR=""; TIMEOUT=300; MAXMEM=4096
while [[ $# -gt 0 ]]; do
  case "$1" in
    --script)          SCRIPT="$2"; shift 2;;
    --workdir)         WORKDIR="$2"; shift 2;;
    --timeout)         TIMEOUT="$2"; shift 2;;
    --max-memory-mb)   MAXMEM="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 64;;
  esac
done

if [[ -z "$SCRIPT" || -z "$WORKDIR" ]]; then
  echo "usage: run_r_sandboxed.sh --script <path.R> --workdir <dir> [--timeout s] [--max-memory-mb mb]" >&2
  exit 64
fi
if ! command -v Rscript >/dev/null 2>&1; then
  echo "R sandbox: Rscript not found on PATH. Build the image with R installed (see infra/README.md)." >&2
  exit 69   # EX_UNAVAILABLE
fi

SCRIPT_ABS="$(cd "$(dirname "$SCRIPT")" && pwd)/$(basename "$SCRIPT")"
WORKDIR_ABS="$(cd "$WORKDIR" && pwd)"

# Prefix the run with a network namespace if the host allows it.
NET_PREFIX=()
if unshare --net true >/dev/null 2>&1; then
  NET_PREFIX=(unshare --net)
else
  echo "R sandbox: network namespace not permitted; running resource-capped but NOT network-isolated." >&2
fi

# Resource limits are set in this subshell and inherited across exec into unshare/timeout/R.
(
  ulimit -v $(( MAXMEM * 1024 )) 2>/dev/null || true   # address space, KB
  ulimit -t $(( TIMEOUT + 5 ))   2>/dev/null || true   # CPU seconds (belt-and-suspenders)
  ulimit -f 2097152              2>/dev/null || true   # max output file size ~2 GB
  cd "$WORKDIR_ABS" || exit 70
  export HOME="$WORKDIR_ABS" TMPDIR="$WORKDIR_ABS"
  export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1      # bound CPU / keep BLAS deterministic
  exec "${NET_PREFIX[@]}" timeout --signal=KILL "${TIMEOUT}s" Rscript --vanilla "$SCRIPT_ABS"
)
exit $?
