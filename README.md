# Zed Agent Debugger Tool — Test Project

This project exercises the agent **`debugger` tool** in the revived Zed PR
(#58439). It contains ten deliberate bugs, one per file in `bugs/` (bug 10 is
the "final boss").

The point is **not** to fix them by reading the code — it's to find and fix them
**using the debugger**, proving the revived debugger tool works end-to-end.

> **AI disclosure.** The majority of this harness was developed using DeepSeek V4 Pro,
> with assistance from Claude Sonnet 4.6 and Gemini 3.1 Pro.

## Hard-fork evidence

This harness produces the acceptance evidence the
[`whitecat1331/zed`](https://github.com/whitecat1331/zed) hard fork requires from
AI-assisted PRs — see the fork's `AI_POLICY.md`. A PR that used AI must attach a
full acceptance run through this suite: a completed, dated `TEST_REPORT-*.md`
covering the full adapter matrix (not a smoke run).

## Prerequisites

- Python 3.x
- `debugpy` (Zed's DAP adapter for Python). `pip install debugpy` if missing.

## How to run

```bash
python main.py
```

You'll see nine wrong results (and one hanging bug).

## How to debug (this is the actual test)

Use the agent's `debugger` tool:

1. `list_adapters` — see the Python/Debugpy adapter and its launch-config schema.
2. `start_session` — launch a Debugpy session for `main.py` (or a bug module).
3. `set_breakpoints` at the hinted line, then `control` (continue / step / run_to_line)
   and `snapshot` to inspect live state.
4. `list_sessions` to confirm active sessions; `stop_session` + `remove_breakpoints`
   to clean up at the end.

## Re-breaking the demo

After the agent has fixed the bugs, restore the broken state so the exercise can
be repeated:

```bash
python rebreak.py
```

`rebreak.py` applies the inverse of each canonical fix, returning every bug file
to its original broken state.

To verify the re-breaker actually worked, **use the `debugger` tool** rather than
just reading the files: set a breakpoint in a re-broken function and `snapshot`
the wrong value (proving it's broken again), then apply the fix and `snapshot`
the correct value (proving it's fixed). This exercises the debugger in both
directions — confirming something *is* broken and then that it *is not*.

## The bugs (hints, not answers)

### Bug 1 — off-by-one (`bugs/bug1_off_by_one.py`)
`sum_first_n_evens(5)` should be `20` but isn't.
**Hint:** breakpoint on the line updating `total`; step the first two iterations
and `snapshot` the loop variable. First value added should be `0`, last `8`.

### Bug 2 — shadowing / assignment vs accumulation (`bugs/bug2_shadowing.py`)
`format_report([10, 20, 30])` reports the wrong total and average.
**Hint:** breakpoint inside the loop; `snapshot` `total` each iteration. It
should *accumulate* (10 → 30 → 60), not get overwritten.

### Bug 3 — logic error (`bugs/bug3_condition.py`)
`is_in_range(50, 0, 10)` returns `True` but should be `False`.
**Hint:** breakpoint on the `return` line; `snapshot` `value`/`low`/`high`.
Inspect the boolean operator joining the two comparisons.

### Bug 4 — mutation during iteration (`bugs/bug4_mutation.py`)
`filter_even([1, 3, 2, 5, 4])` should be `[2, 4]` but returns `[3, 2, 4]`.
**Hint:** breakpoint inside the loop; `snapshot` the list before/after each
`remove`. Notice which element is *skipped*.

### Bug 5 — wrong-variable crash (`bugs/bug5_exception.py`)
`safe_divide(10, 0)` crashes with `ZeroDivisionError` instead of returning `0`.
**Hint:** breakpoint on the first line; `snapshot` `numerator` and `denominator`.
Which one should the guard actually check?

### Bug 6 — helper bug (`bugs/bug6_step_in.py`) — **step_in**
`final_price(100, True)` should be `80.0` but returns `120.0`.
**Hint:** breakpoint on the `apply_discount(price, percent)` call inside
`final_price`, then `step_in` and `snapshot` the formula inside `apply_discount`.

### Bug 7 — wrong return (`bugs/bug7_step_out.py`) — **step_out**
`report([10, 20, 30])` should be `Average: 20.00` but is `Average: 30.00`.
**Hint:** breakpoint on `return total / count` inside `compute_average`,
`snapshot` `total` and `count`, then `step_out` and `snapshot` the returned value.

### Bug 8 — line corruption (`bugs/bug8_run_to_line.py`) — **run_to_line**
`process([1, 2, 3])` should be `[2, 4, 6]` but returns `[1002, 1004, 1006]`.
**Hint:** `run_to_line` straight to the line `result[-1] += 1000` (no breakpoint),
then `snapshot` to see the corruption.

### Bug 9 — infinite loop (`bugs/bug9_pause.py`) — **pause**
`find_divisor(9)` should return `3` but hangs forever.
**Hint:** run `bugs/bug9_pause.py` in a session (it hangs), then `control` with
`pause` and `snapshot` to see `i` stuck at `2`.

### Bug 10 — maximum product subarray (`bugs/bug10_final_boss.py`) — **final boss**
`max_product_subarray([-2, 3, -4])` should be `24` but returns something smaller.
No category hint this time — you have to find the bug on your own.

**Hints (read in order, only if stuck):**
1. Verify which inputs fail: `[2, 3, -2, 4]` happens to be correct, but
   `[-2, 3, -4]` is wrong. What is different about the failing case?
2. Breakpoint inside the loop and `snapshot` the running product for
   `[-2, 3, -4]` step by step. At each step ask: is the *largest product* the
   same as the *largest running value* you're tracking?
3. Multiplying two negatives makes a positive. When the current number is
   negative, a small (very negative) running product can become the largest on
   the next step. What second value do you need to keep track of?

## Success criteria

Once the debugger tool can find and explain each root cause, apply the fixes and
`python main.py` prints the expected results with no crash (bug 9 fixed
separately). Then run `python rebreak.py` and use the debugger to confirm the
bugs are broken again.

## Cross-language adapter tests

The Python `bugs/` prove the agent `debugger` tool works against `Debugpy`.
The directories below prove the same tool against the remaining bundled
adapters. They are **feature tests**, not ten-bug clones: each one targets the
capabilities that actually differ between adapters — `step_in`/`step_out`,
`run_to_line`, `pause` — plus basic breakpoint + snapshot.

See [`TESTING.md`](TESTING.md) for the agent test brief that drives the whole
suite (Python + cross-language),
[`test-reports/TEST_REPORT_TEMPLATE.md`](test-reports/TEST_REPORT_TEMPLATE.md)
for the fill-in report template (completed reports go in
[`test-reports/`](test-reports/)), and [`REBREAKING.md`](REBREAKING.md) for how
to fix and re-break the shared defects.

### Adapter matrix

| Language | `adapter` value | Directory | Build before launch |
|----------|-----------------|-----------|---------------------|
| Python | `Debugpy` | `bugs/`, `main.py` | none |
| JavaScript | `JavaScript` | `javascript/` | none |
| TypeScript | `JavaScript` | `typescript/` | `npm install && npm run build` |
| Go | `Delve` | `golang/` | none (Delve builds the package) |
| Rust | `CodeLLDB` | `rust/` | `cargo build` |
| C | `GDB` | `c/` | `gcc -g -O0 main.c -o main` |

### What each program covers

Every non-Python `main` file contains the same four deliberate defects, one per
capability:

| Function | Debugger capability | What to prove |
|----------|--------------------|---------------|
| `apply_discount` | `step_in` / `step_out` | breakpoint on the call, `step_in`, snapshot `price`/`percent`, `step_out` |
| `sum_even` | breakpoint + `snapshot` | off-by-one — snapshot the accumulator each iteration |
| `process` (JS/TS: `processValues`) | `run_to_line` | run straight to the `+= 1000` corruption line, then snapshot |
| `find_divisor` | `pause` | launch with `--hang`, then `pause` and snapshot `i` stuck |

Each function is annotated in source with the exact bug and the capability it
exercises, mirroring the Python hints.

### Build & run

```bash
# JavaScript
node javascript/main.js                 # wrong output
node javascript/main.js --hang          # hangs (use pause)

# TypeScript (compile first — the adapter launches dist/main.js via source maps)
cd typescript && npm install && npm run build
node typescript/dist/main.js            # wrong output
node typescript/dist/main.js --hang     # hangs (use pause)

# Go
go run ./golang                        # wrong output (or: cd golang && go run .)
go run ./golang --hang                  # hangs (use pause)

# Rust
cargo build --manifest-path rust/Cargo.toml
./rust/target/debug/rust-demo           # wrong output
./rust/target/debug/rust-demo --hang    # hangs (use pause)

# C (GDB adapter)
gcc -g -O0 c/main.c -o c/main           # or cl /Zi c/main.c
./c/main                                # wrong output
./c/main --hang                         # hangs (use pause)
```

On Windows the Rust binary is `rust-demo.exe` and the C binary is `main.exe`.

### `start_session` launch configs

Use `list_adapters` first to confirm the adapter name and schema. `<repo>` below
means the absolute path to this repository. The tool auto-adds `stopOnEntry`
for launch configs, but including it is harmless.

**Spread the launch-config fields at the scenario top level** — do not nest
them under a `"config"` key. The nested form is silently rejected
(`start_session` returns a session_id that never appears in `list_sessions`).

**JavaScript** (`type` is required by the adapter):
```json
{
  "adapter": "JavaScript",
  "label": "JS feature test",
  "type": "pwa-node",
  "request": "launch",
  "program": "<repo>/javascript/main.js",
  "cwd": "<repo>/javascript",
  "stopOnEntry": true
}
```

**TypeScript** (JavaScript adapter; launch compiled `dist/main.js` — breakpoints set in `main.ts` resolve via source maps):
```json
{
  "adapter": "JavaScript",
  "label": "TypeScript feature test",
  "type": "pwa-node",
  "request": "launch",
  "program": "<repo>/typescript/dist/main.js",
  "cwd": "<repo>/typescript",
  "stopOnEntry": true
}
```

**Go** (`program` is the package directory; `mode: debug` builds it):
```json
{
  "adapter": "Delve",
  "label": "Go feature test",
  "request": "launch",
  "mode": "debug",
  "program": ".",
  "cwd": "<repo>/golang",
  "stopOnEntry": true
}
```

**Rust** (launch the compiled binary):
```json
{
  "adapter": "CodeLLDB",
  "label": "Rust feature test",
  "request": "launch",
  "program": "<repo>/rust/target/debug/rust-demo",
  "cwd": "<repo>/rust",
  "stopOnEntry": true
}
```

**C via GDB** (uses `stopAtBeginningOfMainSubprogram`):
```json
{
  "adapter": "GDB",
  "label": "C feature test",
  "request": "launch",
  "program": "<repo>/c/main",
  "cwd": "<repo>/c",
  "stopAtBeginningOfMainSubprogram": true
}
```

For the `pause` test, add `"args": ["--hang"]` to the launch config and use the
`control` operation with `pause` instead of setting breakpoints.

### Toolchain prerequisites

- **JavaScript**: a Node runtime (Zed auto-downloads `vscode-js-debug`).
- **TypeScript**: a Node runtime plus the TypeScript compiler (`npm install` in
  `typescript/`). Same `vscode-js-debug` adapter as JavaScript; source maps map
  breakpoints set in `main.ts` to `dist/main.js`.
- **Go**: the Go toolchain — Zed auto-installs `dlv` and its DAP shim if missing.
- **Rust**: `cargo`/`rustc`; `debug = 2` is set in `rust/Cargo.toml`. CodeLLDB
  is auto-downloaded by Zed.
- **C**: a C compiler plus a system `gdb` for the GDB adapter. Compile with
  `-g -O0`.

### Notes

- `run_to_line` (the `process` defect) and `pause` (the `find_divisor` defect)
  are the two capabilities most likely to be flaky or unsupported on a given
  adapter — that is exactly why each language exercises them.
- The Python suite remains the authoritative ten-bug reference; these are
  single-file smoke tests, so instead of a per-language `rebreak.py` they rely
  on [`REBREAKING.md`](REBREAKING.md) to document how to fix and re-break each
  defect by hand.

### Planned adapters

Zed does not yet ship debug adapters for Java/Kotlin, C#, Ruby, or PHP. These
are tracked as future work in [`ROADMAP.md`](ROADMAP.md): build the adapter in
`zed/crates/dap_adapters`, then add a matching test here.


## Documentation

- [`DEVELOPER_INIT.md`](DEVELOPER_INIT.md) — one-time setup to get the suite ready to drive.
- [`DRIVING_THE_SUITE.md`](DRIVING_THE_SUITE.md) — how to run the suite: with the individual skills, or via the `debugger-loop`.
- [`TESTING.md`](TESTING.md) — the agent test brief (authoritative).
- [`REBREAKING.md`](REBREAKING.md) — how to fix and re-break the shared defects.
- [`ROADMAP.md`](ROADMAP.md) — planned adapters and rendering-fidelity work.
