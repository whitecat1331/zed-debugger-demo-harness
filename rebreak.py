#!/usr/bin/env python3
"""Re-break this harness after the agent has fixed the bugs.

Run this to restore every bug file to its original broken state so the
exercise can be run again. It applies the inverse of each canonical fix.
"""
from pathlib import Path

BUGS_DIR = Path(__file__).resolve().parent / "bugs"

# (filename, [(fixed_snippet, broken_snippet), ...]).
# Each fixed snippet is replaced with the broken (buggy) snippet. An empty
# broken snippet means "delete this line/snippet".
TRANSFORMS = {
    "bug1_off_by_one.py": [("total += 2 * i", "total += 2 * (i + 1)")],
    "bug2_shadowing.py": [("total += value", "total = value")],
    "bug3_condition.py": [("value >= low and value <= high", "value >= low or value <= high")],
    "bug4_mutation.py": [
        ("for value in values[:]:", "for value in values:"),
        ("for value in list(values):", "for value in values:"),
    ],
    "bug5_exception.py": [("if denominator == 0:", "if numerator == 0:")],
    "bug6_step_in.py": [("price * (1 - percent / 100)", "price * (1 + percent / 100)")],
    "bug7_step_out.py": [("count = len(values)", "count = len(values) - 1")],
    "bug8_run_to_line.py": [
        (
            "        result.append(doubled)\n",
            "        result.append(doubled)\n        result[-1] += 1000\n",
        )
    ],
    "bug9_pause.py": [("        i += 1\n", "")],
    "bug10_final_boss.py": [
        ("current_max = current_min = nums[0]", "current_max = nums[0]"),
        (
            "        if num < 0:\n            current_max, current_min = current_min, current_max\n",
            "",
        ),
        ("        current_min = min(num, current_min * num)\n", ""),
        # The previous_max / no-swap variant of the canonical fix.
        (
            "    current_max = nums[0]\n    current_min = nums[0]\n    global_max = nums[0]\n\n"
            "    for num in nums[1:]:\n        previous_max = current_max\n"
            "        current_max = max(num, current_max * num, current_min * num)\n"
            "        current_min = min(num, previous_max * num, current_min * num)\n"
            "        global_max = max(global_max, current_max)\n",
            "    current_max = nums[0]\n    global_max = nums[0]\n\n"
            "    for num in nums[1:]:\n        current_max = max(num, current_max * num)\n"
            "        global_max = max(global_max, current_max)\n",
        ),
    ],
}


def rebreak() -> int:
    changed = 0
    for filename, replacements in TRANSFORMS.items():
        path = BUGS_DIR / filename
        text = path.read_text(encoding="utf-8")
        original = text
        for fixed, broken in replacements:
            if broken and broken in text:
                continue  # already in the broken state
            if fixed in text:
                text = text.replace(fixed, broken, 1)
        if text != original:
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"re-broken {filename}")
            changed += 1
        else:
            print(f"no change: {filename} (already broken, or fix not found)")
    print(f"\n{changed} file(s) re-broken.")
    return 0


if __name__ == "__main__":
    raise SystemExit(rebreak())
