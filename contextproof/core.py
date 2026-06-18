#!/usr/bin/env python3
"""Audit and benchmark repository-level AI agent context files."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "0.3.0"

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    "examples",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
}

CONTEXT_BASENAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "SKILL.md",
    "MCP.md",
    "MCP-SERVER.md",
    ".cursorrules",
    ".windsurfrules",
    ".clinerules",
}

VAGUE_PATTERNS = [
    r"\bfollow best practices\b",
    r"\bclean code\b",
    r"\bbe careful\b",
    r"\bproduction[- ]ready\b",
    r"\bhigh quality\b",
    r"\bmake it robust\b",
    r"\buse your judgment\b",
]

OVERBROAD_PATTERNS = [
    r"\bread (the )?entire (repo|repository|codebase)\b",
    r"\binspect all files\b",
    r"\breview all files\b",
    r"\balways run all tests\b",
    r"\brun the full test suite for every change\b",
    r"\bsearch the whole repository\b",
]

RISKY_PATTERNS = [
    r"\bcurl\b.*\|\s*(sh|bash)\b",
    r"\bwget\b.*\|\s*(sh|bash)\b",
    r"\bsudo\s+rm\s+-rf\b",
    r"\brm\s+-rf\s+/\b",
    r"\bchmod\s+777\b",
    r"\bprint all (env|environment variables)\b",
    r"\bread .*\.env\b",
    r"\bignore previous instructions\b",
    r"\bdo not (mention|disclose|reveal)\b.*\b(instruction|rule|policy)\b",
]

GENERAL_DOC_PATTERNS = [
    r"^#+\s*(roadmap|product overview|meeting notes|release notes|changelog|marketing copy)\b",
    r"\bq[1-4]\s+roadmap\b",
    r"\bgo[- ]to[- ]market\b",
    r"\buser personas?\b",
]

COMMAND_RE = re.compile(r"`([^`\n]*(?:npm|pnpm|yarn|bun|pytest|ruff|mypy|cargo|go test|make|just)[^`\n]*)`")
PATH_MARKER_RE = re.compile(
    r"(?<![\w/.-])"
    r"("
    r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:\.[A-Za-z0-9]+)?"
    r"|"
    r"[A-Za-z0-9_.-]+\.(?:py|js|jsx|ts|tsx|json|toml|yaml|yml|md|mdc|rs|go|java|rb|php|cs|sh|ps1|sql)"
    r")"
)

SEVERITY_PENALTY = {
    "critical": 12.0,
    "high": 8.0,
    "medium": 4.0,
    "low": 2.0,
    "info": 0.0,
}

CONFIDENCE_MULTIPLIER = {
    "high": 1.0,
    "medium": 0.75,
    "low": 0.5,
}

DIMENSION_WEIGHTS = {
    "discoverability": 10.0,
    "actionability": 20.0,
    "minimality": 15.0,
    "consistency": 20.0,
    "safety": 20.0,
    "workflow_fit": 15.0,
}

PROJECT_MODE_ALIASES = {
    "existing_project_audit": "existing_project",
    "new_project_bootstrap": "new_project",
}

PROJECT_MODES = {"existing_project", "new_project", "migration_project"}

VARIANT_ALIASES = {
    "contextproof-minimized": "contextproof-reviewed",
    "contextproof-minified": "contextproof-reviewed",
    "contextproof-optimized": "contextproof-reviewed",
}

PRIMARY_VARIANT_ORDER = ["contextproof-reviewed", "current", "native-init", "none"]

EVIDENCE_STATUS_TO_CONFIDENCE = {
    "not_provided": "static_only",
    "insufficient": "static_with_insufficient_benchmark",
    "mixed": "static_with_mixed_benchmark",
    "directional_positive": "static_with_directional_benchmark",
    "directional_negative": "static_with_directional_benchmark",
    "supported_positive": "static_with_supported_benchmark",
    "supported_negative": "static_with_supported_benchmark",
}


class ContextProofInputError(Exception):
    """Raised when user-provided input cannot be processed."""


@dataclass
class ContextFile:
    path: str
    kind: str
    chars: int
    lines: int
    token_estimate: int
    command_mentions: list[str]


@dataclass
class Command:
    name: str
    command: str
    source: str
    confidence: str


@dataclass
class Issue:
    id: str
    severity: str
    file: str
    message: str
    evidence: str
    recommendation: str


def issue_category(issue_id: str) -> str:
    if issue_id in {"missing-agent-context"}:
        return "discoverability"
    if issue_id in {"large-context-file", "vague-rule", "duplicate-rule", "overconstrained-rules", "misplaced-general-docs"}:
        return "minimality"
    if issue_id in {"large-context-set"}:
        return "minimality"
    if issue_id in {"missing-test-command"}:
        return "actionability"
    if issue_id in {"risky-shell"}:
        return "safety"
    if issue_id in {"conflicting-rule"}:
        return "consistency"
    if issue_id in {"overbroad-context"}:
        return "workflow_fit"
    return "workflow_fit"


def issue_confidence(issue: Issue) -> str:
    if issue.id == "missing-agent-context":
        return "medium"
    if issue.id in {"risky-shell", "conflicting-rule", "large-context-file"}:
        return "high"
    if issue.severity in {"critical", "high"}:
        return "high"
    if issue.severity == "medium":
        return "medium"
    return "medium"


def issue_dimension_shares(issue: Issue) -> dict[str, float]:
    category = issue_category(issue.id)
    if issue.id == "missing-test-command":
        return {"actionability": 0.65, "workflow_fit": 0.35}
    if issue.id == "overbroad-context":
        return {"minimality": 0.35, "workflow_fit": 0.65}
    if issue.id == "risky-shell":
        return {"safety": 1.0}
    if issue.id == "conflicting-rule":
        return {"consistency": 0.75, "workflow_fit": 0.25}
    return {category: 1.0}


def add_global_issues(
    context_files: list[ContextFile],
    commands: list[Command],
    issues: list[Issue],
    project_mode: str,
) -> None:
    total_tokens = sum(item.token_estimate for item in context_files)
    if not context_files:
        severity = "medium" if normalize_project_mode(project_mode) == "new_project" else "high"
        issues.append(
            Issue(
                "missing-agent-context",
                severity,
                "*",
                "No repository-level agent context file was found.",
                "No AGENTS.md, CLAUDE.md, SKILL.md, .cursor/rules, or related context file detected.",
                "Add a concise AGENTS.md or tool-specific context file with validation commands and repository-specific rules.",
            )
        )
    elif total_tokens > 4000:
        issues.append(
            Issue(
                "large-context-set",
                "medium",
                "*",
                f"Total agent context is large ({total_tokens} estimated tokens).",
                f"{total_tokens} estimated tokens across {len(context_files)} context files",
                "Move conditional detail into referenced docs and keep top-level agent context focused.",
            )
        )

    if context_files and not commands:
        issues.append(
            Issue(
                "missing-test-command",
                "high",
                "*",
                "No validation command was discovered in project files or agent context.",
                "No test, lint, typecheck, build, make, or just command found.",
                "Add explicit validation commands such as test, lint, typecheck, or build.",
            )
        )


def finding_from_issue(issue: Issue) -> dict[str, Any]:
    return {
        "id": issue.id,
        "severity": issue.severity,
        "category": issue_category(issue.id),
        "path": issue.file,
        "line": None,
        "evidence": issue.evidence,
        "recommendation": issue.recommendation,
        "confidence": issue_confidence(issue),
        "source": "deterministic",
        "rationale": issue.message,
        "dimension_shares": issue_dimension_shares(issue),
    }


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def normalize_project_mode(value: str | None) -> str:
    normalized = PROJECT_MODE_ALIASES.get(value or "", value or "existing_project")
    if normalized not in PROJECT_MODES:
        return "existing_project"
    return normalized


def normalize_variant(value: Any) -> str:
    raw = str(value or "unknown").strip()
    return VARIANT_ALIASES.get(raw, raw)


def bool_metric(row: dict[str, Any], key: str) -> bool | None:
    if key not in row or row[key] is None:
        return None
    value = row[key]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1", "pass", "passed", "success"}:
            return True
        if lowered in {"false", "no", "0", "fail", "failed", "failure"}:
            return False
    return bool(value)


def numeric_metric(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            return float(len(value))
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def mean_or_none(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def read_text(path: Path, max_bytes: int = 512_000) -> str:
    data = path.read_bytes()
    if len(data) > max_bytes:
        data = data[:max_bytes]
    return data.decode("utf-8", errors="replace")


def is_context_file(path: Path, root: Path) -> bool:
    name = path.name
    parts = set(path.relative_to(root).parts)
    if name in CONTEXT_BASENAMES:
        return True
    if ".cursor" in parts and "rules" in parts and path.suffix in {".md", ".mdc", ".txt"}:
        return True
    if ".github" in parts and name == "copilot-instructions.md":
        return True
    if ".codex" in parts and name == "SKILL.md":
        return True
    return False


def is_context_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    if not normalized:
        return False
    parts = normalized.split("/")
    name = parts[-1]
    if name in CONTEXT_BASENAMES:
        return True
    if ".cursor" in parts and "rules" in parts and Path(name).suffix in {".md", ".mdc", ".txt"}:
        return True
    if normalized == ".github/copilot-instructions.md" or normalized.endswith("/.github/copilot-instructions.md"):
        return True
    return False


def git_output(root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def detect_changed_context_files(root: Path, changed_against: str | None = None) -> dict[str, Any]:
    try:
        git_output(root, ["rev-parse", "--show-toplevel"])
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {
            "status": "not_available",
            "reason": "No readable git repository was found.",
            "base_ref": changed_against,
            "changed_files": [],
            "changed_context_files": [],
        }

    try:
        changed: set[str] = set()
        if changed_against:
            changed.update(
                line.strip()
                for line in git_output(root, ["diff", "--name-only", "--relative", changed_against, "--", "."]).splitlines()
                if line.strip()
            )
            source = "git_diff_ref"
        else:
            for args in (
                ["diff", "--name-only", "--relative", "--", "."],
                ["diff", "--name-only", "--relative", "--cached", "--", "."],
                ["ls-files", "--others", "--exclude-standard", "--", "."],
            ):
                changed.update(line.strip() for line in git_output(root, args).splitlines() if line.strip())
            source = "git_worktree"
    except subprocess.CalledProcessError as exc:
        return {
            "status": "error",
            "reason": (exc.stderr or str(exc)).strip(),
            "base_ref": changed_against,
            "changed_files": [],
            "changed_context_files": [],
        }

    changed_files = sorted(changed)
    changed_context_files = [item for item in changed_files if is_context_path(item)]
    return {
        "status": "available",
        "source": source,
        "base_ref": changed_against,
        "changed_files": changed_files,
        "changed_context_files": changed_context_files,
        "changed_context_file_count": len(changed_context_files),
    }


def classify_context(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if relative == "AGENTS.md":
        return "agents"
    if path.name == "CLAUDE.md":
        return "claude"
    if ".cursor/rules/" in relative:
        return "cursor"
    if path.name == "SKILL.md":
        return "skill"
    if ".github/copilot-instructions.md" in relative:
        return "copilot"
    return "agent-context"


def iter_repo_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".tox")]
        base = Path(dirpath)
        for filename in filenames:
            yield base / filename


def discover_context_files(root: Path) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for path in iter_repo_files(root):
        if is_context_file(path, root):
            files.append((path, classify_context(path, root)))
    return sorted(files, key=lambda item: rel(item[0], root))


def discover_commands(root: Path) -> list[Command]:
    commands: list[Command] = []
    package_json = root / "package.json"
    if package_json.exists():
        try:
            data = json.loads(read_text(package_json))
            scripts = data.get("scripts", {})
            runner = "npm"
            if (root / "pnpm-lock.yaml").exists():
                runner = "pnpm"
            elif (root / "yarn.lock").exists():
                runner = "yarn"
            elif (root / "bun.lockb").exists() or (root / "bun.lock").exists():
                runner = "bun"
            for name in sorted(scripts):
                if re.search(r"test|lint|type|check|build", name, re.I):
                    commands.append(Command(name, f"{runner} run {name}", "package.json", "high"))
        except Exception:
            pass

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = read_text(pyproject)
        if "[tool.pytest" in text or "pytest" in text:
            commands.append(Command("test", "pytest", "pyproject.toml", "medium"))
        if "[tool.ruff" in text or "ruff" in text:
            commands.append(Command("lint", "ruff check .", "pyproject.toml", "medium"))
        if "[tool.mypy" in text or "mypy" in text:
            commands.append(Command("typecheck", "mypy .", "pyproject.toml", "medium"))

    if (root / "Cargo.toml").exists():
        commands.extend(
            [
                Command("test", "cargo test", "Cargo.toml", "high"),
                Command("check", "cargo check", "Cargo.toml", "high"),
            ]
        )

    if (root / "go.mod").exists():
        commands.append(Command("test", "go test ./...", "go.mod", "high"))

    makefile = root / "Makefile"
    if makefile.exists():
        text = read_text(makefile)
        for target in re.findall(r"^([A-Za-z0-9_.-]+):", text, flags=re.M):
            if re.search(r"test|lint|check|build", target, re.I):
                commands.append(Command(target, f"make {target}", "Makefile", "medium"))

    justfile = root / "justfile"
    if justfile.exists():
        text = read_text(justfile)
        for target in re.findall(r"^([A-Za-z0-9_.-]+):", text, flags=re.M):
            if re.search(r"test|lint|check|build", target, re.I):
                commands.append(Command(target, f"just {target}", "justfile", "medium"))

    for path, _kind in discover_context_files(root):
        text = read_text(path)
        relative = rel(path, root)
        for mentioned in COMMAND_RE.findall(text):
            commands.append(Command("context-command", mentioned.strip(), relative, "medium"))

    seen: set[str] = set()
    unique: list[Command] = []
    for command in commands:
        key = command.command
        if key not in seen:
            seen.add(key)
            unique.append(command)
    return unique


def add_pattern_issues(
    issues: list[Issue],
    text: str,
    path: str,
    patterns: list[str],
    issue_id: str,
    severity: str,
    message: str,
    recommendation: str,
) -> None:
    lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lower, re.I)
        if match:
            evidence = text[max(0, match.start() - 60) : match.end() + 60].strip().replace("\n", " ")
            issues.append(Issue(issue_id, severity, path, message, evidence, recommendation))
            return


def normalized_instruction_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        item = re.sub(r"[^a-z0-9 ]+", " ", line.lower()).strip()
        item = re.sub(r"\s+", " ", item)
        if len(item) >= 30 and not item.startswith("#"):
            lines.append(item)
    return lines


def analyze_context(root: Path) -> tuple[list[ContextFile], list[Issue], dict[str, int]]:
    context_files: list[ContextFile] = []
    issues: list[Issue] = []
    duplicate_counter: dict[str, int] = {}

    for path, kind in discover_context_files(root):
        text = read_text(path)
        relative = rel(path, root)
        token_estimate = estimate_tokens(text)
        commands = COMMAND_RE.findall(text)
        context_files.append(
            ContextFile(
                path=relative,
                kind=kind,
                chars=len(text),
                lines=len(text.splitlines()),
                token_estimate=token_estimate,
                command_mentions=commands[:20],
            )
        )

        if token_estimate > 2000:
            issues.append(
                Issue(
                    "large-context-file",
                    "medium",
                    relative,
                    f"Context file is large ({token_estimate} estimated tokens).",
                    f"{token_estimate} tokens",
                    "Move conditional detail into referenced files or remove generic rules.",
                )
            )

        modal_count = len(re.findall(r"\b(always|must|never|forbidden|required|do not)\b", text, re.I))
        if token_estimate and modal_count / token_estimate > 0.025 and modal_count >= 12:
            issues.append(
                Issue(
                    "overconstrained-rules",
                    "medium",
                    relative,
                    "Context contains a high density of absolute rules.",
                    f"{modal_count} absolute terms in {token_estimate} estimated tokens",
                    "Keep only constraints that are specific, current, and testable.",
                )
            )

        add_pattern_issues(
            issues,
            text,
            relative,
            VAGUE_PATTERNS,
            "vague-rule",
            "low",
            "Context contains generic quality guidance.",
            "Replace vague guidance with concrete commands, file paths, or review criteria.",
        )
        add_pattern_issues(
            issues,
            text,
            relative,
            OVERBROAD_PATTERNS,
            "overbroad-context",
            "high",
            "Context encourages broad repository exploration.",
            "Use relevance-based exploration and concrete validation commands instead.",
        )
        add_pattern_issues(
            issues,
            text,
            relative,
            RISKY_PATTERNS,
            "risky-shell",
            "critical",
            "Context contains risky operational or prompt-injection language.",
            "Remove unsafe shell patterns and instructions that hide or override policy.",
        )
        add_pattern_issues(
            issues,
            text,
            relative,
            GENERAL_DOC_PATTERNS,
            "misplaced-general-docs",
            "low",
            "Context appears to include general project documentation rather than agent operating instructions.",
            "Move general narrative, roadmap, or product notes into ordinary docs and keep agent context operational.",
        )

        for line in normalized_instruction_lines(text):
            duplicate_counter[line] = duplicate_counter.get(line, 0) + 1

    duplicates = {line: count for line, count in duplicate_counter.items() if count > 1}
    for line, count in sorted(duplicates.items(), key=lambda item: (-item[1], item[0]))[:10]:
        issues.append(
            Issue(
                "duplicate-rule",
                "low",
                "*",
                "The same instruction appears in multiple places.",
                f"{count}x: {line[:120]}",
                "Keep one source of truth and remove repeated rules.",
            )
        )

    all_text = "\n".join(read_text(path) for path, _ in discover_context_files(root)).lower()
    conflict_pairs = [
        ("always ask", "never ask"),
        ("always run tests", "do not run tests"),
        ("must run tests", "skip tests"),
        ("never edit", "edit freely"),
    ]
    for left, right in conflict_pairs:
        if left in all_text and right in all_text:
            issues.append(
                Issue(
                    "conflicting-rule",
                    "high",
                    "*",
                    "Context contains likely conflicting instructions.",
                    f"Both '{left}' and '{right}' appear.",
                    "Resolve the policy into one context-dependent rule.",
                )
            )

    return context_files, issues, duplicates


def aggregate_score(context_files: list[ContextFile], commands: list[Command], issues: list[Issue]) -> dict[str, Any]:
    remaining = dict(DIMENSION_WEIGHTS)
    issue_counts = {severity: 0 for severity in SEVERITY_PENALTY}

    for issue in issues:
        issue_counts[issue.severity] = issue_counts.get(issue.severity, 0) + 1
        penalty = SEVERITY_PENALTY.get(issue.severity, 2.0) * CONFIDENCE_MULTIPLIER[issue_confidence(issue)]
        for dimension, share in issue_dimension_shares(issue).items():
            remaining[dimension] = max(0.0, remaining[dimension] - penalty * share)

    if any(issue.id == "risky-shell" and issue.severity == "critical" for issue in issues):
        total_cap = 69
    else:
        total_cap = 100
    if any(issue.id == "conflicting-rule" for issue in issues):
        remaining["workflow_fit"] = min(remaining["workflow_fit"], DIMENSION_WEIGHTS["workflow_fit"] * 0.6)

    total = min(total_cap, round(sum(remaining.values())))
    dimensions = {
        name: round(100 * value / DIMENSION_WEIGHTS[name])
        for name, value in remaining.items()
    }
    return {"total": total, "dimensions": dimensions, "issue_counts": issue_counts}


def build_recommendations(context_files: list[ContextFile], commands: list[Command], issues: list[Issue]) -> list[str]:
    recommendations: list[str] = []
    if any(issue.id == "risky-shell" for issue in issues):
        recommendations.append("Remove risky shell and prompt-injection language before using this context in CI.")
    if any(issue.id == "overbroad-context" for issue in issues):
        recommendations.append("Replace broad exploration rules with relevance-based file discovery.")
    if sum(item.token_estimate for item in context_files) > 2000:
        recommendations.append("Minimize top-level context and move conditional detail into referenced files.")
    if not commands:
        recommendations.append("Add concrete test, lint, build, or typecheck commands.")
    if any(issue.id == "duplicate-rule" for issue in issues):
        recommendations.append("Deduplicate repeated rules and keep one source of truth.")
    if not recommendations:
        recommendations.append("Keep context lean and require behavioral benchmark data for major changes.")
    return recommendations


def finding_key(finding: dict[str, Any]) -> str:
    return "|".join(
        [
            str(finding.get("id", "")),
            str(finding.get("path", "")),
            str(finding.get("evidence", ""))[:160],
        ]
    )


def compact_finding(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": finding.get("id"),
        "severity": finding.get("severity"),
        "path": finding.get("path"),
        "recommendation": finding.get("recommendation"),
    }


def build_baseline_delta(report: dict[str, Any], baseline_path: Path | None) -> dict[str, Any] | None:
    if baseline_path is None:
        return None
    if not baseline_path.exists() or not baseline_path.is_file():
        raise ContextProofInputError(f"Baseline report file does not exist: {baseline_path}")
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContextProofInputError(f"Baseline report is not valid JSON: {exc}") from exc

    current_findings = report.get("findings", [])
    baseline_findings = baseline.get("findings", [])
    current_by_key = {finding_key(item): item for item in current_findings}
    baseline_by_key = {finding_key(item): item for item in baseline_findings}
    new_keys = sorted(set(current_by_key) - set(baseline_by_key))
    resolved_keys = sorted(set(baseline_by_key) - set(current_by_key))
    current_score = int(report.get("static_context_score", {}).get("total", 0))
    baseline_score = int(baseline.get("static_context_score", {}).get("total", 0))
    return {
        "status": "compared",
        "baseline_report": str(baseline_path),
        "score_delta": current_score - baseline_score,
        "baseline_score": baseline_score,
        "current_score": current_score,
        "new_finding_count": len(new_keys),
        "resolved_finding_count": len(resolved_keys),
        "unchanged_finding_count": len(set(current_by_key) & set(baseline_by_key)),
        "new_findings": [compact_finding(current_by_key[key]) for key in new_keys[:20]],
        "resolved_findings": [compact_finding(baseline_by_key[key]) for key in resolved_keys[:20]],
    }


def audit_repo(
    root: Path,
    deterministic: bool = False,
    project_mode: str = "existing_project",
    runs_path: Path | None = None,
    changed_against: str | None = None,
    baseline_path: Path | None = None,
) -> dict[str, Any]:
    normalized_project_mode = normalize_project_mode(project_mode)
    context_files, issues, duplicates = analyze_context(root)
    commands = discover_commands(root)
    add_global_issues(context_files, commands, issues, normalized_project_mode)
    scoring = aggregate_score(context_files, commands, issues)
    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    benchmark_summary = summarize_runs(runs_path, deterministic=deterministic) if runs_path else None
    benchmark_evidence = (
        benchmark_summary["benchmark_evidence"]
        if benchmark_summary
        else {
            "status": "not_provided",
            "reason": "No paired benchmark runs were provided.",
        }
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "root": str(root.resolve()),
        "project_mode": normalized_project_mode,
        "confidence_state": EVIDENCE_STATUS_TO_CONFIDENCE.get(benchmark_evidence["status"], "static_only"),
        "static_context_score": {
            "total": scoring["total"],
            "dimensions": scoring["dimensions"],
        },
        "benchmark_evidence": benchmark_evidence,
        "summary": {
            "context_file_count": len(context_files),
            "total_context_tokens": sum(item.token_estimate for item in context_files),
            "command_count": len(commands),
            "issue_count": len(issues),
            "duplicate_rule_count": len(duplicates),
            "benchmark_run_count": benchmark_summary["run_count"] if benchmark_summary else 0,
        },
        "change_detection": detect_changed_context_files(root, changed_against),
        "context_files": [asdict(item) for item in context_files],
        "commands": [asdict(item) for item in commands],
        "findings": [finding_from_issue(item) for item in issues],
        "recommendations": build_recommendations(context_files, commands, issues),
    }
    if benchmark_summary:
        report["benchmark_summary"] = benchmark_summary
    baseline_delta = build_baseline_delta(report, baseline_path)
    if baseline_delta:
        report["baseline_delta"] = baseline_delta
    return report


def render_markdown_report(report: dict[str, Any]) -> str:
    static_score = report["static_context_score"]
    lines = [
        "# ContextProof Report",
        "",
        f"Static context score: {static_score['total']} / 100",
        f"Confidence state: {report['confidence_state']}",
        f"Benchmark evidence: {report['benchmark_evidence']['status']}",
        "",
        "## Summary",
        "",
        f"- Context files: {report['summary']['context_file_count']}",
        f"- Estimated context tokens: {report['summary']['total_context_tokens']}",
        f"- Commands discovered: {report['summary']['command_count']}",
        f"- Issues: {report['summary']['issue_count']}",
        "",
        "## Dimension Scores",
        "",
    ]
    for name, value in static_score["dimensions"].items():
        lines.append(f"- {name}: {value}")
    lines.extend(["", "## Benchmark Evidence", ""])
    evidence = report["benchmark_evidence"]
    lines.append(f"- Status: `{evidence['status']}`")
    lines.append(f"- Reason: {evidence.get('reason', 'No benchmark evidence note provided.')}")
    if "target_variant" in evidence:
        lines.append(f"- Target variant: `{evidence['target_variant']}`")
    if "paired_groups" in evidence:
        lines.append(f"- Paired groups: {evidence['paired_groups']}")
    change_detection = report.get("change_detection", {})
    lines.extend(["", "## Changed Agent Context", ""])
    if change_detection.get("status") == "available":
        changed_context_files = change_detection.get("changed_context_files", [])
        if changed_context_files:
            for item in changed_context_files:
                lines.append(f"- `{item}`")
        else:
            lines.append("- No changed agent-context files detected.")
    else:
        lines.append(f"- Change detection unavailable: {change_detection.get('reason', 'unknown')}")
    if "baseline_delta" in report:
        delta = report["baseline_delta"]
        lines.extend(["", "## Baseline Delta", ""])
        lines.append(f"- Score delta: {delta['score_delta']:+d}")
        lines.append(f"- New findings: {delta['new_finding_count']}")
        lines.append(f"- Resolved findings: {delta['resolved_finding_count']}")
    lines.extend(["", "## Findings", ""])
    if report["findings"]:
        for issue in report["findings"]:
            lines.append(f"- [{issue['severity']}] {issue['id']} in {issue['path']}: {issue['rationale']}")
            if issue["evidence"]:
                lines.append(f"  Evidence: {issue['evidence']}")
            lines.append(f"  Recommendation: {issue['recommendation']}")
    else:
        lines.append("- No static findings.")
    lines.extend(["", "## Commands", ""])
    if report["commands"]:
        for command in report["commands"]:
            lines.append(f"- `{command['command']}` ({command['source']}, {command['confidence']})")
    else:
        lines.append("- No validation commands discovered.")
    lines.extend(["", "## Recommendations", ""])
    for item in report["recommendations"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def render_pr_comment(report: dict[str, Any]) -> str:
    score = report["static_context_score"]["total"]
    findings = report["findings"]
    high_findings = [item for item in findings if item["severity"] in {"critical", "high"}]
    lines = [
        "## ContextProof",
        "",
        f"- Static context score: **{score}/100**",
        f"- Confidence: `{report['confidence_state']}`",
        f"- Benchmark evidence: `{report['benchmark_evidence']['status']}`",
        f"- Findings: {len(findings)} total, {len(high_findings)} critical/high",
        "",
    ]
    change_detection = report.get("change_detection", {})
    if change_detection.get("status") == "available":
        changed_context_files = change_detection.get("changed_context_files", [])
        lines.append("### Changed agent context")
        lines.append("")
        if changed_context_files:
            for item in changed_context_files[:10]:
                lines.append(f"- `{item}`")
            if len(changed_context_files) > 10:
                lines.append(f"- ...and {len(changed_context_files) - 10} more")
        else:
            lines.append("- No changed agent-context files detected.")
        lines.append("")
    if "baseline_delta" in report:
        delta = report["baseline_delta"]
        lines.append("### Baseline delta")
        lines.append("")
        lines.append(f"- Score delta: **{delta['score_delta']:+d}**")
        lines.append(f"- New findings: {delta['new_finding_count']}")
        lines.append(f"- Resolved findings: {delta['resolved_finding_count']}")
        if delta["new_findings"]:
            lines.append("")
            lines.append("New findings:")
            for item in delta["new_findings"][:5]:
                lines.append(f"- **{item['severity']}** `{item['id']}` in `{item['path']}`")
        lines.append("")
    if high_findings:
        lines.append("### Highest priority findings")
        lines.append("")
        for item in high_findings[:5]:
            lines.append(f"- **{item['severity']}** `{item['id']}` in `{item['path']}`: {item['recommendation']}")
    else:
        lines.append("No critical/high static findings.")
    lines.extend(["", "See `.contextproof/report.md` for details.", ""])
    return "\n".join(lines)


def choose_commands(commands: list[dict[str, Any]]) -> dict[str, str]:
    selected: dict[str, str] = {}
    for command in commands:
        name = command["name"].lower()
        value = command["command"]
        if "test" in name and "test" not in selected:
            selected["test"] = value
        elif ("lint" in name or "ruff" in value) and "lint" not in selected:
            selected["lint"] = value
        elif ("type" in name or "mypy" in value or "tsc" in value) and "typecheck" not in selected:
            selected["typecheck"] = value
        elif "build" in name and "build" not in selected:
            selected["build"] = value
        elif "check" in name and "check" not in selected:
            selected["check"] = value
    return selected


def build_minimal_agents_md(report: dict[str, Any]) -> str:
    commands = choose_commands(report["commands"])
    lines = [
        "# AGENTS.md",
        "",
        "## Scope",
        "",
        "These instructions apply to the whole repository.",
        "",
        "## Working Rules",
        "",
        "- Keep changes scoped to the requested task.",
        "- Prefer reading files directly relevant to the change before broad searches.",
        "- Do not edit generated, vendored, build, or dependency directories unless the task explicitly requires it.",
        "- Report any validation command that could not be run.",
        "",
        "## Validation",
        "",
    ]
    if commands:
        for label in ["test", "lint", "typecheck", "build", "check"]:
            if label in commands:
                lines.append(f"- {label}: `{commands[label]}`")
    else:
        lines.append("- No repository validation commands were detected. Add test, lint, or build commands here.")
    lines.extend(
        [
            "",
            "## Context Policy",
            "",
            "- Add new persistent instructions only when they prevent a repeated mistake.",
            "- Keep this file concise; move conditional details to referenced docs when needed.",
            "- Avoid generic quality rules that cannot be verified.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any], json_out: str | None, md_out: str | None) -> None:
    if json_out:
        target = Path(json_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if md_out:
        target = Path(md_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_markdown_report(payload), encoding="utf-8")


def canonical_context_filename(path: Path) -> str:
    if path.name in CONTEXT_BASENAMES:
        return path.name
    if path.suffix in {".md", ".mdc", ".txt"}:
        return "AGENTS.md"
    return "AGENTS.md"


def context_input_text(path: Path) -> str:
    if path.is_file():
        return read_text(path)
    if path.is_dir():
        chunks: list[str] = []
        for context_path, _kind in discover_context_files(path):
            relative = rel(context_path, path)
            chunks.append(f"\n\n<!-- {relative} -->\n\n{read_text(context_path)}")
        return "\n".join(chunks).strip()
    raise ContextProofInputError(f"Context input does not exist: {path}")


def audit_context_input(path: Path, deterministic: bool, project_mode: str) -> dict[str, Any]:
    if path.is_dir():
        return audit_repo(path.resolve(), deterministic=deterministic, project_mode=project_mode)
    if not path.is_file():
        raise ContextProofInputError(f"Context input does not exist or is not a file/directory: {path}")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / canonical_context_filename(path)
        target.write_text(read_text(path), encoding="utf-8")
        return audit_repo(root, deterministic=deterministic, project_mode=project_mode)


def severity_count(report: dict[str, Any], severities: set[str]) -> int:
    return sum(1 for item in report.get("findings", []) if item.get("severity") in severities)


def finding_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {finding_key(item): item for item in report.get("findings", [])}


def extract_validation_commands(text: str) -> set[str]:
    return {item.strip() for item in COMMAND_RE.findall(text) if item.strip()}


def extract_path_markers(text: str) -> set[str]:
    markers: set[str] = set()
    for match in PATH_MARKER_RE.findall(text):
        value = match.strip("`'\".,:;()[]{}")
        if not value or value.startswith(("http://", "https://")):
            continue
        if len(value) > 160:
            continue
        markers.add(value.replace("\\", "/"))
    return markers


def compact_report_summary(report: dict[str, Any]) -> dict[str, Any]:
    score = report.get("static_context_score", {})
    summary = report.get("summary", {})
    findings = report.get("findings", [])
    return {
        "score": score.get("total"),
        "dimensions": score.get("dimensions", {}),
        "total_context_tokens": summary.get("total_context_tokens", 0),
        "context_file_count": summary.get("context_file_count", 0),
        "issue_count": len(findings),
        "critical_high_finding_count": severity_count(report, {"critical", "high"}),
        "findings": [compact_finding(item) for item in findings[:30]],
    }


def compare_contexts(
    source_path: Path,
    candidate_path: Path,
    deterministic: bool = False,
    project_mode: str = "existing_project",
) -> dict[str, Any]:
    source_path = source_path.resolve()
    candidate_path = candidate_path.resolve()
    source_text = context_input_text(source_path)
    candidate_text = context_input_text(candidate_path)
    source_report = audit_context_input(source_path, deterministic=deterministic, project_mode=project_mode)
    candidate_report = audit_context_input(candidate_path, deterministic=deterministic, project_mode=project_mode)

    source_findings = finding_map(source_report)
    candidate_findings = finding_map(candidate_report)
    resolved_keys = sorted(set(source_findings) - set(candidate_findings))
    introduced_keys = sorted(set(candidate_findings) - set(source_findings))

    source_commands = extract_validation_commands(source_text)
    candidate_commands = extract_validation_commands(candidate_text)
    source_paths = extract_path_markers(source_text)
    candidate_paths = extract_path_markers(candidate_text)
    removed_commands = sorted(source_commands - candidate_commands)
    removed_paths = sorted(source_paths - candidate_paths)

    source_score = int(source_report["static_context_score"]["total"])
    candidate_score = int(candidate_report["static_context_score"]["total"])
    source_tokens = int(source_report["summary"]["total_context_tokens"])
    candidate_tokens = int(candidate_report["summary"]["total_context_tokens"])
    source_critical_high = severity_count(source_report, {"critical", "high"})
    candidate_critical_high = severity_count(candidate_report, {"critical", "high"})
    introduced_high = [
        candidate_findings[key]
        for key in introduced_keys
        if candidate_findings[key].get("severity") in {"critical", "high"}
    ]

    regression_flags: list[str] = []
    if introduced_high:
        regression_flags.append("introduced-critical-or-high-finding")
    if source_commands and not candidate_commands:
        regression_flags.append("dropped-all-validation-commands")
    elif removed_commands:
        regression_flags.append("removed-some-validation-commands")
    if source_paths and len(removed_paths) == len(source_paths):
        regression_flags.append("dropped-all-path-markers")
    elif source_paths and len(removed_paths) / max(1, len(source_paths)) > 0.5:
        regression_flags.append("dropped-most-path-markers")
    source_safety = int(source_report["static_context_score"]["dimensions"].get("safety", 0))
    candidate_safety = int(candidate_report["static_context_score"]["dimensions"].get("safety", 0))
    if candidate_safety < source_safety:
        regression_flags.append("safety-score-decreased")

    score_delta = candidate_score - source_score
    token_delta = candidate_tokens - source_tokens
    critical_high_delta = candidate_critical_high - source_critical_high
    if regression_flags:
        verdict = "regression"
    elif score_delta > 0 and critical_high_delta <= 0:
        verdict = "improved"
    elif score_delta == 0 and token_delta == 0 and critical_high_delta == 0:
        verdict = "unchanged"
    else:
        verdict = "mixed"

    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "comparison_type": "context_candidate",
        "project_mode": normalize_project_mode(project_mode),
        "source_path": str(source_path),
        "candidate_path": str(candidate_path),
        "verdict": verdict,
        "regression_flags": regression_flags,
        "deltas": {
            "score_delta": score_delta,
            "token_delta": token_delta,
            "critical_high_finding_delta": critical_high_delta,
            "resolved_finding_count": len(resolved_keys),
            "introduced_finding_count": len(introduced_keys),
        },
        "source": compact_report_summary(source_report),
        "candidate": compact_report_summary(candidate_report),
        "preservation": {
            "source_validation_commands": sorted(source_commands),
            "candidate_validation_commands": sorted(candidate_commands),
            "removed_validation_commands": removed_commands,
            "source_path_marker_count": len(source_paths),
            "candidate_path_marker_count": len(candidate_paths),
            "removed_path_markers": removed_paths[:30],
        },
        "resolved_findings": [compact_finding(source_findings[key]) for key in resolved_keys[:30]],
        "introduced_findings": [compact_finding(candidate_findings[key]) for key in introduced_keys[:30]],
        "recommendation": candidate_recommendation(verdict, regression_flags),
    }


def candidate_recommendation(verdict: str, regression_flags: list[str]) -> str:
    if verdict == "improved":
        return "Candidate improved static context hygiene without detected preservation regressions. Review manually before replacing source context."
    if regression_flags:
        return "Do not adopt this candidate until regression flags are resolved: " + ", ".join(regression_flags) + "."
    if verdict == "unchanged":
        return "Candidate did not materially change the measured context quality."
    return "Candidate has mixed results. Review resolved and introduced findings before deciding whether to adopt it."


def render_candidate_report(report: dict[str, Any]) -> str:
    deltas = report["deltas"]
    lines = [
        "# ContextProof Candidate Report",
        "",
        f"Verdict: `{report['verdict']}`",
        f"Source: `{report['source_path']}`",
        f"Candidate: `{report['candidate_path']}`",
        "",
        "## Score Delta",
        "",
        f"- Source score: {report['source']['score']} / 100",
        f"- Candidate score: {report['candidate']['score']} / 100",
        f"- Score delta: {deltas['score_delta']:+d}",
        f"- Estimated token delta: {deltas['token_delta']:+d}",
        f"- Critical/high finding delta: {deltas['critical_high_finding_delta']:+d}",
        f"- Resolved findings: {deltas['resolved_finding_count']}",
        f"- Introduced findings: {deltas['introduced_finding_count']}",
        "",
        "## Preservation",
        "",
    ]
    preservation = report["preservation"]
    if preservation["removed_validation_commands"]:
        lines.append("Removed validation commands:")
        for item in preservation["removed_validation_commands"]:
            lines.append(f"- `{item}`")
    else:
        lines.append("- No explicit validation commands were removed.")
    if preservation["removed_path_markers"]:
        lines.append("")
        lines.append("Removed path markers requiring review:")
        for item in preservation["removed_path_markers"][:15]:
            lines.append(f"- `{item}`")
    if report["regression_flags"]:
        lines.extend(["", "## Regression Flags", ""])
        for item in report["regression_flags"]:
            lines.append(f"- `{item}`")
    lines.extend(["", "## Resolved Findings", ""])
    if report["resolved_findings"]:
        for item in report["resolved_findings"][:15]:
            lines.append(f"- **{item['severity']}** `{item['id']}` in `{item['path']}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Introduced Findings", ""])
    if report["introduced_findings"]:
        for item in report["introduced_findings"][:15]:
            lines.append(f"- **{item['severity']}** `{item['id']}` in `{item['path']}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Recommendation", "", report["recommendation"], ""])
    return "\n".join(lines)


def iter_scenario_dirs(root: Path) -> list[Path]:
    if not root.exists() or not root.is_dir():
        raise ContextProofInputError(f"Scenario directory does not exist: {root}")
    scenarios = [path for path in root.iterdir() if (path / "expected.json").is_file() and (path / "source").exists()]
    return sorted(scenarios, key=lambda item: item.name)


def load_scenario_expected(scenario_dir: Path) -> dict[str, Any]:
    try:
        payload = json.loads((scenario_dir / "expected.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContextProofInputError(f"Scenario expected.json is not valid JSON: {scenario_dir}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContextProofInputError(f"Scenario expected.json must be an object: {scenario_dir}")
    return payload


def discover_candidate_inputs(scenario_dir: Path) -> list[Path]:
    candidates_dir = scenario_dir / "candidates"
    if not candidates_dir.exists():
        return []
    found: list[Path] = []
    for path in sorted(candidates_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".mdc", ".txt"}:
            found.append(path)
    if not found:
        for path in sorted(candidates_dir.iterdir()):
            if path.is_dir() and discover_context_files(path):
                found.append(path)
    return found


def infer_prompt_variant(candidate_path: Path, scenario_dir: Path, default_variant: str) -> str:
    candidates_dir = scenario_dir / "candidates"
    try:
        relative = candidate_path.relative_to(candidates_dir)
    except ValueError:
        return default_variant
    if len(relative.parts) > 1:
        return relative.parts[0]
    return default_variant


def build_optimizer_benchmark_rows(
    scenarios_root: Path,
    prompt_variant: str = "baseline",
    deterministic: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    for scenario_dir in iter_scenario_dirs(scenarios_root):
        expected = load_scenario_expected(scenario_dir)
        source = scenario_dir / "source"
        scenario_id = str(expected.get("scenario_id") or scenario_dir.name)
        project_mode = normalize_project_mode(str(expected.get("project_mode") or "existing_project"))
        preserve = [str(item) for item in expected.get("preserve", []) if str(item).strip()]
        for candidate in discover_candidate_inputs(scenario_dir):
            comparison = compare_contexts(source, candidate, deterministic=deterministic, project_mode=project_mode)
            candidate_text = context_input_text(candidate)
            missing_preservation = [item for item in preserve if item not in candidate_text]
            variant = infer_prompt_variant(candidate, scenario_dir, prompt_variant)
            regression_flags = list(comparison["regression_flags"])
            if missing_preservation:
                regression_flags.append("missing-expected-preservation")
            score_delta = int(comparison["deltas"]["score_delta"])
            token_delta = int(comparison["deltas"]["token_delta"])
            critical_high_delta = int(comparison["deltas"]["critical_high_finding_delta"])
            success = (
                comparison["verdict"] == "improved"
                and score_delta >= 0
                and token_delta <= 0
                and critical_high_delta <= 0
                and not regression_flags
            )
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "generated_at": generated_at,
                    "run_id": f"{scenario_id}:{variant}:{candidate.name}",
                    "scenario_id": scenario_id,
                    "prompt_variant": variant,
                    "project_mode": project_mode,
                    "source_path": str(source.resolve()),
                    "candidate_path": str(candidate.resolve()),
                    "verdict": comparison["verdict"],
                    "success": success,
                    "score_delta": score_delta,
                    "token_delta": token_delta,
                    "critical_high_finding_delta": critical_high_delta,
                    "resolved_finding_count": comparison["deltas"]["resolved_finding_count"],
                    "introduced_finding_count": comparison["deltas"]["introduced_finding_count"],
                    "source_score": comparison["source"]["score"],
                    "candidate_score": comparison["candidate"]["score"],
                    "source_tokens": comparison["source"]["total_context_tokens"],
                    "candidate_tokens": comparison["candidate"]["total_context_tokens"],
                    "regression_flags": regression_flags,
                    "removed_validation_commands": comparison["preservation"]["removed_validation_commands"],
                    "missing_expected_preservation": missing_preservation,
                }
            )
    return rows


def summarize_optimizer_benchmark(rows: list[dict[str, Any]], prompt_variant: str) -> dict[str, Any]:
    variants: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        variants.setdefault(str(row["prompt_variant"]), []).append(row)
    variant_summaries: dict[str, dict[str, Any]] = {}
    for variant, items in sorted(variants.items()):
        score_deltas = [float(item["score_delta"]) for item in items]
        token_deltas = [float(item["token_delta"]) for item in items]
        critical_deltas = [float(item["critical_high_finding_delta"]) for item in items]
        successes = [1.0 if item.get("success") else 0.0 for item in items]
        variant_summaries[variant] = {
            "runs": len(items),
            "success_rate": mean_or_none(successes) or 0.0,
            "avg_score_delta": mean_or_none(score_deltas),
            "avg_token_delta": mean_or_none(token_deltas),
            "avg_critical_high_finding_delta": mean_or_none(critical_deltas),
            "regression_count": sum(1 for item in items if item.get("regression_flags")),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_type": "context_optimizer",
        "default_prompt_variant": prompt_variant,
        "run_count": len(rows),
        "scenario_count": len({str(row["scenario_id"]) for row in rows}),
        "variants": variant_summaries,
    }


def render_optimizer_benchmark_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# ContextProof Optimizer Benchmark",
        "",
        f"Runs: {summary['run_count']}",
        f"Scenarios: {summary['scenario_count']}",
        "",
        "## Variants",
        "",
    ]
    for variant, item in summary["variants"].items():
        lines.append(f"### {variant}")
        lines.append("")
        lines.append(f"- Runs: {item['runs']}")
        lines.append(f"- Success rate: {item['success_rate']:.2%}")
        if item["avg_score_delta"] is not None:
            lines.append(f"- Avg score delta: {item['avg_score_delta']:+.1f}")
        if item["avg_token_delta"] is not None:
            lines.append(f"- Avg token delta: {item['avg_token_delta']:+.1f}")
        if item["avg_critical_high_finding_delta"] is not None:
            lines.append(f"- Avg critical/high finding delta: {item['avg_critical_high_finding_delta']:+.1f}")
        lines.append(f"- Regression count: {item['regression_count']}")
        lines.append("")
    lines.extend(["## Runs", ""])
    if not rows:
        lines.append("- No candidate runs found.")
    for row in rows:
        lines.append(f"### {row['scenario_id']} / {row['prompt_variant']}")
        lines.append("")
        lines.append(f"- Verdict: `{row['verdict']}`")
        lines.append(f"- Success: `{row['success']}`")
        lines.append(f"- Score delta: {row['score_delta']:+d}")
        lines.append(f"- Token delta: {row['token_delta']:+d}")
        lines.append(f"- Critical/high finding delta: {row['critical_high_finding_delta']:+d}")
        if row["regression_flags"]:
            lines.append(f"- Regression flags: {', '.join(f'`{item}`' for item in row['regression_flags'])}")
        lines.append("")
    return "\n".join(lines)


def normalize_run(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    normalized["variant"] = normalize_variant(row.get("variant"))
    normalized["project_mode"] = normalize_project_mode(str(row.get("project_mode") or "existing_project"))
    normalized["paired_group_id"] = str(
        row.get("paired_group_id") or row.get("task_id") or row.get("run_id") or "unpaired"
    )
    normalized["success"] = bool_metric(row, "success")
    normalized["tests_passed"] = bool_metric(row, "tests_passed")
    normalized["human_intervention"] = bool_metric(row, "human_intervention")
    normalized["tokens_input"] = numeric_metric(row, "tokens_input", "input_tokens")
    normalized["tokens_output"] = numeric_metric(row, "tokens_output", "output_tokens")
    normalized["duration_seconds"] = numeric_metric(row, "duration_seconds")
    normalized["files_read"] = numeric_metric(row, "files_read")
    normalized["files_changed"] = numeric_metric(row, "files_changed", "files_touched")
    normalized["turns"] = numeric_metric(row, "turns", "turn_count")
    normalized["commands_run_count"] = numeric_metric(row, "commands_run_count", "commands_run")
    violations = row.get("instruction_violations")
    normalized["instruction_violation_count"] = len(violations) if isinstance(violations, list) else numeric_metric(row, "instruction_violations")
    return normalized


def load_runs(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise ContextProofInputError(f"Benchmark runs file does not exist: {path}")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ContextProofInputError(f"Invalid JSON on line {number}: {exc}") from exc
        if not isinstance(raw, dict):
            raise ContextProofInputError(f"Benchmark run on line {number} must be a JSON object.")
        rows.append(normalize_run(raw))
    return rows


def variant_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [float(value) for row in items if (value := row.get("success")) is not None]
    tests = [float(value) for row in items if (value := row.get("tests_passed")) is not None]
    interventions = [float(value) for row in items if (value := row.get("human_intervention")) is not None]
    tokens_input = [float(value) for row in items if (value := row.get("tokens_input")) is not None]
    tokens_output = [float(value) for row in items if (value := row.get("tokens_output")) is not None]
    durations = [float(value) for row in items if (value := row.get("duration_seconds")) is not None]
    files_read = [float(value) for row in items if (value := row.get("files_read")) is not None]
    files_changed = [float(value) for row in items if (value := row.get("files_changed")) is not None]
    turns = [float(value) for row in items if (value := row.get("turns")) is not None]
    commands = [float(value) for row in items if (value := row.get("commands_run_count")) is not None]
    violations = [float(value) for row in items if (value := row.get("instruction_violation_count")) is not None]
    project_modes = sorted({str(row.get("project_mode", "existing_project")) for row in items})
    return {
        "runs": len(items),
        "project_modes": project_modes,
        "success_rate": mean_or_none(successes) or 0.0,
        "tests_pass_rate": mean_or_none(tests),
        "human_intervention_rate": mean_or_none(interventions),
        "avg_tokens_input": mean_or_none(tokens_input),
        "avg_tokens_output": mean_or_none(tokens_output),
        "avg_duration_seconds": mean_or_none(durations),
        "avg_files_read": mean_or_none(files_read),
        "avg_files_changed": mean_or_none(files_changed),
        "avg_turns": mean_or_none(turns),
        "avg_commands_run": mean_or_none(commands),
        "avg_instruction_violations": mean_or_none(violations),
    }


def choose_primary_variant(variants: dict[str, dict[str, Any]]) -> str | None:
    for variant in PRIMARY_VARIANT_ORDER:
        if variant in variants:
            return variant
    if not variants:
        return None
    return max(
        variants,
        key=lambda item: (
            variants[item].get("success_rate") or 0.0,
            variants[item].get("tests_pass_rate") or 0.0,
            -(variants[item].get("human_intervention_rate") or 0.0),
        ),
    )


def aggregate_group_variant(items: list[dict[str, Any]]) -> dict[str, float | None]:
    metrics = variant_metrics(items)
    return {
        "success_rate": metrics["success_rate"],
        "tests_pass_rate": metrics["tests_pass_rate"],
        "human_intervention_rate": metrics["human_intervention_rate"],
        "avg_tokens_input": metrics["avg_tokens_input"],
        "avg_duration_seconds": metrics["avg_duration_seconds"],
        "avg_turns": metrics["avg_turns"],
        "avg_files_changed": metrics["avg_files_changed"],
    }


def comparison_score_delta(target: dict[str, float | None], baseline: dict[str, float | None]) -> float:
    success_delta = (target.get("success_rate") or 0.0) - (baseline.get("success_rate") or 0.0)
    tests_delta = (target.get("tests_pass_rate") or 0.0) - (baseline.get("tests_pass_rate") or 0.0)
    intervention_delta = (target.get("human_intervention_rate") or 0.0) - (baseline.get("human_intervention_rate") or 0.0)
    return success_delta + 0.5 * tests_delta - 0.25 * intervention_delta


def build_comparison(rows: list[dict[str, Any]], target_variant: str, baseline_variant: str) -> dict[str, Any]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        grouped.setdefault(str(row["paired_group_id"]), {}).setdefault(str(row["variant"]), []).append(row)

    success_deltas: list[float] = []
    tests_deltas: list[float] = []
    intervention_deltas: list[float] = []
    tokens_input_deltas: list[float] = []
    duration_deltas: list[float] = []
    turns_deltas: list[float] = []
    files_changed_deltas: list[float] = []
    score_deltas: list[float] = []

    for variants in grouped.values():
        if target_variant not in variants or baseline_variant not in variants:
            continue
        target = aggregate_group_variant(variants[target_variant])
        baseline = aggregate_group_variant(variants[baseline_variant])
        success_deltas.append((target.get("success_rate") or 0.0) - (baseline.get("success_rate") or 0.0))
        tests_deltas.append((target.get("tests_pass_rate") or 0.0) - (baseline.get("tests_pass_rate") or 0.0))
        intervention_deltas.append(
            (target.get("human_intervention_rate") or 0.0) - (baseline.get("human_intervention_rate") or 0.0)
        )
        for key, sink in [
            ("avg_tokens_input", tokens_input_deltas),
            ("avg_duration_seconds", duration_deltas),
            ("avg_turns", turns_deltas),
            ("avg_files_changed", files_changed_deltas),
        ]:
            if target.get(key) is not None and baseline.get(key) is not None:
                sink.append(float(target[key]) - float(baseline[key]))
        score_delta = comparison_score_delta(target, baseline)
        score_deltas.append(score_delta)

    return {
        "target_variant": target_variant,
        "baseline_variant": baseline_variant,
        "paired_groups": len(score_deltas),
        "score_delta": mean_or_none(score_deltas),
        "success_rate_delta": mean_or_none(success_deltas),
        "tests_pass_rate_delta": mean_or_none(tests_deltas),
        "human_intervention_rate_delta": mean_or_none(intervention_deltas),
        "avg_tokens_input_delta": mean_or_none(tokens_input_deltas),
        "avg_duration_seconds_delta": mean_or_none(duration_deltas),
        "avg_turns_delta": mean_or_none(turns_deltas),
        "avg_files_changed_delta": mean_or_none(files_changed_deltas),
        "wins": sum(1 for value in score_deltas if value > 0.05),
        "losses": sum(1 for value in score_deltas if value < -0.05),
        "ties": sum(1 for value in score_deltas if -0.05 <= value <= 0.05),
    }


def infer_benchmark_evidence(run_count: int, target_variant: str | None, comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    if not run_count:
        return {"status": "not_provided", "reason": "No benchmark runs were provided."}
    if not target_variant:
        return {"status": "insufficient", "reason": "No benchmark variant could be selected for comparison."}

    comparable = [item for item in comparisons if item["paired_groups"] > 0 and item["score_delta"] is not None]
    max_pairs = max((item["paired_groups"] for item in comparable), default=0)
    if max_pairs < 3:
        return {
            "status": "insufficient",
            "reason": "Fewer than 3 paired task groups are available for the selected comparison.",
            "target_variant": target_variant,
            "paired_groups": max_pairs,
        }

    strong_negative = any(
        (item.get("success_rate_delta") or 0.0) <= -0.15 or (item.get("score_delta") or 0.0) <= -0.25
        for item in comparable
    )
    positive = all((item.get("score_delta") or 0.0) >= 0 for item in comparable) and any(
        (item.get("success_rate_delta") or 0.0) >= 0.15
        or ((item.get("success_rate_delta") or 0.0) >= 0 and (item.get("avg_tokens_input_delta") or 0.0) < 0)
        for item in comparable
    )
    negative = strong_negative and not positive

    if positive:
        status = "supported_positive" if max_pairs >= 6 else "directional_positive"
        return {
            "status": status,
            "reason": f"{target_variant} has positive paired outcomes across available baselines.",
            "target_variant": target_variant,
            "paired_groups": max_pairs,
        }
    if negative:
        status = "supported_negative" if max_pairs >= 6 else "directional_negative"
        return {
            "status": status,
            "reason": f"{target_variant} underperformed at least one paired baseline.",
            "target_variant": target_variant,
            "paired_groups": max_pairs,
        }
    return {
        "status": "mixed",
        "reason": "Paired benchmark results do not support a clear positive or negative direction.",
        "target_variant": target_variant,
        "paired_groups": max_pairs,
    }


def summarize_runs(path: Path, deterministic: bool = False) -> dict[str, Any]:
    rows = load_runs(path)
    variants_raw: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        variants_raw.setdefault(str(row.get("variant", "unknown")), []).append(row)
    variants = {variant: variant_metrics(items) for variant, items in sorted(variants_raw.items())}
    target_variant = choose_primary_variant(variants)
    baseline_variants = [variant for variant in ["none", "current", "native-init"] if variant in variants and variant != target_variant]
    comparisons = [build_comparison(rows, str(target_variant), baseline) for baseline in baseline_variants] if target_variant else []
    evidence = infer_benchmark_evidence(len(rows), target_variant, comparisons)
    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "benchmark_evidence": evidence,
        "run_count": len(rows),
        "paired_group_count": len({str(row["paired_group_id"]) for row in rows}),
        "target_variant": target_variant,
        "baseline_variants": baseline_variants,
        "variants": variants,
        "comparisons": comparisons,
    }


def render_runs_markdown(summary: dict[str, Any]) -> str:
    evidence = summary["benchmark_evidence"]
    lines = [
        "# ContextProof Benchmark Summary",
        "",
        f"Runs: {summary['run_count']}",
        f"Paired groups: {summary['paired_group_count']}",
        f"Target variant: `{summary.get('target_variant') or 'n/a'}`",
        f"Evidence status: `{evidence['status']}`",
        f"Evidence note: {evidence['reason']}",
        "",
        "## Comparisons",
        "",
    ]
    if summary["comparisons"]:
        for item in summary["comparisons"]:
            lines.append(f"### {item['target_variant']} vs {item['baseline_variant']}")
            lines.append("")
            lines.append(f"- Paired groups: {item['paired_groups']}")
            if item["success_rate_delta"] is not None:
                lines.append(f"- Success rate delta: {item['success_rate_delta']:+.2%}")
            if item["tests_pass_rate_delta"] is not None:
                lines.append(f"- Tests pass rate delta: {item['tests_pass_rate_delta']:+.2%}")
            if item["human_intervention_rate_delta"] is not None:
                lines.append(f"- Human intervention delta: {item['human_intervention_rate_delta']:+.2%}")
            if item["avg_tokens_input_delta"] is not None:
                lines.append(f"- Avg input token delta: {item['avg_tokens_input_delta']:+.0f}")
            if item["avg_duration_seconds_delta"] is not None:
                lines.append(f"- Avg duration delta seconds: {item['avg_duration_seconds_delta']:+.0f}")
            lines.append(f"- Wins/losses/ties: {item['wins']}/{item['losses']}/{item['ties']}")
            lines.append("")
    else:
        lines.append("- No paired comparisons available.")
        lines.append("")

    lines.extend(["## Variants", ""])
    for variant, item in summary["variants"].items():
        lines.append(f"### {variant}")
        lines.append("")
        lines.append(f"- Runs: {item['runs']}")
        lines.append(f"- Success rate: {item['success_rate']:.2%}")
        if item["tests_pass_rate"] is not None:
            lines.append(f"- Tests pass rate: {item['tests_pass_rate']:.2%}")
        if item["human_intervention_rate"] is not None:
            lines.append(f"- Human intervention rate: {item['human_intervention_rate']:.2%}")
        if item["avg_turns"] is not None:
            lines.append(f"- Avg turns: {item['avg_turns']:.1f}")
        if item["avg_tokens_input"] is not None:
            lines.append(f"- Avg input tokens: {item['avg_tokens_input']:.0f}")
        if item["avg_tokens_output"] is not None:
            lines.append(f"- Avg output tokens: {item['avg_tokens_output']:.0f}")
        if item["avg_duration_seconds"] is not None:
            lines.append(f"- Avg duration seconds: {item['avg_duration_seconds']:.0f}")
        if item["avg_files_read"] is not None:
            lines.append(f"- Avg files read: {item['avg_files_read']:.1f}")
        if item["avg_files_changed"] is not None:
            lines.append(f"- Avg files changed: {item['avg_files_changed']:.1f}")
        lines.append("")
    return "\n".join(lines)


def command_audit(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    if not root.exists() or not root.is_dir():
        raise ContextProofInputError(f"Repository path does not exist or is not a directory: {root}")
    runs_path = Path(args.runs).resolve() if args.runs else None
    baseline_path = Path(args.baseline).resolve() if args.baseline else None
    report = audit_repo(
        root,
        deterministic=args.deterministic,
        project_mode=args.project_mode,
        runs_path=runs_path,
        changed_against=args.changed_against,
        baseline_path=baseline_path,
    )

    output_dir = Path(args.output_dir) if args.output_dir else root / ".contextproof"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = args.json_out or str(output_dir / "report.json")
    md_out = args.md_out or str(output_dir / "report.md")

    write_outputs(report, json_out, md_out)
    if args.pr_comment:
        target = output_dir / "pr-comment.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_pr_comment(report), encoding="utf-8")
    if "benchmark_summary" in report:
        (output_dir / "benchmark-summary.json").write_text(
            json.dumps(report["benchmark_summary"], indent=2) + "\n",
            encoding="utf-8",
        )
        (output_dir / "benchmark-summary.md").write_text(
            render_runs_markdown(report["benchmark_summary"]),
            encoding="utf-8",
        )
    if args.minimize:
        (output_dir / "context.min.md").write_text(build_minimal_agents_md(report), encoding="utf-8")
        (output_dir / "minimize-rationale.md").write_text(
            "# ContextProof Starter Scaffold Rationale\n\n"
            "Generated as a generic starter scaffold from deterministic repository scan "
            "and command discovery. It is not a project-specific rewrite. Review before "
            "using it anywhere.\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2))
    if args.fail_under is not None and report["static_context_score"]["total"] < args.fail_under:
        return 1
    return 0


def command_minimize(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    if not root.exists() or not root.is_dir():
        raise ContextProofInputError(f"Repository path does not exist or is not a directory: {root}")
    report = audit_repo(root, deterministic=args.deterministic, project_mode=args.project_mode)
    candidate = build_minimal_agents_md(report)
    if args.output:
        Path(args.output).write_text(candidate, encoding="utf-8")
    else:
        print(candidate)
    return 0


def command_quickstart(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    if not root.exists() or not root.is_dir():
        raise ContextProofInputError(f"Repository path does not exist or is not a directory: {root}")
    report = audit_repo(root, deterministic=args.deterministic, project_mode=args.project_mode)
    findings = report["findings"][:3]
    print(f"ContextProof static score: {report['static_context_score']['total']}/100")
    if findings:
        print("Top findings:")
        for item in findings:
            print(f"- {item['severity']} {item['id']}: {item['recommendation']}")
    else:
        print("No static findings.")
    print("Next: contextproof audit . --pr-comment")
    return 0


def command_explain(args: argparse.Namespace) -> int:
    path = Path(args.report)
    if not path.exists() or not path.is_file():
        raise ContextProofInputError(f"Report file does not exist: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if args.pr_comment:
        print(render_pr_comment(report))
    else:
        print(render_markdown_report(report))
    return 0


def command_summarize_runs(args: argparse.Namespace) -> int:
    summary = summarize_runs(Path(args.runs), deterministic=args.deterministic)
    if args.json_out:
        target = Path(args.json_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        target = Path(args.md_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_runs_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


def command_compare_context(args: argparse.Namespace) -> int:
    source = Path(args.source)
    candidate = Path(args.candidate)
    if not source.exists():
        raise ContextProofInputError(f"Source context path does not exist: {source}")
    if not candidate.exists():
        raise ContextProofInputError(f"Candidate context path does not exist: {candidate}")
    report = compare_contexts(
        source,
        candidate,
        deterministic=args.deterministic,
        project_mode=args.project_mode,
    )
    output_dir = Path(args.output_dir) if args.output_dir else Path.cwd() / ".contextproof"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = Path(args.json_out) if args.json_out else output_dir / "candidate-report.json"
    md_out = Path(args.md_out) if args.md_out else output_dir / "candidate-report.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_candidate_report(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def command_benchmark_optimizer(args: argparse.Namespace) -> int:
    scenarios_root = Path(args.scenarios).resolve()
    rows = build_optimizer_benchmark_rows(
        scenarios_root,
        prompt_variant=args.prompt_variant,
        deterministic=args.deterministic,
    )
    summary = summarize_optimizer_benchmark(rows, args.prompt_variant)
    if args.jsonl_out:
        target = Path(args.jsonl_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")
    if args.json_out:
        target = Path(args.json_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        target = Path(args.md_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_optimizer_benchmark_markdown(summary, rows), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit and benchmark AI agent context files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Audit repository agent context files.")
    audit.add_argument("repo", nargs="?", default=".", help="Repository path.")
    audit.add_argument("--json-out", help="Write JSON report to this path.")
    audit.add_argument("--md-out", help="Write markdown report to this path.")
    audit.add_argument("--output-dir", help="Write default ContextProof outputs to this directory.")
    audit.add_argument("--pr-comment", action="store_true", help="Write a local PR comment markdown file.")
    audit.add_argument("--minimize", action="store_true", help="Also write a generic starter context candidate.")
    audit.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    audit.add_argument("--runs", help="Optional benchmark JSONL file to merge into the audit report.")
    audit.add_argument("--changed-against", help="Git ref/range used to detect changed agent-context files.")
    audit.add_argument("--baseline", help="Previous ContextProof report.json to compare against.")
    audit.add_argument(
        "--project-mode",
        choices=["existing_project", "new_project", "migration_project", "existing_project_audit", "new_project_bootstrap"],
        default="existing_project",
        help="Declare whether this is an existing, new, or migration project context.",
    )
    audit.add_argument("--fail-under", type=int, help="Exit 1 when score is below this threshold.")
    audit.set_defaults(func=command_audit)

    minimize = subparsers.add_parser("minimize", help="Generate a generic AGENTS.md starter scaffold.")
    minimize.add_argument("repo", help="Repository path.")
    minimize.add_argument("--output", help="Write candidate to this path. Defaults to stdout.")
    minimize.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    minimize.add_argument(
        "--project-mode",
        choices=["existing_project", "new_project", "migration_project", "existing_project_audit", "new_project_bootstrap"],
        default="existing_project",
        help="Declare whether this is an existing, new, or migration project context.",
    )
    minimize.set_defaults(func=command_minimize)

    quickstart = subparsers.add_parser("quickstart", help="Run a first-time ContextProof check.")
    quickstart.add_argument("repo", nargs="?", default=".", help="Repository path.")
    quickstart.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    quickstart.add_argument(
        "--project-mode",
        choices=["existing_project", "new_project", "migration_project", "existing_project_audit", "new_project_bootstrap"],
        default="existing_project",
        help="Declare whether this is an existing, new, or migration project context.",
    )
    quickstart.set_defaults(func=command_quickstart)

    explain = subparsers.add_parser("explain", help="Explain a ContextProof JSON report.")
    explain.add_argument("report", help="Path to report.json.")
    explain.add_argument("--pr-comment", action="store_true", help="Render the PR comment form.")
    explain.set_defaults(func=command_explain)

    runs = subparsers.add_parser("summarize-runs", help="Summarize recorded benchmark JSONL runs.")
    runs.add_argument("runs", help="Path to benchmark JSONL file.")
    runs.add_argument("--json-out", help="Write JSON summary to this path.")
    runs.add_argument("--md-out", help="Write markdown summary to this path.")
    runs.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    runs.set_defaults(func=command_summarize_runs)

    compare = subparsers.add_parser("compare-context", help="Compare original agent context with an optimized candidate.")
    compare.add_argument("source", help="Original context file or repository directory.")
    compare.add_argument("candidate", help="Candidate context file or repository directory.")
    compare.add_argument("--json-out", help="Write JSON candidate comparison to this path.")
    compare.add_argument("--md-out", help="Write markdown candidate comparison to this path.")
    compare.add_argument("--output-dir", help="Write default candidate reports to this directory.")
    compare.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    compare.add_argument(
        "--project-mode",
        choices=["existing_project", "new_project", "migration_project", "existing_project_audit", "new_project_bootstrap"],
        default="existing_project",
        help="Declare whether this is an existing, new, or migration project context.",
    )
    compare.set_defaults(func=command_compare_context)

    optimizer = subparsers.add_parser("benchmark-optimizer", help="Record optimizer candidate results across scenario fixtures.")
    optimizer.add_argument("scenarios", nargs="?", default="examples/scenarios", help="Directory containing scenario fixtures.")
    optimizer.add_argument("--prompt-variant", default="baseline", help="Prompt variant label for flat candidate directories.")
    optimizer.add_argument("--jsonl-out", help="Write per-candidate benchmark rows as JSONL.")
    optimizer.add_argument("--json-out", help="Write benchmark summary JSON.")
    optimizer.add_argument("--md-out", help="Write benchmark summary markdown.")
    optimizer.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    optimizer.set_defaults(func=command_benchmark_optimizer)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return int(args.func(args))
    except ContextProofInputError as exc:
        print(f"ContextProof input error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ContextProof internal error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
