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

PHASES = {"stage", "test", "verify", "restart", "run", "fix", "complete"}
VERIFY_STATES = {"pending", "verify_clippy", "plan", "execute", "clean"}
STATUSES = {"open", "in-progress", "resolved", "deferred", "adapter-upstream"}
CLASSIFICATIONS = {"fork", "adapter-upstream", "harness-doc"}
SEVERITIES = {"P0", "P1", "P2"}
CAUSE_STATES = {"confirmed", "hypothesized", "unknown"}
CONFIDENCES = {"high", "medium"}
FIX_ATTEMPTS_CAP = 3
SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
PRIOR_FINDING_RE = re.compile(r"prior\s+finding", re.IGNORECASE)
ISSUE_ID_RE = re.compile(r"^ISSUE-(\d+)$")


def issue_number(issue_id):
    match = ISSUE_ID_RE.match(issue_id or "")
    return int(match.group(1)) if match else None

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
    for key in ("phase", "next_action", "active_issue", "last_report", "action_plan",
                "build_commit", "changes_introduced", "fixes_applied",
                "verify", "stall_key", "run_count", "pending_validation", "next_plan"):
        if key not in data:
            error(f"LOOP_STATE.json: missing field {key!r}")

    if "active_issue" in data and data["active_issue"] is not None and not isinstance(data["active_issue"], str):
        error("LOOP_STATE.json: active_issue must be a string or null")

    for field in ("phase", "next_action"):
        if field in data and data[field] not in PHASES:
            error(f"LOOP_STATE.json: {field} must be one of {sorted(PHASES)}")

    if "stall_key" in data and data["stall_key"] is not None and not isinstance(data["stall_key"], str):
        error("LOOP_STATE.json: stall_key must be a string or null")

    if "run_count" in data:
        if not isinstance(data["run_count"], int) or data["run_count"] < 0:
            error("LOOP_STATE.json: run_count must be a non-negative integer")
    if "pending_validation" in data and not isinstance(data["pending_validation"], list):
        error("LOOP_STATE.json: pending_validation must be a list")
    if data.get("pending_validation"):
        warning("LOOP_STATE.json: pending_validation non-empty — the next run must be full (not smoke) and clear items only with evidence")
    if "next_plan" in data and data["next_plan"] is not None and not isinstance(data["next_plan"], str):
        error("LOOP_STATE.json: next_plan must be a string or null")

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


def validate_changes_introduced(entries, zed_repo: Path) -> None:
    if entries is None:
        return
    if not isinstance(entries, list):
        error("LOOP_STATE.json: changes_introduced must be a list")
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            error(f"LOOP_STATE.json: changes_introduced[{index}] must be an object")
            continue
        if not isinstance(entry.get("name"), str) or not entry["name"]:
            error(f"LOOP_STATE.json: changes_introduced[{index}].name must be a non-empty string")
        if not isinstance(entry.get("commits"), list) or not entry["commits"]:
            error(f"LOOP_STATE.json: changes_introduced[{index}].commits must be a non-empty list")
            continue
        for sha in commit_shas(entry["commits"]):
            verify_commit(sha, zed_repo)
        for field in ("files", "adapters", "capabilities"):
            if field in entry and entry[field] is not None and not isinstance(entry[field], list):
                error(f"LOOP_STATE.json: changes_introduced[{index}].{field} must be a list")
        for field in ("notes", "plan", "manifest"):
            if field in entry and entry[field] is not None and not isinstance(entry[field], str):
                error(f"LOOP_STATE.json: changes_introduced[{index}].{field} must be a string")


def validate_cause(issue_id: str, cause) -> None:
    if not isinstance(cause, dict):
        error(f"{issue_id}: cause must be an object")
        return
    state = cause.get("state")
    if state not in CAUSE_STATES:
        error(f"{issue_id}: cause.state must be one of {sorted(CAUSE_STATES)}")
        return
    evidence = cause.get("evidence")
    if evidence is not None and (not isinstance(evidence, list) or not all(isinstance(p, str) and p for p in evidence)):
        error(f"{issue_id}: cause.evidence must be a list of non-empty strings")
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

        cause_state = (issue.get("cause") or {}).get("state")
        if issue.get("status") == "adapter-upstream" and cause_state != "confirmed":
            error(
                f"{issue_id}: status 'adapter-upstream' requires cause.state 'confirmed' "
                f"(got {cause_state!r}); otherwise use 'deferred'"
            )

        if "fix_attempts" in issue:
            if not isinstance(issue["fix_attempts"], int):
                error(f"{issue_id}: fix_attempts must be an integer")
            elif issue["fix_attempts"] < 0:
                error(f"{issue_id}: fix_attempts must be >= 0")
            else:
                if issue["fix_attempts"] >= 2 and cause_state == "unknown":
                    error(
                        f"{issue_id}: fix_attempts ({issue['fix_attempts']}) with cause.state "
                        f"'unknown' means you guessed repeatedly without observing; "
                        f"instrument before patching again"
                    )
                if issue["fix_attempts"] >= 2 and not (issue.get("cause") or {}).get("evidence"):
                    error(
                        f"{issue_id}: fix_attempts ({issue['fix_attempts']}) requires "
                        f"cause.evidence (an instrumentation artifact)"
                    )
                if issue["fix_attempts"] >= FIX_ATTEMPTS_CAP and issue.get("status") not in {"resolved", "deferred", "adapter-upstream"}:
                    warning(
                        f"{issue_id}: fix_attempts ({issue['fix_attempts']}) reached the cap "
                        f"({FIX_ATTEMPTS_CAP}) but status is {issue.get('status')!r}; "
                        f"stall/defer it and advance"
                    )

    # Sub-issue parents must reference a real issue id.
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        parent = issue.get("parent")
        if parent is not None:
            if not isinstance(parent, str):
                error(f"{issue.get('id')}: parent must be a string (or null)")
            elif parent not in ids:
                error(f"{issue.get('id')}: parent {parent!r} not found in ISSUES.json")

    # regression_of must reference a real, prior (lower-numbered) issue id.
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        regression_of = issue.get("regression_of")
        if regression_of is not None:
            if not isinstance(regression_of, str):
                error(f"{issue.get('id')}: regression_of must be a string (or null)")
            elif regression_of not in ids:
                error(f"{issue.get('id')}: regression_of {regression_of!r} not found in ISSUES.json")
            else:
                current_number = issue_number(issue.get("id"))
                ref_number = issue_number(regression_of)
                if current_number is not None and ref_number is not None and ref_number >= current_number:
                    error(f"{issue.get('id')}: regression_of {regression_of!r} must be a prior (lower-numbered) issue")

    return ids


def check_files_exist(data) -> None:
    for field in ("last_report", "action_plan"):
        value = data.get(field)
        if isinstance(value, str) and value and not (REPO_ROOT / value).exists():
            error(f"LOOP_STATE.json: {field} points to a missing file: {value}")


def check_evidence_files(issues_data) -> None:
    if issues_data is None:
        return
    for issue in issues_data.get("issues", []):
        if not isinstance(issue, dict):
            continue
        evidence = (issue.get("cause") or {}).get("evidence") or []
        for path in evidence:
            if not (REPO_ROOT / path).exists():
                error(f"{issue.get('id')}: cause.evidence file does not exist: {path}")


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
        validate_changes_introduced(loop_state.get("changes_introduced"), args.zed_repo)
        check_files_exist(loop_state)
        if isinstance(loop_state.get("build_commit"), str) and loop_state["build_commit"]:
            verify_commit(loop_state["build_commit"], args.zed_repo)

    issue_ids = validate_issues(issues_data, args.zed_repo) if issues_data is not None else set()
    if issues_data is not None:
        check_evidence_files(issues_data)

    if loop_state is not None:
        validate_fixes_applied(loop_state, args.zed_repo, issue_ids)
        active_issue = loop_state.get("active_issue")
        if active_issue:
            if active_issue not in issue_ids:
                error(f"LOOP_STATE.json: active_issue {active_issue!r} not in ISSUES.json")
            elif issues_data is not None:
                status = next((issue["status"] for issue in issues_data["issues"] if issue["id"] == active_issue), None)
                if status not in {"open", "in-progress"}:
                    error(f"LOOP_STATE.json: active_issue {active_issue!r} must be open or in-progress, got {status!r}")
        if loop_state.get("stall_key") and loop_state["stall_key"] not in issue_ids:
            error(f"LOOP_STATE.json: stall_key {loop_state['stall_key']!r} not in ISSUES.json")
        if issues_data is not None:
            open_issues = [issue for issue in issues_data["issues"] if issue.get("status") in {"open", "in-progress"}]
            if loop_state.get("next_action") == "complete":
                if loop_state.get("active_issue") is not None:
                    error("LOOP_STATE.json: next_action 'complete' requires active_issue to be null")
                if open_issues:
                    error(f"LOOP_STATE.json: next_action 'complete' but {len(open_issues)} issue(s) still open or in-progress")
            elif loop_state.get("active_issue") is None and not open_issues:
                warning("LOOP_STATE.json: no open issues and no active_issue; record the terminal state (next_action = 'complete')")
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
