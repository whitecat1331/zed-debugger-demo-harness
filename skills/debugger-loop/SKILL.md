---
name: debugger-loop
description: Own and keep current the state of the Zed debugger-tool fix loop (stage, test, verify, restart, run, fix). Use when resuming or updating the loop state in zed-debugger-demo/LOOP_STATE.json and ISSUES.json.
---

# Debugger Fix Loop

Own and keep current the state of the Zed debugger-tool fix loop. The loop is
a repeating cycle of six phases:

```
stage → test → verify → restart → run → fix → …
```

`verify` is itself a nested loop for clippy (see "Clippy verify phase" below),
and `test` is a nested loop for test coverage (see the `debugger-test-gate`
skill). `stage` re-checks between every phase, so new work is never missed.

State lives in **`zed-debugger-demo/LOOP_STATE.json`**. This skill is the only
thing that should edit that file (the `debugger-stage` skill drives it
mechanically via `stage.py`). Issue identity/status/cause lives in
**`zed-debugger-demo/ISSUES.json`**; this skill keeps the two reconciled.

## Read state first

Always `read_file` `zed-debugger-demo/LOOP_STATE.json` and
`zed-debugger-demo/ISSUES.json` before changing either, and verify any commit
SHA you write against real git output — never guess a hash. After writing,
re-read and re-run `zed-tools/loop/check-loop-state.py` (it fails on drift).

`continue` is a context-economy device: to begin, read **only** the two state
files plus the one phase's script/skill section. Do not re-read reports, plans,
or docs unless the phase explicitly requires them. `check-loop-state.py` is the
one full-context consumer; a resume is not.

## Schema — `LOOP_STATE.json`

| Field | Meaning |
|-------|---------|
| `phase` | The phase just completed (redundant with `next_action`, kept for back-compat) |
| `next_action` | The phase to do next: `stage`, `test`, `verify`, `restart`, `run`, `fix`, or `complete` (source of truth for resume) |
| `active_issue` | The issue currently being worked (e.g. `"ISSUE-0016"`), or `null` when clear. **This is the loop's index** — derived from `ISSUES.json`, never a separate counter |
| `last_report` | Path to the latest acceptance report (relative to `zed-debugger-demo/`) |
| `action_plan` | Path to the in-progress plan of action |
| `build_commit` | The commit SHA the next build must be based on |
| `changes_introduced` | Change manifest seeding the current triage: list of `{"name", "commits": ["crate:short-sha"], "files"?, "adapters"?, "capabilities"?, "notes"?}` |
| `fixes_applied` | List of `{"name", "commits": ["crate:short-sha"], "issue"?}` objects |
| `verify` | State of the nested clippy loop: `{"state", "clippy_issues", "last_clippy_run"}` |
| `stall_key` | `ISSUES.json` ID that blocks the loop, or `null` when healthy |
| `run_count` | Integer, incremented once per `run` phase. A coarse "how far along" signal, distinct from the `ISSUE` index |
| `pending_validation` | List of `{capability, adapter, why}` that must be exercised full (not smoke) on the next `run`; cleared after a clean full run |
| `next_plan` | Plan path the idle loop recommends implementing next, or `null` (see "Idle plan triage") |

There is **no `iteration` or `max_iterations`** gate. The index is the `ISSUE`
number itself; `run_count` is a progress counter, not a loop bound.

## Schema — `ISSUES.json`

One record per issue, stable ID `ISSUE-0000` (zero-padded, monotonic, **never
reused**). `DAP-*`/`HOST-*` are retired; the `adapter` field carries the
category. Fields: `id`, `title`, `classification`, `severity`, `adapter`,
`capability`, `status`, `first_seen`, `last_seen`, `owning_commits`,
`resolution`, `cause`, `regression_of`, and optionally `parent` (sub-issues)
and `fix_attempts`.

- `status`: `open | in-progress | resolved | deferred | adapter-upstream`.
- `regression_of`: the ID of the prior occurrence this one regressed from, or
  `null`. Forms a chain — see "Regression handling".
- `severity` (`P0|P1|P2`) doubles as the tier for ordering.
- `cause.evidence`: optional list of file paths (relative to
  `zed-debugger-demo/`) that substantiate the cause — a DAP trace, a log
  snippet, or a report. Required once `fix_attempts >= 2`; the linter checks
  each path exists.

## Phase cycle

`next_action` is what to do next — treat each as a **dispatch**: one script or
skill per phase, with the state files as the only shared input:

- `stage` → run `zed-tools/loop/stage.py` (see the `debugger-stage` skill).
  Detect new commits/plans/changes, advance `build_commit`, recompute
  `active_issue`, re-point per the re-point rule.
- `test` → run the `debugger-test-gate` skill (source tests + harness coverage
  + source-current). On pass, set `next_action = "verify"`.
- `verify` → run the clippy nested loop (`zed-verify` on the `compiler` VM).
  When clean, set `next_action = "restart"`.
- `restart` → rebuild `zed.exe` at `build_commit` via `remote-compiler`, then
  launch a **new** Zed (do **not** kill the running one) via
  `zed-tools/loop/restart-zed.py` (injects `--agent-prompt resume-loop.md`).
  Then `next_action = "run"`.
- `run` → run the acceptance suite (`debugger-suite` skill), then increment
  `run_count`. If `pending_validation` is non-empty, those paths must be run
  **full** (never carried forward as smoke). On issues found, set
  `next_action = "fix"`; on clean, mark the issue `resolved`, advance
  `active_issue`, clear `pending_validation`, run the run → stage
  reconciliation (below), then set `next_action = "stage"` (or `complete` if
  `active_issue` is `null`).
- `fix` → fix the failures, commit via `atomic-commits`, append `fixes_applied`,
  set `build_commit`, then `next_action = "verify"`. Before a 2nd-or-later
  attempt on the same issue, gate on "Instrument vs. fix" first.
- `complete` → the loop is idle (`active_issue == null`, no open issues). Run
  the **idle plan triage** (below), record `next_plan`, and report it in one
  line.

## Re-point rule (never a full reset)

The loop **continues** by default. It re-points only when the build is stale:

| Change detected | `next_action` |
|---|---|
| New commits (code) | `verify` (or `test` if a new plan also landed) |
| New issue (no code) | `fix` (set by `run`, not the stager) |
| New plan, no commits | continue (record only) |
| Nothing new | continue |

Invariant: **`run` never executes against a stale build** — so new code always
flows back through `verify`/`restart` before `run`.

## Priority ordering (`active_issue`)

`active_issue` is computed from open `ISSUES.json` records, ordered by:

```
severity tier (P0 → P1 → P2) → dependency (child before parent) → number
```

It is **derived**, not stored as a separate counter, so it can't drift.

## Regression handling

A regression **mints a new `ISSUE` number** with `regression_of` pointing to the
immediate prior occurrence. A `resolved` issue is frozen — never re-open it.

```
ISSUE-0003 (original)  → resolved
ISSUE-0018 → regression_of: "ISSUE-0003"  → resolved
ISSUE-0021 → regression_of: "ISSUE-0018"  → open
```

This keeps the index monotonic and each regression a datable, countable event.
Before minting a regression, confirm it is the same root cause (else it is a
new, unrelated issue — no link).

## Progress vs attempts

- **Resolve a top-level issue** (and its whole cluster) → its `status` becomes
  `resolved`; `active_issue` advances to the next open issue.
- **Fail a fix attempt** → increment that issue's `fix_attempts`; leave
  `active_issue` alone.
- **`fix_attempts` is per-issue.** A sub-issue gets its own 3-try budget; finding
  a sub-issue is *discovery*, not a failed attempt (record it, don't touch the
  parent's counter).
- **`fix_attempts` reaches `FIX_ATTEMPTS_CAP` (3)** → the issue isn't converging.
  The exit status is chosen by **evidence**, not by the cap:
  - `adapter-upstream` requires `cause.state == "confirmed"` **and** a
    `cause.root_cause` that names the adapter's specific behavior, backed by a
    wire/protocol trace (or equivalent direct observation). Otherwise the
    honest exit is `deferred` — reaching the cap proves "budget exhausted,"
    not "fault is upstream."
  - If the issue blocks the parent, the cluster stalls: set `stall_key` and
    move on.

## Run → stage reconciliation

A clean `run` → `stage` transition is not just "advance `active_issue`." It
must also reconcile loop process state before continuing:

1. **Plan-completion gate** — run the plan-manager completeness gate over
   `plans/in-progress-plans/`; if a plan's phases are all done and validated,
   ask the user before completing it (never auto-complete).
2. **Prune `changes_introduced`** — after a clean run, append its entries to
   `zed-debugger-demo/tmp/changes_introduced.archive.json` (append-only; `tmp/`
   is git-ignored) and clear the field. It seeds the *current* triage only;
   letting it accumulate breaks its "mirror of `fixes_applied`" relationship.
3. **Close-out when `active_issue` is `null`** — apply the terminal/close-out
   policy below instead of idling at `stage`.

### Terminal / close-out state

When `active_issue` is `null` (every open issue is `resolved`,
`adapter-upstream`, or `deferred`), the loop is **complete**, not merely
between iterations. Set `next_action = "complete"` (the linter enforces that
this implies no open issues), apply the `adapter-upstream` backlog policy, and
run the **idle plan triage** (below).

- **File upstream** — if the adapter behavior is `confirmed` (see
  "Progress vs attempts"), open/attach an upstream report carrying the
  wire/protocol trace.
- **Document-as-accepted** — record a confirmed-but-tolerated behavior as a
  known limitation in the report/README rather than an open issue.
- **Park (`deferred`)** — leave the issue `deferred` with a reason; it does not
  block the loop.

### Idle plan triage

At `next_action = "complete"`, recommend the next plan work instead of idling:

1. Sweep `plans/in-progress-plans/`: a plan with `Status: done` still sitting
   there is a plan-manager completeness-gate candidate (move to `completed/`,
   awaiting approval) — not a next action. A plan with open phases → recommend
   its most imminent next step.
2. If every in-progress plan is implemented, sweep `plans/initial-plans/`:
   prefer `Stage: plan` over `Stage: draft`, and recommend the highest-value one
   to promote and implement.
3. Record the recommendation in `LOOP_STATE.json` as `next_plan`, so a bare
   `@debugger-loop continue` at idle reports "no bugs; recommended next plan: X"
   in one line.

### Watch-list → issue promotion

An observation found while running the suite is a **watch-list item**, not yet
an issue. Promote it to an `ISSUES.json` record only when it **recurs across
two reports** (same adapter + capability + symptom). A single occurrence is
documented as known/non-blocking and does **not** silently accumulate — it is
dismissed or left as a watch-list note, never minted as a half-formed issue.

## Instrument vs. fix (stop guessing)

A failed fix returns ~zero information; an instrumented reproduction returns the
data that splits the remaining hypotheses. Switch to observation **before**
writing another patch when any of these hold:

- `fix_attempts ≥ 1` on the issue (one failed attempt) — do **not** wait for
  the cap (3). The cap is a give-up budget, not a switch-tools trigger.
- The `cause` is a *what* (reproducible symptom), not a *why* (mechanism down to
  a specific line/decision). "Confirmed symptom" ≠ "confirmed cause".
- The bug crosses a process/protocol boundary (DAP, IPC, child-process,
  reverse-request, network). Reading one side's source cannot resolve it.
- A hypothesis is a claim about *another component's* behavior that was
  **inferred**, not observed (e.g. "the adapter doesn't re-send X" from the
  *absence* of a log line).

Gate on the `fix` phase: before a 2nd-or-later attempt on the same issue, name
the one observation that would discriminate the remaining hypotheses, then
produce it (log line, wire trace, or breakpoint) before writing the patch.

The first attempt is a free *guess*, not a free *coin-flip*: even before the
first patch, name the hypothesis it tests — what you believe and why. The gate
upgrades that requirement from "name the hypothesis" (attempt 1) to "observe
before patching" (attempt 2 onward).

Observation order is a **decision**, not a fixed sequence:

1. **If a process/protocol boundary is already implicated** (DAP, IPC,
   child-process, reverse-request), observe with the **wire/protocol trace**
   directly — the DAP logger / packet dump. It sees the same transport point as
   a boundary log but also carries message contents, at near-zero extra cost
   and no rebuild.
2. **Boundary log line** — a `log::info!` at the transport/protocol layer. Use
   it only to *locate or confirm* that a boundary is involved, not to diagnose
   a boundary you already know about.
3. **Source-level debugger (`CodeLLDB`)** — reserve for **deterministic,
   already-localized** code questions (you know the side and a few lines). For
   timing-sensitive/async bugs, the wire trace is the **terminal** observation:
   breakpoints perturb scheduling and can make the race vanish. Pay for the
   debug-symbols build only after the cheaper probes have localized you to one
   side.

## Sub-issues and the three-case tiebreaker

A failure found *while* fixing an issue is one of three things:

1. **Same root cause, second symptom** — fold into the parent's `cause`/
   `verification`; no new record.
2. **Blocking sub-issue** — add a record with `"parent": "<parent-id>"`; the
   parent is `resolved` only when every child is.
3. **Unrelated** — new top-level `ISSUE` ID (no `parent`).

Tiebreaker: *"can I fix the current issue without also fixing this one?"* No →
sub-issue; yes → same root cause (fold) or independent (new).

`changes_introduced` is the mirror of `fixes_applied`: seed it at the start of a
batch (or let the stager auto-seed it) so the first run can triage failures
against it. Always run the **full** suite; use `changes_introduced` to decide
where to look first, never to scope the run.

## Clippy verify phase (nested loop)

Driven by `verify.state`:

```
verify_clippy → plan → execute → verify_clippy → … (until clean) → restart
```

1. `verify_clippy` — run `./script/clippy` via `zed-verify` (`remote-compiler`
   first). Record results in `verify.last_clippy_run` / `verify.clippy_issues`.
2. Clean → `verify.state = "clean"`, `next_action = "restart"`.
3. Dirty → `verify.state = "plan"`, write the plan, fix + commit
   (`atomic-commits`), append to `fixes_applied`, loop.
4. If clippy loops more than a few times, stop and record the blocker.

`verify.state` resets to `"pending"` each time a new outer `fix` begins.

## Auto-update on direction change

Update `LOOP_STATE.json` proactively whenever the conversation's activity moves
to a different phase — do not wait to be told:

| Activity shift | Update |
|---|---|
| Stage new work | drive `stage.py`; set `next_action` per re-point |
| Start/complete a test-gate pass | `next_action = "verify"` (or stay `test`) |
| Start/complete clippy verify | drive `verify` nested loop; clean → `restart` |
| Start/complete a fix (commit) | `next_action = "verify"`, append `fixes_applied`, set `build_commit` |
| Start/complete a rebuild | `next_action = "run"` |
| Complete an acceptance run | set `last_report`; `fix` on red, or mark resolved + advance `active_issue` on green |
| Rebase / history rewrite | remap every SHA in `build_commit` + `fixes_applied` |

## Location hygiene

The loop state, action plan, and reports live in `zed-debugger-demo/` (sibling
of the open-source `zed` fork). Never create loop-state or plan files inside
`zed`; personal scripts go in `zed-debugger-demo/zed-tools/`.

## Related skills

- `debugger-stage` — the `stage` phase (detect + reconcile via `stage.py`).
- `debugger-test-gate` — the `test` phase (source + harness coverage gate).
- `debugger-suite` — the `run` phase (acceptance suite).
- `zed-verify` — the `verify` phase (clippy nested loop).
- `remote-compiler` — the `restart` phase (Windows `zed.exe` build).
- `zed-tools/loop/restart-zed.py` — launches a fresh Zed with the resume prompt.
- `plan-manager` — owns the `action_plan` under `zed-debugger-demo/plans/`.
- `atomic-commits` — commit fixes (Zed style) before updating state.
