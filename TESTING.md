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
- `control` — `continue | pause | step_over | step_in | step_out | step_back | run_to_line | detach | restart | restart_frame`. The step
  actions accept an optional `granularity` (`line` | `statement` |
  `instruction`; defaults to `line`).
- `evaluate` — `{ session_id, expression, frame_id? }`; returns the computed
  result string and its `variables_reference`.
- `set_variable` — `{ session_id, variables_reference, name, value, frame_id? }`;
  pass a scope's `variables_reference` from a snapshot, then `snapshot` again to
  confirm the change.
- `list_exception_breakpoints` / `set_exception_breakpoints` — read / enable-or-
  disable the adapter's exception-breakpoint filters (`{ id, enabled }`).
- `list_data_breakpoints` / `set_data_breakpoints` — read / set data breakpoints
  on a variable (`{ variables_reference, name, access_type?, condition?, hit_condition? }`).
- `set_ignore_breakpoints` — `{ session_id, ignore }`; toggle ignoring all
  breakpoints for a session.
- `clear_breakpoints` — clear every source breakpoint in the project.
- `read_memory` — `{ session_id, memory_reference, offset?, count }`; reads raw
  memory via DAP `readMemory`, gated on `supports_read_memory_request`. Content
  is returned base64-encoded with a decoded byte count.
- `list_modules` / `list_loaded_sources` — `{ session_id }`; list the debuggee's
  loaded modules (DLLs/shared libraries) and loaded source files, gated on
  `supports_modules_request` / `supports_loaded_sources_request`.
- `list_history` / `select_history` — list / select the session's historic
  stopped-state snapshots (`{ session_id }` / `{ session_id, index }`); the next
  `snapshot` reflects the selected frame.
- `list_watch_expressions` / `add_watch_expression` / `remove_watch_expression` —
  read / add / remove the session's watch list (`{ session_id, expression,
  frame_id? }`), evaluate-backed.
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

### Breakpoint-class operations (new)

Five new operations (three write ops with read counterparts, plus ignore-all and
clear-all). Like `step_back` / `restart`, they are capability/state-gated, so the
suite exercises the gate on every adapter and the happy path where the adapter
advertises support (happy paths are also covered by fake-adapter source tests in
`crates/debugger_ui/src/tests/agent_api.rs`):

- **`list_exception_breakpoints`** — returns the adapter's
  `exception_breakpoint_filters` (id + label + enabled).
- **`set_exception_breakpoints`** — idempotent enable/disable per filter
  (`{ id, enabled }`), gated on `exception_breakpoint_filters`; returns a clear
  `does not support` error when the adapter advertises none.
- **`list_data_breakpoints`** — returns the session's data breakpoints.
- **`set_data_breakpoints`** — resolves each `{ variables_reference, name }`
  through DAP `dataBreakpointInfo` → `dataId`, then `setDataBreakpoints`, gated
  on `supports_data_breakpoints`; returns a clear `does not support` error when
  absent.
- **`set_ignore_breakpoints`** — `{ session_id, ignore }`; re-sends source
  breakpoints with/without the ignore flag (local running session only).
- **`clear_breakpoints`** — project-global clear of all source breakpoints.

Procedure per adapter (after `start_session` and stopping at a breakpoint/entry):

1. `list_exception_breakpoints` → record the filters (or the `does not support`
   gate).
2. `set_exception_breakpoints` on one filter → `list_exception_breakpoints`
   confirms the enabled flag changed (or assert the gate).
3. `set_data_breakpoints` on a variable from a `snapshot` scope →
   `list_data_breakpoints` shows it (or assert the `does not support` gate).
4. `set_ignore_breakpoints true` → confirm a breakpoint no longer stops →
   `set_ignore_breakpoints false`.
5. `set_breakpoints` then `clear_breakpoints` → `list_breakpoints` returns empty.

### Inspection operations (Phase 4)

Three read/evaluate-backed surfaces the agent can now touch. `read_memory` is
capability-gated; history and watch are client-side (no DAP gate).

#### `read_memory`

1. `start_session` and stop at a breakpoint/entry; `snapshot` to obtain a
   stopped thread.
2. Obtain a `memory_reference` (e.g. from a snapshot variable's
   `memory_reference`, or an evaluate result).
3. `read_memory` with `{ session_id, memory_reference, count }`; assert the
   returned `content` base64-decodes to the requested byte count.
4. On an adapter that does not advertise `supports_read_memory_request`, assert
   `read_memory` returns a clear `does not support` error (no `readMemory`
   request emitted).

#### `list_history` / `select_history`

1. `start_session` and stop at a breakpoint/entry.
2. Continue/step a couple of times so the session records multiple stopped
   states.
3. `list_history` → assert it reports the recorded snapshots (index + thread
   count).
4. `select_history` on a valid index → `snapshot` reflects that older frame.
5. `select_history` on an out-of-bounds index → clear error.

#### `list_modules` / `list_loaded_sources`

1. `start_session` and stop at a breakpoint/entry.
2. `list_modules` → assert it returns the loaded modules (id, name, path,
   symbol status) when the adapter advertises `supports_modules_request`.
3. `list_loaded_sources` → assert it returns the loaded sources (name, path)
   when the adapter advertises `supports_loaded_sources_request`.
4. On an adapter that does not advertise the capability, assert the operation
   returns a clear `does not support` error (no DAP request emitted).

#### Watch expressions

1. `start_session` and stop at a breakpoint/entry.
2. `add_watch_expression` with `{ session_id, expression }` →
   `list_watch_expressions` shows it with the evaluated value.
3. `remove_watch_expression` → `list_watch_expressions` no longer shows it.

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
- `list_exception_breakpoints` / `set_exception_breakpoints` exercise the
  adapter's exception-breakpoint filters (or the `does not support` gate when the
  adapter advertises none).
- `list_data_breakpoints` / `set_data_breakpoints` exercise data breakpoints (or
  the `does not support` gate when the adapter lacks `supports_data_breakpoints`).
- `set_ignore_breakpoints` toggles ignore-all and a follow-up confirms breakpoints
  are honored / ignored.
- `clear_breakpoints` empties `list_breakpoints`.
- `read_memory` returns base64-decoded bytes on an adapter that advertises
  `supports_read_memory_request`, and a clear `does not support` error otherwise.
- `list_history` reports the session's historic snapshots; `select_history` on a
  valid index makes the next `snapshot` reflect that frame, and an out-of-bounds
  index returns a clear error.
- `add_watch_expression` / `list_watch_expressions` / `remove_watch_expression`
  add, list, and remove watch expressions, re-evaluating each on stop.
- `list_modules` / `list_loaded_sources` return the loaded modules and sources
  when the adapter advertises support, and a clear `does not support` error
  otherwise.
- `control` step actions honor an explicit `granularity` (default `line`); the
  DAP step request carries `instruction` / `statement` when requested and the
  adapter advertises `supports_stepping_granularity`.
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
