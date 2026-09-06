#!/usr/bin/env python3
"""Rewrite a `git rebase -i` todo file, converting `pick` to `drop` for a fixed
set of commit SHA prefixes.

Used to split the debugger-loop auto-submit handoff commits out of the Zed
`revive-debugger-tool` branch. Invoked via GIT_SEQUENCE_EDITOR.

Usage:
    GIT_SEQUENCE_EDITOR="python drop-commits-from-todo.py" git rebase -i main
"""

import sys

DROPS = [
    "63ff2b2e0a",  # agent_ui: Add auto-submit agent thread entry point
    "2ee1493423",  # zed: Add --agent-prompt flag for trusted auto-submit
    "adb88b71be",  # zed: Wait for workspace before submitting agent prompt
    "51d857a7f5",  # zed: Open agent panel before auto-submit
]


def main() -> int:
    path = sys.argv[1]
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()

    out = []
    dropped = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("pick "):
            parts = stripped.split()
            if len(parts) >= 2 and any(parts[1].startswith(p) for p in DROPS):
                out.append("drop " + " ".join(parts[1:]) + "\n")
                dropped += 1
                continue
        out.append(line)

    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(out)

    print(f"dropped {dropped} commit(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
