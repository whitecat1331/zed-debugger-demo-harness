# Re-breaking the cross-language tests

The Python suite uses `rebreak.py` to restore its bugs. The non-Python tests
(`golang/`, `javascript/`, `rust/`, `c/`, `typescript/`) deliberately do **not**
have a re-breaker. This file is the substitute: it documents the four shared
defects and their exact inverses, so an agent can apply a fix (un-break), verify
it with the debugger, then re-apply the bug (re-break) by hand.

## The four defects (shared by every language)

Every non-Python `main` file contains the same four defects. The "fix" and
"re-break" for each are exact inverses.

### 1. `apply_discount` — `step_in` / `step_out`

- **Broken:** adds the discount instead of subtracting it, so
  `apply_discount(100, 20)` returns `120` instead of `80`.
- **Fix:** change the sign inside the parentheses:
  `(1 + percent/100)` → `(1 - percent/100)`.
- **Re-break:** change `-` back to `+`.

### 2. `sum_even` — breakpoint + `snapshot`

- **Broken:** the loop bound is off-by-one, so `sum_even(5)` returns `30`
  instead of `20` (it includes the `2*n` term).
- **Fix:** make the bound exclusive: `i <= n` → `i < n`
  (Rust: `0..=n` → `0..n`).
- **Re-break:** make it inclusive again.

### 3. `process` / `processValues` — `run_to_line`

- **Broken:** after the doubling loop, a corruption line adds `1000` to the
  last element (`result[last] += 1000`, `result[len-1] += 1000`,
  `result[result.length - 1] += 1000`, or `out[n - 1] += 1000`).
- **Fix:** delete the corruption line (and, in Rust, the `let last = …` helper
  if it is now unused).
- **Re-break:** re-add the corruption line.

### 4. `find_divisor` — `pause`

- **Broken:** the loop counter never advances, so `find_divisor(9)` hangs.
- **Fix:** add the missing increment inside the loop body:
  Go/JS/TS `i++`, Rust `i += 1`, C `++i`.
- **Re-break:** remove the increment again.

## Per-language function names

| Defect | Go | JavaScript / TypeScript | Rust | C |
|--------|----|-------------------------|------|---|
| 1 | `applyDiscount` | `applyDiscount` | `apply_discount` | `apply_discount` |
| 2 | `sumEven` | `sumEven` | `sum_even` | `sum_even` |
| 3 | `process` | `processValues` | `process` | `process` |
| 4 | `findDivisor` | `findDivisor` | `find_divisor` | `find_divisor` |

> JavaScript and TypeScript name defect 3 `processValues` (not `process`) to
> avoid shadowing Node's global `process` object.

## Per-language syntax for the syntax-sensitive fixes

The defects are language-agnostic, but two of the fixes are syntax-sensitive.
The table below shows the broken → fixed form for each language.

> **Canonical fix forms** — `rebreak.py` inverts specific fix snippets, so
> prefer these forms when fixing so the re-breaker matches:
> - Defect 2 (bug 4 equivalent): `for value in values[:]:` (the rebreaker also
>   accepts `list(values)`).
> - Defect 3: delete the corruption line entirely.
> - Defect 4: add the increment exactly (`i++`, `i += 1`, `++i`).
> - Python bug 10: use the swap form (`if num < 0: current_max, current_min =
>   current_min, current_max`) — the rebreaker also accepts the
>   `previous_max`/no-swap variant.

| Defect | Go | JavaScript / TypeScript | Rust | C |
|--------|----|-------------------------|------|---|
| 1 (sign) | `(1 + percent/100)` → `(1 - percent/100)` | `(1 + percent / 100)` → `(1 - percent / 100)` | `(1.0 + percent / 100.0)` → `(1.0 - percent / 100.0)` | `(1 + percent / 100)` → `(1 - percent / 100)` |
| 2 (bound) | `i <= n` → `i < n` | `i <= n` → `i < n` | `0..=n` → `0..n` | `i <= n` → `i < n` |
| 4 (increment) | add `i++` | add `i++` | add `i += 1` | add `++i` |

## Verification workflow

Do **not** verify by reading the file — use the `debugger` tool, the same way
the Python suite is re-verified:

1. **Un-break:** apply the fix above.
2. **Confirm fixed:** run the program normally and confirm the expected output
   (see the `(expected …)` annotations in each `main` file). Optionally
   `start_session`, `set_breakpoints` at the fixed line, and `snapshot` the
   now-correct value.
3. **Re-break:** apply the inverse.
4. **Confirm re-broken:** `snapshot` the wrong value again (e.g. `sum_even(5)`
   accumulates to `30`, or `find_divisor` hangs and needs `pause`).

Each source file already carries inline `BUG:` comments marking the defect, so
an agent can cross-check this doc against the code while editing.
