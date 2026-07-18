# `infra/` — sandboxed R runtime (STUB)

Agent-produced R is **untrusted code that touches user data**, so it must never run in the
backend process. The orchestrator shells out to `R_SANDBOX_CMD` (default:
`infra/run_r_sandboxed.sh`), which must enforce the sandbox contract below.

## The sandbox contract (what `run_r_sandboxed.sh` must guarantee)

Invoked as:

```
run_r_sandboxed.sh --script <path.R> --workdir <run_dir> --timeout <s> --max-memory-mb <mb>
```

It must:

1. **No network.** The container/namespace has networking disabled. R cannot phone home or
   exfiltrate the user's data.
2. **Resource caps.** CPU, memory (`--max-memory-mb`), and wall-time (`--timeout`) limits,
   enforced by the runtime (cgroups / `ulimit` / container limits), not by trusting the script.
3. **Ephemeral, minimal mounts.** Only `<run_dir>` is mounted read-write (so the script can
   write `analytic.parquet`, `results/`, `agent-results.yaml`, `sessionInfo.txt`). Nothing
   else on the host is visible. The session dataset is staged inside `<run_dir>/_session/`.
4. **Preinstalled, pinned R env.** The internal `cibmtrrepro` package (see `r-engine/`) plus
   `survival`, `cmprsk`, `tidycmprsk`, `arrow`, `IPDfromKM`, pinned via `renv`. Writes
   `sessionInfo.txt` and honors `renv.lock` so runs are reproducible later.
5. **Non-root, read-only rootfs** except the run dir. Drop capabilities.
6. **Exit code is meaningful.** Non-zero exit ⇒ the orchestrator treats results as invalid and
   does not score them.

## Reference implementation sketch (Docker)

`run_r_sandboxed.sh` (stub in this repo) would do roughly:

```bash
docker run --rm \
  --network none \
  --memory "${MAXMEM}m" --cpus 2 --pids-limit 256 \
  --read-only --tmpfs /tmp \
  -v "$WORKDIR":/work:rw \
  --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges \
  cibmtr-r-sandbox:pinned \
  Rscript --vanilla /work/"$(basename "$SCRIPT")"
```

with an outer `timeout "$TIMEOUT"` wrapper.

## Status — IMPLEMENTED (MVP), with a documented hardening ladder

`run_r_sandboxed.sh` is now a **real runner**, and the backend image installs R + the
`cibmtrrepro` package, so agent-produced R executes. What it enforces today:

- **Ephemeral workspace scoping** — runs in the per-run dir with `HOME`/`TMPDIR` pinned there;
  `Rscript --vanilla` (no profile/site files, nothing saved or restored).
- **Resource caps** — wall-clock `timeout` (SIGKILL), `ulimit` on address space, CPU time, and
  output file size. `OPENBLAS/OMP_NUM_THREADS=1` bounds CPU.
- **Best-effort network isolation** — `unshare --net` when the container has the privilege (the
  backend image runs as root, so this normally applies). If not permitted, it warns and runs
  resource-capped but not network-isolated.

Verify it on a running backend: `GET /r-health` runs a real KM fit through the sandbox and
returns `{"r_ready": true, ...}`.

### Hardening ladder (still open — see `docs/TODO.md`)

The MVP runs R as a subprocess in the **same** container as the API. Stronger isolation, in
increasing order, for a hostile-input production posture:

1. **Container-per-run** — spawn a throwaway container per script (`--network none`, read-only
   rootfs, non-root, cap-drop, cgroup limits). Needs a Docker/daemon or Kubernetes Job the API
   can call; the `docker run …` recipe is sketched below.
2. **gVisor (`runsc`)** — run that container under a syscall-filtering sandbox.
3. **microVM (Firecracker / Kata)** — hardware-virtualized isolation per run.

Also outstanding regardless of sandbox tier: wiring the **session dataset upload** end to end
(the frontend has the file input; the backend needs the upload endpoint + to pass the path to
the cohort agents) before a *real* study — as opposed to the synthetic example — can run
through the UI.
