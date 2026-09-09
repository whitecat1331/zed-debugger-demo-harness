---
name: debugger-suite
description: Run the Zed agent debugger-tool acceptance suite (Python, Go, JavaScript, TypeScript, Rust, C) against a debugger-enabled Zed build. Use when the user wants to kick off, run, verify, or report on the Zed debugger (DAP) feature end-to-end across all bundled adapters.
---

# Zed debugger-tool acceptance suite

Drive the Zed agent **`debugger`** tool (the DAP client) through the
through this harness to prove it works against every bundled adapter.
The point is to find and fix each deliberate bug **using the tool**, not by
reading the source.

## Prerequisites

- A Zed build with the `debugger` agent tool enabled (the revived PR #58439
  build).
- This harness checked out locally.
- Toolchains for the languages under test (see the harness `README.md`):
  Python + `debugpy`; Node; Go; `cargo`/`rustc`; a C compiler + `gdb`.
  Zed auto-downloads the `vscode-js-debug`, CodeLLDB, and Delve adapters.

## Ground rules

- Find each bug via breakpoint + `snapshot`; do not just read and "fix" it.
- Verify a fix by `snapshot`-ing the now-correct value, not only by rerunning.
- Re-break afterward (see `REBREAKING.md`) and `snapshot` the wrong value again.
- Exercise `run_to_line` and `pause` for **every** adapter — they are the
  highest-risk capabilities.

## Regression coverage for new operations

Every new `debugger` operation must be added to the acceptance criteria below
before its feature work is considered complete — an operation that is not
exercised end-to-end against a real adapter is not "done". When you add an
operation to the tool, extend the acceptance criteria and add a runbook
procedure that drives it through `snapshot`/`control` to prove it behaves.

## Tool surface

`list_adapters`, `start_session` (`{adapter, label}` + the launch-config
fields spread at the scenario top level), `set_breakpoints` /
`remove_breakpoints` (`{path, line, condition?}`), `snapshot`
(`{session_id, snapshot_limits?}`), `control`
(`continue | pause | step_over | step_in | step_out | run_to_line`),
`evaluate` (`{session_id, expression, frame_id?}`), `set_variable`
(`{session_id, variables_reference, name, value, frame_id?}`),
`list_sessions`, `stop_session`.

## Adapter matrix

| Language | `adapter` value | Directory | Build before launch |
|----------|-----------------|-----------|---------------------|
| Python | `Debugpy` | `bugs/`, `main.py` | none |
| JavaScript | `JavaScript` | `javascript/` | none |
| TypeScript | `JavaScript` | `typescript/` | `npm install && npm run build` |
| Go | `Delve` | `golang/` | none (Delve builds) |
| Rust | `CodeLLDB` | `rust/` | `cargo build` |
| C | `GDB` | `c/` | `gcc -g -O0 main.c -o main` |

Adapter names are case-sensitive and fixed: `Debugpy`, `JavaScript`, `Delve`,
`CodeLLDB`, `GDB` — not `"python"`, `"node"`, `"go"`, etc.

### Launch-config gotchas

Full `start_session` launch-config JSON lives in the harness `README.md`. Key
fields to get right:

- **Spread the launch config at the scenario top level** — do NOT nest it
  under a `"config"` key:
  `{"adapter": "Debugpy", "label": "...", "request": "launch", "program": "...", "cwd": "..."}`.
  The nested `"config"` form is silently rejected — `start_session` still
  returns a session_id, but the session never appears in `list_sessions`.
- **JavaScript/TypeScript**: the config must include `"type": "pwa-node"`.
  TypeScript launches the compiled `dist/main.js`, with breakpoints set in
  `main.ts` resolved via source maps.
- **Go**: `"mode": "debug"` with `"program": "."` builds the package.
- **C/GDB**: use `"stopAtBeginningOfMainSubprogram": true` (not `stopOnEntry`).
- **Rust (CodeLLDB)**: launch the compiled binary as `program`.

## Session hygiene

- Treat `list_sessions` immediately after `start_session` as the source of
  truth: `start_session` can return a phantom session_id even when the panel
  rejects the config or the adapter boot times out (check `Zed.log` for
  `debugger_panel` errors when sessions vanish).
- The tool auto-adds `stopOnEntry` for launch configs, so a fresh session
  stops at the program's first line.
- `control continue` on a hanging program returns `status: "timedout"` with a
  live snapshot — pair it with `pause` + `snapshot` to inspect the hang.
- A session disappears from `list_sessions` when the debuggee exits — that is
  normal, not a launch failure.
- Don't cancel an agent turn mid-`start_session`: the in-flight boot dies and
  can briefly wedge the next sessions (TCP DAP timeout).
- Breakpoints persist across sessions (project-level). Remove them as you
  finish each bug, and prefer setting all breakpoints before launch —
  mutating breakpoints while stopped mid-session has killed the debuggee
  once.
- Use `condition` on `set_breakpoints` to stop only on failing cases
  (e.g. `{"condition": "num == -4"}`), and `snapshot_limits` to keep the
  large per-stop JSON manageable.

## Execution pattern

Run the suite with a **single driver agent** owning every `debugger` tool call,
plus **parallel prep agents** for the independent, non-debugger work. Do **not**
fan out debugger sessions — the DAP client is shared, stateful, and
single-threaded (global session-id namespace, project-level breakpoints, fragile
boot timing); parallel `start_session`/`control`/`snapshot` calls collide rather
than speed up.

### Driver (exactly one)

- Owns `start_session` → `list_sessions` (source of truth) → `set_breakpoints` →
  `control` → `snapshot` → `stop_session` / `remove_breakpoints`, serially, one
  language at a time.
- Owns all writes to `ISSUES.json`, `LOOP_STATE.json`, and the report.

### Prep agents (one per language, parallel, disjoint)

Each returns a `program` / `cwd` / `args` launch config plus a breakpoint line
map; none touch the debugger tool, breakpoints, or the ledger/report:

| Agent | Deliverable |
|-------|-------------|
| Python | `python main.py` broken output; 10-bug line map |
| JavaScript | `node --version`; 4-defect line map |
| TypeScript | `npm install && npm run build`; confirm `dist/main.js` + source map; line map |
| Go | `go version` / `dlv version` (expect DAP-001 block); line map |
| Rust | `cargo build`; confirm binary path; line map |
| C | `gcc -g -O0 main.c -o main`; confirm binary; line map |

**Verify every prep output against real paths before the driver consumes it.**
Prep agents can get `cwd`/line numbers slightly wrong — e.g. a JS prep once
suggested `cwd` = repo root when the correct value is `javascript/` per
`README.md`; `find_divisor` line maps may report the `while`/`for` header while
`pause` actually lands on the inner `if`.

### Speed levers

- **Carry forward unchanged capabilities.** A `project`-only pause fix does not
  require re-driving `step_in`/`step_out`/`run_to_line` on every adapter; re-run
  only the changed path plus smoke checks on the riskiest capabilities (`pause`,
  breakpoint+snapshot).
- **Always pass `snapshot_limits`** on `snapshot`/`control` — the JS `Closure`
  scope alone can produce ~10k tokens; `max_frames`, `max_variables_per_scope`,
  and `max_variable_value_length` collapse it to a few hundred.
- **Batch `set_breakpoints` before launch**; don't mutate breakpoints mid-session.
- **One session per language**, stopped before moving on.

## Runbook

### Python (`Debugpy`)

Work through the ten bugs in `bugs/`. The capability-specific ones are:

| Bug | Capability |
|-----|------------|
| bug 6 | `step_in` |
| bug 7 | `step_out` |
| bug 8 | `run_to_line` |
| bug 9 | `pause` |

Follow the per-bug hints in the harness `README.md`.

### Cross-language

Every non-Python `main` file contains the same four defects, one per capability:

| Defect (function) | Capability | Procedure |
|-------------------|------------|-----------|
| `apply_discount` | `step_in` / `step_out` | breakpoint on the call, step in, snapshot `price`/`percent`, step out |
| `sum_even` | breakpoint + `snapshot` | snapshot the accumulator each iteration |
| `process` (`processValues` in JS/TS) | `run_to_line` | run straight to the `+= 1000` line (no breakpoint), snapshot |
| `find_divisor` | `pause` | launch with `--hang`, `pause`, snapshot `i` stuck |

For each language: `start_session` → work all four defects → `stop_session` →
move to the next language.

### Evaluate / set_variable (new operations)

- `evaluate`: while stopped at a breakpoint, evaluate a simple expression
  (`{session_id, expression}`) and assert the returned `result`.
- `set_variable`: from a `snapshot`, take a scope's `variables_reference` and a
  variable `name`, set it (`{session_id, variables_reference, name, value}`),
  then `snapshot` again and confirm the value changed.
- Exercise both on at least one adapter per language, and confirm the
  capability-gated error on an adapter that lacks `supports_set_variable`.

## Acceptance criteria

For every language, all of the following must hold:

- Each defect was found via `snapshot`, not by reading.
- Each fix was verified by `snapshot`-ing the correct value.
- `run_to_line` reaches the corruption line and the snapshot shows it.
- `pause` interrupts the hung `--hang` run and the snapshot shows the stuck loop.
- `evaluate` returns the correct computed value (e.g. `1 + 1` → `"2"`).
- `set_variable` mutates a variable and a follow-up `snapshot` shows the new
  value.
- After re-breaking, the wrong value is observable again.

Expected outputs are annotated in each `main` file as `(expected …)`.

## Watch list (report as findings)

- `run_to_line` on Delve (historically flaky) and CodeLLDB.
- `pause` reliability on CodeLLDB and GDB.
- TypeScript source-map resolution (breakpoint in `.ts`, execution in `dist/`).
- Any adapter that fails to launch, or returns empty/unexpanded variable
  children in `snapshot`.

Known adapter gotchas observed on the acceptance runs (2026-09-04):

- **GDB: debuggee stdout never appears in `snapshot.output`** (gdb-dap
  limitation) — snapshots only carry gdb console text. Verify program output
  via the `Return` scope after `step_out` (gdb-dap exposes `(return)` values)
  or via a CLI run; don't claim a fix without one of those.
- **GDB: set breakpoints on loop-body lines, not `for`/`while` header lines** —
  continuing from a re-hit on a header-line breakpoint has killed the whole
  session (gdb-dap 17.2 quirk).
- **CodeLLDB (Rust): avoid conditional breakpoints** (`condition` wedged resume
  at loader/ntdll disassembly once) — use plain breakpoints and re-derive
  values from snapshots.
- **Debugpy `pause`** — historically the first `pause` returned a
  "did not halt"-style status and needed a second `pause`; fixed in commit
  `49082d4083` (DAP-002), so a single `pause` should halt the current build.
  If you still see "did not halt", pause again as a fallback.

## Report

`test-reports/TEST_REPORT_TEMPLATE.md` is a blank template —
**never fill it in place**. At the start of the run, copy it to the reports
folder with a date/time suffix, then fill in that copy:

```
test-reports/TEST_REPORT-YYYY-MM-DD-HHMM.md
```

The template has a per-language checklist (found / fixed / re-broken),
capability checks, and a findings section keyed by stable issue ID. Return the
completed report plus a short prose summary of anything on the watch list,
including adapter + operation + session id + config + snapshot output.

After filling the report, reconcile `ISSUES.json`: mark
resolved issues, update `last_seen`, add new IDs, and record a cause assessment
for each finding (see "Cause assessment"). Findings in the report must reference
stable IDs (`DAP-xxx`, `HOST-xxx`), never prose "prior finding N".

## Cause assessment (no guesses)

For every finding, record the cause in exactly one of three states:

- **Confirmed** — `root_cause` + `verification` are non-empty. Proven.
- **Hypothesized** — `hypotheses[]` with `confidence` `high` or `medium`, each
  with a non-empty `basis` (the specific evidence) and what would disprove it.
- **Unknown** — state explicitly that you don't know the cause.

Rules:

- No guess is better than an incorrect guess; a correct guess is most useful.
- `low`/speculative confidence is not allowed — if that is all you have, record
  `unknown`.
- Never fabricate a plausible-sounding cause. If there is no signal, write
  `unknown` and let the planner instrument first.

## Fix & re-break

Use `REBREAKING.md` for the exact broken → fixed → re-broken
form of each of the four shared defects.

## References

- `TESTING.md` — full agent brief (authoritative).
- `test-reports/TEST_REPORT_TEMPLATE.md` — fill-in report
  template (copy to `TEST_REPORT-YYYY-MM-DD-HHMM.md` before filling in).
- `REBREAKING.md` — fix/re-break reference.
- `README.md` — launch configs, prerequisites, Python hints.
- `ROADMAP.md` — future adapters + rendering-fidelity checks.
- `DRIVING_THE_SUITE.md` — the single-driver + parallel-prep execution pattern.
