# Driving the Suite

Two ways to drive the debugger-tool acceptance suite:

- **(A) one skill at a time** — for a manual acceptance run + verify + rebuild.
- **(B) the `debugger-loop` skill** — for the full, automated
  `run → fix → verify → restart` loop.

---

## A. Drive with the individual skills

### 1. Acceptance run — `debugger-suite`

Load [`skills/debugger-suite/SKILL.md`](skills/debugger-suite/SKILL.md). In short:

- **One driver** agent owns every `debugger` tool call serially — never fan out
  sessions. The DAP client is a single shared, stateful resource (global
  session-id namespace, project-level breakpoints, fragile boot timing).
- Work **one language at a time**: Python (`Debugpy`, 10 bugs) → JavaScript →
  TypeScript (source maps) → Go (`Delve`) → Rust (`CodeLLDB`) → C (`GDB`)
  (4 defects each).
- Per language: `start_session` → `list_sessions` (source of truth) →
  `set_breakpoints` → `control` / `snapshot` → `stop_session` /
  `remove_breakpoints`.
- Exercise every capability per adapter: breakpoint + `snapshot`,
  `step_in` / `step_out`, `run_to_line`, and `pause`.
- Find each bug by `snapshot`, not by reading source; verify a fix by
  snapshotting the now-correct value.
- Optional: use **parallel prep agents** (one per language) for the non-debugger
  work — building TypeScript/Rust/C and returning `program` / `cwd` / `args` +
  a breakpoint line map. They never touch the `debugger` tool.

Record results in a fresh `test-reports/TEST_REPORT-YYYY-MM-DD-HHMM.md` (copy the
template; never edit the template in place). Reconcile `ISSUES.json` with each
finding.

### 2. Verify — `zed-verify`

Load [`skills/zed-verify/SKILL.md`](skills/zed-verify/SKILL.md). In the Zed fork:

- `./script/clippy` (not `cargo clippy`).
- Narrow `cargo test -p <crate>` for the crates you touched.

### 3. Build — `remote-compiler` (global)

Heavy Zed builds go to a remote compiler, never the laptop. Follow your
`remote-compiler` setup to rebuild `zed.exe` (+ `cli.exe`, `conpty.dll`,
`OpenConsole.exe`) and copy the runnable set into the dev-build folder.

---

## B. Drive with the loop — `debugger-loop`

Load [`skills/debugger-loop/SKILL.md`](skills/debugger-loop/SKILL.md). The loop
is a repeating cycle:

```
run (acceptance suite) → fix (commit fixes) → verify (clippy) → restart (rebuild zed.exe) → run → …
```

- Loop state lives in `LOOP_STATE.json`; **`next_action` is the source of truth**
  for what to do next (`run` / `fix` / `verify` / `restart`).
- Issue identity / status / cause lives in `ISSUES.json`; the skill keeps the two
  files reconciled.
- [`scripts/loop/restart-zed.py`](scripts/loop/restart-zed.py) launches a fresh
  Zed with the resume prompt (non-destructive — never kills the running instance).
- [`scripts/loop/check-loop-state.py`](scripts/loop/check-loop-state.py) validates
  the state files for drift.

To resume, read `LOOP_STATE.json` and perform `next_action`.

> Note: the loop state files (`LOOP_STATE.json`, `ISSUES.json`,
> `resume-loop.md`) are the author's internal fix-loop tracking and are not
> committed to this public harness. The loop method is included here for
> completeness of the driving workflow.
