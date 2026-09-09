#!/usr/bin/env python3
"""Remap post-rebase commit SHAs in ISSUES.json (structured + prose references)."""

from pathlib import Path

PATH = Path("ISSUES.json")

MAPPING = {
    "ff01c5981e": "d1a641c3f3",
    "41b5cb57cf": "d3e89b9f09",
    "43beab78ba": "8bea65f627",
    "f74f3949c3": "b91c245fdb",
    "edaaaea204": "1de9e2236f",
    "20ad403f49": "c15bc5532a",
    "016fcda73e": "c4b28f455d",
}


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    for old, new in MAPPING.items():
        text = text.replace(old, new)
    PATH.write_text(text, encoding="utf-8")
    print("remapped ISSUES.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
