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
- `control` — `continue | pause | step_over | step_in | step_out | step_back | run_to_line | detach | restart | restart_frame`.
- `evaluate` — `{ session_id, expression, frame_id? }`; returns the computed
  result string and its `variables_reference`.
- `set_variable` — `{ session_id, variables_reference, name, value, frame_id? }`;
  pass a scope's `variables_reference` from a snapshot, then `snapshot` again to
  confirm the change.
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

## Regression coverage for new operations

Any new `debugger` operation must be added to this brief's tool surface **and**
acceptance criteria before its feature work is considered complete. An
operation that is not exercised end-to-end against a real adapter is not done —
extend the criteria above and add a runbook procedure that drives the operation
through `snapshot`/`control` to prove it behaves.

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

### `step_back` (new control action)

Reverse execution is not advertised by any bundled adapter
(`supports_step_back` is absent), so `control step_back` must return a clear
unsupported-capability error instead of sending a `stepBack` DAP request.
Exercise the gate on every adapter:

1. `start_session` and stop at a breakpoint/entry.
2. `control` with `action: "step_back"` on the stopped thread.
3. Assert the tool returns an error mentioning "does not support" (no hang,
   no silent no-op, no `stepBack` request emitted).

The happy path (an actual reverse step) is validated by the fake-adapter source
test in `crates/debugger_ui/src/tests/agent_api.rs`, since no bundled adapter
implements `stepBack`.

### `detach`, `restart`, `restart_frame` (new control actions)

These three are capability/state-gated, so the suite exercises the gate on
**every** adapter rather than a happy path (the happy paths are validated by the
fake-adapter source tests in `crates/debugger_ui/src/tests/agent_api.rs`):

- **`detach`** — only valid for attach sessions. Every suite session is a
  launch, so `control action: "detach"` must return a clear `not attached`
  error (no DAP `disconnect` emitted, no hang, no silent no-op).
- **`restart`** — gated on `supports_restart_request`. On an adapter that does
  not advertise it, `control action: "restart"` must return a clear
  `does not support` error. If an adapter advertises it, assert the session
  restarts and record the adapter in the report.
- **`restart_frame`** — gated on `supports_restart_frame`, using a `frame_id`
  from a `snapshot`. Same unsupported-capability contract as `restart`.

Procedure per adapter (after `start_session` and stopping at a breakpoint/entry):

1. `snapshot` to obtain a stopped thread (and, for `restart_frame`, a frame id).
2. `control` each action and record the result in the report.
3. Assert the error is a clear, immediate capability/state error — never a
   hang or a DAP request the adapter silently rejects.

## Acceptance criteria

For every language, all of the following must hold:

- Each defect was found via `snapshot`, not by reading.
- Each fix was verified by `snapshot`-ing the correct value.
- `run_to_line` reaches the corruption line and the snapshot shows it.
- `pause` interrupts the hung `--hang` run and the snapshot shows the stuck loop.
- `evaluate` returns the correct computed value (e.g. `1 + 1` → `"2"`).
- `set_variable` mutates a variable and a follow-up `snapshot` shows the new
  value.
- `control step_back` returns a clear unsupported-capability error on every
  adapter (no bundled adapter advertises `supports_step_back`).
- `control detach` returns a clear `not attached` error on every launch session.
- `control restart` returns a clear `does not support` error (or restarts, when
  the adapter advertises `supports_restart_request`).
- `control restart_frame` returns a clear `does not support` error (or restarts
  the frame, when the adapter advertises `supports_restart_frame`).
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
