#!/usr/bin/env python3
"""Check the debugger-loop tracking state for drift.

Validates LOOP_STATE.json and ISSUES.json, verifies referenced files and git
commits, and exits non-zero on drift (mirrors the scripts/checks.sh pattern).
Run at the end of every run/fix/verify/restart transition.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ZED_REPO = REPO_ROOT.parent / "zed"
DEFAULT_ZED_BINARY = REPO_ROOT.parent / "zed-dev-build" / "zed.exe"

PHASES = {"run", "fix", "verify", "restart"}
VERIFY_STATES = {"pending", "verify_clippy", "plan", "execute", "clean"}
STATUSES = {"open", "in-progress", "resolved", "deferred", "adapter-upstream"}
CLASSIFICATIONS = {"fork", "adapter-upstream", "harness-doc"}
SEVERITIES = {"P0", "P1", "P2"}
CAUSE_STATES = {"confirmed", "hypothesized", "unknown"}
CONFIDENCES = {"high", "medium"}
SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
PRIOR_FINDING_RE = re.compile(r"prior\s+finding", re.IGNORECASE)

ERRORS: list[str] = []
WARNINGS: list[str] = []


def error(message: str) -> None:
    ERRORS.append(message)


def warning(message: str) -> None:
    WARNINGS.append(message)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        error(f"{path}: file does not exist")
    except json.JSONDecodeError as exc:
        error(f"{path}: invalid JSON ({exc})")
    return None


def verify_commit(sha: str, zed_repo: Path) -> None:
    if not SHA_RE.match(sha):
        error(f"invalid commit SHA: {sha!r}")
        return
    if not zed_repo.exists():
        warning(f"zed repo not found at {zed_repo}; skipping commit verification")
        return
    result = subprocess.run(
        ["git", "-C", str(zed_repo), "rev-parse", "--verify", f"{sha}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        error(f"commit {sha} does not exist in {zed_repo}")
        return
    full = result.stdout.strip()
    reachable = subprocess.run(
        ["git", "-C", str(zed_repo), "merge-base", "--is-ancestor", full, "revive-debugger-tool"],
        capture_output=True,
    )
    if reachable.returncode != 0:
        error(f"commit {sha} is not reachable from revive-debugger-tool")


def commit_shas(entries) -> list[str]:
    shas: list[str] = []
    for entry in entries:
        if ":" not in entry:
            error(f"fixes_applied commit entry is missing 'crate:sha' form: {entry!r}")
            continue
        shas.append(entry.split(":", 1)[1].strip())
    return shas


def validate_loop_state(data) -> None:
    if data is None:
        return
    for key in ("iteration", "phase", "next_action", "last_report", "action_plan",
                "build_commit", "fixes_applied", "verify", "max_iterations", "stall_key"):
        if key not in data:
            error(f"LOOP_STATE.json: missing field {key!r}")

    for field in ("iteration", "max_iterations"):
        if field in data and not isinstance(data[field], int):
            error(f"LOOP_STATE.json: {field} must be an integer")

    if isinstance(data.get("iteration"), int) and isinstance(data.get("max_iterations"), int):
        if data["iteration"] < 0:
            error("LOOP_STATE.json: iteration must be >= 0")
        if data["iteration"] > data["max_iterations"]:
            error(f"LOOP_STATE.json: iteration ({data['iteration']}) exceeds max_iterations ({data['max_iterations']})")

    for field in ("phase", "next_action"):
        if field in data and data[field] not in PHASES:
            error(f"LOOP_STATE.json: {field} must be one of {sorted(PHASES)}")

    if "stall_key" in data and data["stall_key"] is not None and not isinstance(data["stall_key"], str):
        error("LOOP_STATE.json: stall_key must be a string or null")

    if "verify" in data:
        validate_verify(data["verify"])


def validate_verify(data) -> None:
    if not isinstance(data, dict):
        error("LOOP_STATE.json: verify must be an object")
        return
    if data.get("state") not in VERIFY_STATES:
        error(f"LOOP_STATE.json: verify.state must be one of {sorted(VERIFY_STATES)}")
    if "clippy_issues" in data and not isinstance(data["clippy_issues"], list):
        error("LOOP_STATE.json: verify.clippy_issues must be a list")
    last_clippy_run = data.get("last_clippy_run")
    if last_clippy_run is not None and not isinstance(last_clippy_run, str):
        error("LOOP_STATE.json: verify.last_clippy_run must be a string or null")


def validate_fixes_applied(data, zed_repo: Path, issue_ids: set[str]) -> None:
    entries = data.get("fixes_applied")
    if not isinstance(entries, list):
        error("LOOP_STATE.json: fixes_applied must be a list")
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            error(f"LOOP_STATE.json: fixes_applied[{index}] must be an object")
            continue
        if not isinstance(entry.get("name"), str) or not entry["name"]:
            error(f"LOOP_STATE.json: fixes_applied[{index}].name must be a non-empty string")
        if not isinstance(entry.get("commits"), list) or not entry["commits"]:
            error(f"LOOP_STATE.json: fixes_applied[{index}].commits must be a non-empty list")
            continue
        for sha in commit_shas(entry["commits"]):
            verify_commit(sha, zed_repo)
        if entry.get("issue") is not None:
            if entry["issue"] not in issue_ids:
                error(f"LOOP_STATE.json: fixes_applied[{index}].issue {entry['issue']!r} not in ISSUES.json")


def validate_cause(issue_id: str, cause) -> None:
    if not isinstance(cause, dict):
        error(f"{issue_id}: cause must be an object")
        return
    state = cause.get("state")
    if state not in CAUSE_STATES:
        error(f"{issue_id}: cause.state must be one of {sorted(CAUSE_STATES)}")
        return
    if state == "confirmed":
        if not cause.get("root_cause"):
            error(f"{issue_id}: cause.state 'confirmed' requires a non-empty root_cause")
        if not cause.get("verification"):
            error(f"{issue_id}: cause.state 'confirmed' requires a non-empty verification")
    elif state == "hypothesized":
        hypotheses = cause.get("hypotheses")
        if not isinstance(hypotheses, list) or not hypotheses:
            error(f"{issue_id}: cause.state 'hypothesized' requires a non-empty hypotheses list")
            return
        for idx, hypothesis in enumerate(hypotheses):
            if not isinstance(hypothesis, dict):
                error(f"{issue_id}: hypotheses[{idx}] must be an object")
                continue
            if hypothesis.get("confidence") not in CONFIDENCES:
                error(f"{issue_id}: hypotheses[{idx}].confidence must be one of {sorted(CONFIDENCES)} (no 'low' guesses)")
            if not hypothesis.get("cause"):
                error(f"{issue_id}: hypotheses[{idx}].cause must be non-empty")
            if not hypothesis.get("basis"):
                error(f"{issue_id}: hypotheses[{idx}].basis must be non-empty")
    elif state == "unknown":
        if cause.get("root_cause"):
            error(f"{issue_id}: cause.state 'unknown' should not set root_cause")
        if cause.get("hypotheses"):
            error(f"{issue_id}: cause.state 'unknown' should not set hypotheses")


def validate_issues(data, zed_repo: Path) -> set[str]:
    ids: set[str] = set()
    if data is None:
        return ids
    if data.get("version") != 1:
        error("ISSUES.json: version must be 1")
    issues = data.get("issues")
    if not isinstance(issues, list):
        error("ISSUES.json: issues must be a list")
        return ids
    for issue in issues:
        if not isinstance(issue, dict):
            error("ISSUES.json: each issue must be an object")
            continue
        issue_id = issue.get("id")
        if not isinstance(issue_id, str) or not issue_id:
            error("ISSUES.json: each issue needs a non-empty string id")
            continue
        if issue_id in ids:
            error(f"ISSUES.json: duplicate issue id {issue_id!r}")
        ids.add(issue_id)
        for field in ("title", "classification", "severity", "status", "first_seen", "last_seen"):
            if not issue.get(field):
                error(f"{issue_id}: missing or empty field {field!r}")
        if issue.get("classification") not in CLASSIFICATIONS:
            error(f"{issue_id}: classification must be one of {sorted(CLASSIFICATIONS)}")
        if issue.get("severity") not in SEVERITIES:
            error(f"{issue_id}: severity must be one of {sorted(SEVERITIES)}")
        if issue.get("status") not in STATUSES:
            error(f"{issue_id}: status must be one of {sorted(STATUSES)}")
        if not isinstance(issue.get("owning_commits"), list):
            error(f"{issue_id}: owning_commits must be a list")
        else:
            for sha in issue["owning_commits"]:
                verify_commit(sha, zed_repo)
        if issue.get("status") in {"resolved", "adapter-upstream"} and not issue.get("resolution"):
            error(f"{issue_id}: status {issue['status']!r} requires a non-empty resolution")
        validate_cause(issue_id, issue.get("cause"))
    return ids


def check_files_exist(data) -> None:
    for field in ("last_report", "action_plan"):
        value = data.get(field)
        if isinstance(value, str) and value and not (REPO_ROOT / value).exists():
            error(f"LOOP_STATE.json: {field} points to a missing file: {value}")


def check_prior_finding_references(data) -> None:
    report = data.get("last_report")
    if not isinstance(report, str) or not report:
        return
    path = REPO_ROOT / report
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    matches = PRIOR_FINDING_RE.findall(text)
    if matches:
        error(f"{report}: {len(matches)} bare 'prior finding' reference(s) remain; convert them to stable issue IDs")


def check_build_commit_matches_binary(data, zed_repo: Path, binary: Path) -> None:
    build_commit = data.get("build_commit")
    if not isinstance(build_commit, str) or not build_commit:
        return
    if not binary.exists():
        warning(f"zed binary not found at {binary}; skipping build_commit match")
        return
    full = build_commit
    if zed_repo.exists() and len(build_commit) < 40:
        result = subprocess.run(
            ["git", "-C", str(zed_repo), "rev-parse", "--verify", f"{build_commit}^{{commit}}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            full = result.stdout.strip()
    needle = full.encode("ascii")
    try:
        with binary.open("rb") as handle:
            tail = b""
            while True:
                chunk = handle.read(1 << 20)
                if not chunk:
                    break
                window = tail + chunk
                if needle in window:
                    return
                tail = window[-(len(needle) - 1):]
        warning(f"build_commit {build_commit} not found embedded in {binary}")
    except OSError as exc:
        warning(f"could not read binary {binary}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zed-repo", type=Path, default=DEFAULT_ZED_REPO)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--zed-binary", type=Path, default=DEFAULT_ZED_BINARY)
    args = parser.parse_args()

    loop_state = read_json(args.repo_root / "LOOP_STATE.json")
    issues_data = read_json(args.repo_root / "ISSUES.json")

    if loop_state is not None:
        validate_loop_state(loop_state)
        check_files_exist(loop_state)
        if isinstance(loop_state.get("build_commit"), str) and loop_state["build_commit"]:
            verify_commit(loop_state["build_commit"], args.zed_repo)

    issue_ids = validate_issues(issues_data, args.zed_repo) if issues_data is not None else set()

    if loop_state is not None:
        validate_fixes_applied(loop_state, args.zed_repo, issue_ids)
        if loop_state.get("stall_key") and loop_state["stall_key"] not in issue_ids:
            error(f"LOOP_STATE.json: stall_key {loop_state['stall_key']!r} not in ISSUES.json")
        check_prior_finding_references(loop_state)
        check_build_commit_matches_binary(loop_state, args.zed_repo, args.zed_binary)

    for message in WARNINGS:
        print(f"WARN  {message}")
    for message in ERRORS:
        print(f"ERROR {message}")

    if ERRORS:
        print(f"\ncheck-loop-state: {len(ERRORS)} error(s), {len(WARNINGS)} warning(s)")
        return 1
    print(f"check-loop-state: OK ({len(WARNINGS)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
