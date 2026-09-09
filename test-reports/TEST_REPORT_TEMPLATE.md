# Test report — Zed debugger-tool suite

> Template — do not fill this file in place. Copy it to
> `test-reports/TEST_REPORT-YYYY-MM-DD-HHMM.md` at the start of a run and fill
> in that copy.

## Run metadata

- Date:
- Zed build / commit:
- Agent / model:
- Platform (OS):

## Legend

- **Found** — bug identified via `snapshot` (not by reading).
- **Fixed** — source corrected and the correct value confirmed via `snapshot`.
- **Re-broken** — inverse applied (see `REBREAKING.md`) and the wrong value
  confirmed via `snapshot`.

## Summary

- [ ] Python (`Debugpy`) — all 10 bugs
- [ ] JavaScript (`JavaScript`) — 4 defects
- [ ] TypeScript (`JavaScript`, source maps) — 4 defects
- [ ] Go (`Delve`) — 4 defects
- [ ] Rust (`CodeLLDB`) — 4 defects
- [ ] C (`GDB`) — 4 defects
- [ ] Re-break pass completed for every language
- [ ] `evaluate` + `set_variable` exercised for every adapter

## Python (`Debugpy`)

| Bug | Capability | Found | Fixed | Re-broken |
|-----|------------|:-----:|:-----:|:---------:|
| 1 — off-by-one | breakpoint + snapshot | [ ] | [ ] | [ ] |
| 2 — shadowing | breakpoint + snapshot | [ ] | [ ] | [ ] |
| 3 — condition | breakpoint + snapshot | [ ] | [ ] | [ ] |
| 4 — mutation | breakpoint + snapshot | [ ] | [ ] | [ ] |
| 5 — exception | breakpoint + snapshot | [ ] | [ ] | [ ] |
| 6 — step in | `step_in` | [ ] | [ ] | [ ] |
| 7 — step out | `step_out` | [ ] | [ ] | [ ] |
| 8 — run to line | `run_to_line` | [ ] | [ ] | [ ] |
| 9 — pause | `pause` | [ ] | [ ] | [ ] |
| 10 — final boss | all | [ ] | [ ] | [ ] |

## Cross-language

### JavaScript (`JavaScript`) — `javascript/`

| Defect (function) | Capability | Found | Fixed | Re-broken |
|-------------------|------------|:-----:|:-----:|:---------:|
| `applyDiscount` | `step_in` / `step_out` | [ ] | [ ] | [ ] |
| `sumEven` | breakpoint + snapshot | [ ] | [ ] | [ ] |
| `processValues` | `run_to_line` | [ ] | [ ] | [ ] |
| `findDivisor` | `pause` | [ ] | [ ] | [ ] |

### TypeScript (`JavaScript`) — `typescript/`

| Defect (function) | Capability | Found | Fixed | Re-broken |
|-------------------|------------|:-----:|:-----:|:---------:|
| `applyDiscount` | `step_in` / `step_out` | [ ] | [ ] | [ ] |
| `sumEven` | breakpoint + snapshot | [ ] | [ ] | [ ] |
| `processValues` | `run_to_line` | [ ] | [ ] | [ ] |
| `findDivisor` | `pause` | [ ] | [ ] | [ ] |

### Go (`Delve`) — `golang/`

| Defect (function) | Capability | Found | Fixed | Re-broken |
|-------------------|------------|:-----:|:-----:|:---------:|
| `applyDiscount` | `step_in` / `step_out` | [ ] | [ ] | [ ] |
| `sumEven` | breakpoint + snapshot | [ ] | [ ] | [ ] |
| `process` | `run_to_line` | [ ] | [ ] | [ ] |
| `findDivisor` | `pause` | [ ] | [ ] | [ ] |

### Rust (`CodeLLDB`) — `rust/`

| Defect (function) | Capability | Found | Fixed | Re-broken |
|-------------------|------------|:-----:|:-----:|:---------:|
| `apply_discount` | `step_in` / `step_out` | [ ] | [ ] | [ ] |
| `sum_even` | breakpoint + snapshot | [ ] | [ ] | [ ] |
| `process` | `run_to_line` | [ ] | [ ] | [ ] |
| `find_divisor` | `pause` | [ ] | [ ] | [ ] |

### C (`GDB`) — `c/`

| Defect (function) | Capability | Found | Fixed | Re-broken |
|-------------------|------------|:-----:|:-----:|:---------:|
| `apply_discount` | `step_in` / `step_out` | [ ] | [ ] | [ ] |
| `sum_even` | breakpoint + snapshot | [ ] | [ ] | [ ] |
| `process` | `run_to_line` | [ ] | [ ] | [ ] |
| `find_divisor` | `pause` | [ ] | [ ] | [ ] |

## Evaluate / set_variable (new operations)

| Adapter | `evaluate` correct result | `set_variable` mutates + snapshot confirms |
|---------|:-------------------------:|:------------------------------------------:|
| `Debugpy` | [ ] | [ ] |
| `JavaScript` | [ ] | [ ] |
| `Delve` | [ ] | [ ] |
| `CodeLLDB` | [ ] | [ ] |
| `GDB` | [ ] | [ ] |

## Findings

Keyed by stable issue ID from `ISSUES.json` (never prose "prior finding N").
Carry forward still-open issues from the previous report and mark each row's
status this run.

| ID | Title | Status this run | Cause |
|----|-------|-----------------|-------|
| `ISSUE-0001` | Delve reports no threads | still-open | Hypothesis (medium) |
| `ISSUE-0006` | GDB stdout not forwarded | resolved | Confirmed |
| `ISSUE-00xx` | ... | new | Unknown |

Cause column is one of: `Confirmed`, `Hypothesis (high)`, `Hypothesis (medium)`,
or `Unknown`.

## Cause assessment

Record each finding's cause in exactly one of three states, and never guess:

- **Confirmed** — root cause proven; include the verification (snapshot / commit).
- **Hypothesized** — one or more `{cause, confidence, basis}` leads; confidence
  is `high` or `medium` only, and each lead must state its evidence.
- **Unknown** — no signal; say so explicitly. `low`/speculative is not allowed;
  if that is all you have, it is `unknown`.

## Sign-off

- [ ] All six languages pass the acceptance criteria in `TESTING.md`
- [ ] `evaluate` and `set_variable` pass for every adapter
- [ ] Every bug re-broken; repo left in its broken state
- [ ] Findings above are complete
