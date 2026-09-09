#!/usr/bin/env python3
"""Launch a fresh Zed with the freshly built debugger fork and resume the loop.

Fired by the agent as its final action. It launches a NEW Zed instance from
`zed-dev-build/` with `--agent-prompt <resume-loop.md>`, which auto-submits
the resume prompt into a fresh agent thread. No existing Zed instance is
killed or touched.

Usage:
    python restart-zed.py
"""

import os
import subprocess
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD_DIR = os.environ.get("ZED_BUILD_DIR", "")
RESUME_FILE = os.path.join(PROJECT_DIR, "resume-loop.md")
LOG_FILE = os.path.join(PROJECT_DIR, "scripts", "loop", "restart-zed.log")

DEFAULT_PROMPT = (
    "Resume the Zed debugger fix loop: "
    f"read {os.path.join(PROJECT_DIR, 'LOOP_STATE.json')}, "
    "then follow the `debugger-loop` skill for the phase recorded there."
)


def log(message: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def read_resume_prompt() -> str:
    if os.path.exists(RESUME_FILE):
        try:
            with open(RESUME_FILE, encoding="utf-8") as handle:
                text = handle.read().strip()
            if text:
                return text
        except OSError as exc:
            log(f"could not read resume prompt: {exc}")
    log("resume-loop.md missing or empty; using default prompt")
    return DEFAULT_PROMPT


def launch_zed() -> None:
    zed_exe = os.path.join(BUILD_DIR, "zed.exe")
    if not os.path.exists(zed_exe):
        log(f"ERROR: {zed_exe} not found; nothing launched")
        return
    log(f"launching {zed_exe} with --agent-prompt {RESUME_FILE}")
    subprocess.Popen(
        [zed_exe, "--agent-prompt", RESUME_FILE],
        close_fds=True,
    )


def main() -> int:
    read_resume_prompt()  # validate the resume file exists
    launch_zed()
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
