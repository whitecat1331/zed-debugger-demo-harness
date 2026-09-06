# Developer Init

One-time setup to get the debugger-tool acceptance suite ready to drive.

## 1. Get a Zed build with the debugger tool

The suite drives Zed's **agent `debugger` tool** (the DAP client). You need a Zed
build where that tool is present and enabled. The reference implementation is the
`revive-debugger-tool` branch of the Zed fork.

- Build with `--release` (debug builds panic on dev asset loading).
- On Windows, produce a runnable set in one folder: `zed.exe`, `cli.exe`,
  `conpty.dll`, `OpenConsole.exe`.

## 2. Install the language toolchains

| Language | Adapter | Toolchain |
|----------|---------|-----------|
| Python | `Debugpy` | Python 3 + `pip install debugpy` |
| JavaScript | `JavaScript` | Node.js (adapter auto-downloaded by Zed) |
| TypeScript | `JavaScript` | Node.js + TypeScript (`npm install` in `typescript/`) |
| Go | `Delve` | Go toolchain (Delve auto-downloaded by Zed) |
| Rust | `CodeLLDB` | `cargo` / `rustc` (CodeLLDB auto-downloaded) |
| C | `GDB` | a C compiler + `gdb` |

## 3. Build the pre-compiled targets

```bash
# TypeScript → typescript/dist/main.js + source maps
cd typescript && npm install && npm run build

# Rust → rust/target/debug/rust-demo(.exe)
cargo build --manifest-path rust/Cargo.toml

# C → c/main(.exe) with debug symbols
gcc -g -O0 c/main.c -o c/main     # or c/main.exe on Windows
```

Python, JavaScript, and Go need no pre-build — Delve builds Go on launch.

## 4. Open this repo as the Zed worktree

Point Zed at this repository so the debugger resolves source paths correctly and
the agent can launch each language's `program` / `cwd` (see the launch configs in
[`README.md`](README.md)).

## 5. Confirm a clean slate

Using the agent `debugger` tool:

- `list_adapters` — all five adapters present (`Debugpy`, `JavaScript`, `Delve`,
  `CodeLLDB`, `GDB`).
- `list_sessions` — empty.
- `list_breakpoints` — empty.

## Next

See [`DRIVING_THE_SUITE.md`](DRIVING_THE_SUITE.md) to run the suite.
