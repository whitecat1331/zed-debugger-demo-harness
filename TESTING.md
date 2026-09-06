# Agent test brief — Zed debugger-tool suite

This is the kickoff brief for an AI agent running the Zed agent **`debugger`**
tool acceptance suite in this repo. The point of the suite is to prove the
debugger works end-to-end against every bundled DAP adapter **by using the tool**,
not by reading the code.

## Mission

Run the whole suite with the `debugger` tool, find and fix each deliberate bug,
verify each fix with a `snapshot`, then re-break and verify the bug is back.

Two parts:

1. **Python** (`Debugpy`): ten deliberate bugs in `bugs/`.
2. **Cross-language** (`JavaScript`, `Delve`, `CodeLLDB`, `GDB`): four shared
   defects per language in `javascript/`, `typescript/`, `golang/`, `rust/`,
   and `c/`.

## The tool surface

Use these `debugger` operations (`list_adapters` shows each adapter's schema):

- `list_adapters` — registered adapters and their config schemas.
- `start_session` — `{ adapter, label }` plus the launch-config fields
  spread at the scenario top level (NOT nested under a `"config"` key).
- `set_breakpoints` / `remove_breakpoints` — `{ path, line }` (plus optional
  `condition` to stop only on failing cases, e.g. `"condition": "num == -4"`).
- `snapshot` — threads, stack frames, source, variables (optional
  `snapshot_limits` to bound output).
- `control` — `continue | pause | step_over | step_in | step_out | run_to_line`.
- `list_sessions` / `stop_session`.

Treat `list_sessions` immediately after `start_session` as the source of
truth: `start_session` can return a session_id even when the panel rejects
the config or the adapter boot times out (phantom session — it never appears
in `list_sessions`). Breakpoints persist across sessions, so remove them as
you finish each bug.

## Ground rules

- Find each bug by setting a breakpoint and `snapshot`-ing live state. Do **not**
  just read the source and "fix" it.
- Verify a fix by `snapshot`-ing the now-correct value, not only by rerunning.
- After fixing, re-break (see `REBREAKING.md`) and `snapshot` the wrong value
  again to confirm it is broken.
- `run_to_line` and `pause` are the highest-risk capabilities — exercise them
  for **every** adapter, not just Python.

## Adapter matrix

| Language | `adapter` value | Directory | Build before launch |
|----------|-----------------|-----------|---------------------|
| Python | `Debugpy` | `bugs/`, `main.py` | none |
| JavaScript | `JavaScript` | `javascript/` | none |
| TypeScript | `JavaScript` | `typescript/` | `npm install && npm run build` |
| Go | `Delve` | `golang/` | none (Delve builds) |
| Rust | `CodeLLDB` | `rust/` | `cargo build` |
| C | `GDB` | `c/` | `gcc -g -O0 main.c -o main` |

Full `start_session` launch-config JSON lives in `README.md`. Adapter names are
case-sensitive and fixed: `Debugpy`, `JavaScript`, `Delve`, `CodeLLDB`, `GDB` —
not `"python"`, `"node"`, `"go"`, etc.

## Launch-config gotchas

- **Spread the launch config at the scenario top level** — do not nest it
  under a `"config"` key:
  `{"adapter": "Debugpy", "label": "...", "request": "launch", "program": "...", "cwd": "..."}`.
  The nested form is silently rejected — `start_session` still returns a
  session_id, but the session never appears in `list_sessions`.
- **JavaScript/TypeScript**: the config must include `"type": "pwa-node"`.
  TypeScript launches the compiled `dist/main.js`, with breakpoints set in
  `main.ts` resolved via source maps.
- **Go**: `"mode": "debug"` with `"program": "."` builds the package.
- **C/GDB**: use `"stopAtBeginningOfMainSubprogram": true` (not `stopOnEntry`).
- **Rust/C++ (CodeLLDB)**: launch the compiled binary as `program`.

## Part 1 — Python (`Debugpy`)

Follow `README.md` "How to debug" plus the per-bug hints. Work through all ten
bugs. The capability-specific ones are:

| Bug | Capability |
|-----|------------|
| bug 6 | `step_in` |
| bug 7 | `step_out` |
| bug 8 | `run_to_line` |
| bug 9 | `pause` |

## Part 2 — Cross-language

Every non-Python `main` file contains the same four defects, one per capability:

| Defect (function) | Capability | Procedure |
|-------------------|------------|-----------|
| `apply_discount` | `step_in` / `step_out` | breakpoint on the call, `step_in`, snapshot `price`/`percent`, `step_out` |
| `sum_even` | breakpoint + `snapshot` | snapshot the accumulator each iteration |
| `process` (`processValues` in JS/TS) | `run_to_line` | run straight to the `+= 1000` line (no breakpoint), snapshot |
| `find_divisor` | `pause` | launch with `--hang`, `pause`, snapshot `i` stuck |

Per language: `start_session` → work all four defects → `stop_session` → next.

## Acceptance criteria

For every language, all of the following must hold:

- Each defect was found via `snapshot`, not by reading.
- Each fix was verified by `snapshot`-ing the correct value.
- `run_to_line` reaches the corruption line and the snapshot shows it.
- `pause` interrupts the hung `--hang` run and the snapshot shows the stuck loop.
- After re-breaking, the wrong value is observable again.

Expected outputs are annotated in each `main` file as `(expected …)`.

## Watch list (report as findings)

- `run_to_line` on Delve (historically flaky) and CodeLLDB.
- `pause` reliability on CodeLLDB and GDB.
- TypeScript source-map resolution (breakpoint in `.ts`, execution in `dist/`).
- Any adapter that fails to launch, or returns empty/unexpanded variable
  children in `snapshot`.

## Report format

[`test-reports/TEST_REPORT_TEMPLATE.md`](test-reports/TEST_REPORT_TEMPLATE.md)
is a blank template — **never fill it in
place**. At the start of the run, copy it to the reports folder with a date/time
suffix, then fill in that copy:

```
test-reports/TEST_REPORT-YYYY-MM-DD-HHMM.md
```

The template has a per-language checklist (found / fixed / re-broken),
capability checks, and a findings section. Return the completed report plus a
short prose summary of anything on the watch list (adapter + operation +
session id + config + snapshot output).

## Fixing & re-breaking

Use `REBREAKING.md` for the exact broken → fixed → re-broken form of each of the
four shared defects. `README.md` holds the launch configs; `ROADMAP.md` tracks
future adapters and the rendering-fidelity checks to add when they arrive.
