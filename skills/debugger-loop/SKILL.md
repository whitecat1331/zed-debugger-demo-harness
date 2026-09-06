---
name: debugger-loop
description: Manage the Zed debugger-tool fix loop state (zed-debugger-demo/LOOP_STATE.json) and auto-update its position whenever the chat changes direction in the loop. Use when the user mentions the loop state or resume, or when the conversation shifts between testing/fixing/verifying (clippy)/rebuilding the debugger tool — including remapping commit SHAs after a rebase.
---

# Debugger Fix Loop

Own and keep current the state of the Zed debugger-tool fix loop. The loop is
a repeating cycle of four phases:

    run (acceptance suite) → fix (commit fixes) → verify (clippy) → restart (rebuild zed.exe) → run → …

The `verify` phase is itself a nested loop for clippy issues (see "Clippy
verify phase" below).

State lives in **`zed-debugger-demo/LOOP_STATE.json`**. This skill is the only
thing that should edit that file. Issue identity/status/cause lives in
**`zed-debugger-demo/ISSUES.json`**; this skill keeps the two reconciled.

## Auto-update on direction change

This skill is **not** only for explicit "update the loop state" requests.
Whenever the conversation's activity moves to a different phase of the loop,
update `LOOP_STATE.json` immediately and proactively — do not wait to be told.

Example: you are in the `run` phase and find a critical bug that forces a fix
and a rebuild. When the work turns to fixing, set `next_action: "fix"`; when
the fixes are committed, set `next_action: "verify"`; when clippy passes, set
`next_action: "restart"`; when the rebuild begins, set `next_action: "run"`.

Direction changes that require an update:

| Activity shift | Update |
|----------------|--------|
| Start/complete a test run | `next_action: "fix"`, set `last_report`, bump `iteration` |
| Start/complete a fix (commit) | `next_action: "verify"`, append `fixes_applied`, set `build_commit` |
| Start/complete clippy verify | drive the `verify` nested loop; when clean, `next_action: "restart"` |
| Start/complete a rebuild | `next_action: "run"` |
| Rebase / history rewrite | remap every SHA in `build_commit` + `fixes_applied` |

`next_action` is the source of truth for what to do next. Keep `phase` set to
the phase just completed for back-compat, but drive resume from `next_action`.

## Read state first

Always `read_file` `zed-debugger-demo/LOOP_STATE.json` before changing it, and
verify any commit SHA you write against real git output — never guess a hash.

## Schema

| Field | Meaning |
|-------|---------|
| `iteration` | 1-based count of completed `run` phases (test reports) |
| `phase` | The phase just completed: `run`, `fix`, `verify`, or `restart` (redundant with `next_action`) |
| `next_action` | The phase to do next: `run`, `fix`, `verify`, or `restart` (source of truth for resume) |
| `last_report` | Path to the latest acceptance report (relative to `zed-debugger-demo/`) |
| `action_plan` | Path to the in-progress plan of action |
| `build_commit` | The commit SHA the next build must be based on |
| `fixes_applied` | List of `{"name", "commits": ["crate:short-sha"], "issue"?}` objects |
| `verify` | State of the nested clippy loop: `{"state", "clippy_issues", "last_clippy_run"}` |
| `max_iterations` | Exit guard for the loop |
| `stall_key` | `ISSUES.json` ID that blocks the loop, or `null` when healthy |

## Phase cycle

`resume-loop.md` in `zed-debugger-demo/` is the resume entry point. The phases
run in order `run → fix → verify → restart → run`, and `next_action` is what to
do next:

- `next_action: "fix"` → fix the acceptance-suite failures and commit them.
- `next_action: "verify"` → run the clippy nested loop (below). When it comes
  back clean, set `next_action: "restart"`.
- `next_action: "restart"` → rebuild `zed.exe` at `build_commit` via
  `remote-compiler`, then launch a **new** Zed — do **not** kill the running
  one — via `zed-tools/loop/restart-zed.py`, which injects `--agent-prompt
  resume-loop.md`.
- `next_action: "run"` → run the acceptance suite.

## Clippy verify phase (nested loop)

`next_action: "verify"` runs a **nested** loop for clippy issues — the same
plan/execute/verify rhythm as the outer loop, but scoped to clippy output rather
than the debugger acceptance suite. It sits between `fix` and `restart` (remote
compile) so clippy failures never surprise the build again.

The nested loop is driven by `verify.state` in `LOOP_STATE.json`:

    verify_clippy → plan → execute → verify_clippy → … (until clean) → restart

1. **`verify_clippy`** — run clippy via the **`zed-verify`** skill
   (`./script/clippy` on the `compiler` VM; load `remote-compiler` first).
   Record results in `verify.last_clippy_run` and failures in
   `verify.clippy_issues`.
2. If clippy is **clean**, set `verify.state: "clean"`, then
   `next_action: "restart"` and leave the nested loop.
3. If clippy reports issues, set `verify.state: "plan"` — write down the
   clippy findings and the fix plan (`plan-manager` owns any plan doc).
4. **`execute`** — apply the fixes and commit them (`atomic-commits`, Zed
   style), appending to `fixes_applied` exactly like the outer `fix` phase.
5. Loop back to **`verify_clippy`** to confirm the fixes took, repeating until
   clippy is clean.

`verify.state` resets to `"pending"` each time a new outer `fix` phase begins.
If clippy loops more than a few times, stop and record the blocker rather than
spinning indefinitely.

## When to update

1. **After committing fixes**: append each fix to `fixes_applied` as a
   `{"name", "commits": ["crate:short-sha"], "issue"?}` object (set `issue` to
   an `ISSUES.json` ID when the fix addresses a tracked issue), set
   `build_commit` to the new `revive-debugger-tool` HEAD, set `phase` to
   `"fix"`, set `verify.state` to `"pending"`, and `next_action` to `"verify"`.
2. **After each clippy pass**: update `verify.state` and `verify.clippy_issues`
   as the nested loop advances (`verify_clippy` → `plan` → `execute` →
   `verify_clippy`). When clippy comes back clean, set `verify.state` to
   `"clean"`, `phase` to `"verify"`, and `next_action` to `"restart"`.
3. **After a rebase or history rewrite**: remap every SHA in `build_commit` and
   `fixes_applied` old→new, and set `build_commit` to the new HEAD. A rebase by
   itself does **not** advance `next_action`, `phase`, or `iteration`. Get the
   mapping from `git log --oneline main..revive-debugger-tool`.
4. **After a completed acceptance run**: set `last_report` to the new report
   path, bump `iteration`, set `phase` to `"run"`, and `next_action` to `"fix"`.
5. **After a completed rebuild**: set `phase` to `"restart"` and `next_action`
   to `"run"`.
6. **When the loop is blocked** by an `adapter-upstream`/`deferred` ledger
   issue, set `stall_key` to that `ISSUES.json` ID; clear it to `null` when
   unblocked.

Before recording state, reconcile `zed-debugger-demo/ISSUES.json` (mark resolved
issues, update `last_seen`, add new IDs) and run
`zed-tools/loop/check-loop-state.py` — it fails on drift. Always re-read and
re-verify the file after writing it.

## Location hygiene

The loop state, action plan, and reports live in `zed-debugger-demo/` (sibling
of the open-source `zed` fork). Never create loop-state or plan files inside
`zed`; personal scripts go in `zed-debugger-demo/zed-tools/`.

## Related skills

- `debugger-suite` — the `run` phase (acceptance suite).
- `zed-verify` — the `verify` phase (clippy nested loop).
- `remote-compiler` — the `restart` phase (Windows `zed.exe` build).
- `zed-tools/loop/restart-zed.py` — launches a fresh Zed with the resume prompt
  (non-destructive: never kill the running instance).
- `plan-manager` — owns the `action_plan` under `zed-debugger-demo/plans/`.
- `atomic-commits` — commit fixes (Zed style) before updating state.
