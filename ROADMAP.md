# Roadmap

Planned work for the Zed debugger (DAP) feature and this test harness.

## Add Zed debug adapters (future feature)

These ecosystems are popular but Zed does not yet ship a debug adapter for
them. Build the adapter in `zed/crates/dap_adapters`, then add a matching
feature test here following the pattern used by the other language directories
(`golang/`, `javascript/`, `rust/`, `c/`, `typescript/`).

- [ ] Java / Kotlin — JDT debug adapter (`org.eclipse.jdt.ls` / vscode-java)
- [ ] C# / .NET — vsdbg / OmniSharp debug adapter
- [ ] Ruby — `rdbg` (debug gem) / ruby-debug-ide
- [ ] PHP — Xdebug / php-debug

Each new adapter needs:

1. An adapter in `zed/crates/dap_adapters/src/<lang>.rs`, registered in
   `dap_adapters.rs` (see `CodeLldbDebugAdapter`, `PythonDebugAdapter`,
   `JsDebugAdapter`, `GoDebugAdapter`, `GdbDebugAdapter`).
2. A `start_session` launch-config shape documented in `README.md`.
3. A single-file test covering breakpoint + snapshot, `step_in`/`step_out`,
   `run_to_line`, and `pause` (the same four defects as the existing languages).

## Rendering-fidelity tests (catch adapter gaps)

The four-defect tests prove launch/stepping/pause works. They do **not** prove
the adapter renders compound values correctly — the most language-specific part
of an adapter and the most likely to be broken. Add these rendering checks to
each custom adapter's test when building it (and optionally backfill them for
Rust/C++ under `CodeLLDB`).

For each language, the `snapshot` target should inspect the idiomatic compound
types. The pass criterion is "the value renders faithfully," not just "the
program prints the right number":

- **Rust** (`CodeLLDB`): a struct with named fields and an `Option`/`Result`
  enum — verify the enum renders as `Some(x)` (variant + payload), not a raw
  discriminant or `<no data>`. Also `String`/`Vec<T>` contents.
- **C++** (`CodeLLDB`): `std::vector<std::string>` and/or `std::map` — verify
  CodeLLDB's STL formatters expand the contents, not `_M_impl`/incomplete type.
  MinGW `libstdc++` formatters are the highest-risk spot.
- **Java** (JDT): `HashMap`/`ArrayList`/`Optional`/generics.
- **C#** (vsdbg/OmniSharp): `List<T>`/`Dictionary`/`Nullable<T>`.
- **Ruby** (rdbg): `Hash`/`Array`/objects with instance variables.
- **PHP** (Xdebug): associative arrays and objects.

Rendering fidelity is judged by reading `snapshot` output, so a "failure" may
be a genuine adapter gap rather than a test bug — that is the point of these
checks.

## Agent control of debugger-only features (planned)

Close the parity gap between what the debugger UI offers and what the agent's
debugger tool can control — step back first, then detach/restart/restart-frame,
data + exception breakpoints, memory read, and history snapshots. See
`plans/initial-plans/AGENT_DEBUGGER_CONTROL_PARITY.md`. Evaluate and set-variable
are tracked separately in
`plans/initial-plans/AGENT_EVALUATE_OPERATION_AND_UI_LOCKOUT.md`.
