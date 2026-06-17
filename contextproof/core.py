#!/usr/bin/env python3
"""Audit and benchmark repository-level AI agent context files."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "0.1.0"

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

COMMAND_RE = re.compile(r"`([^`\n]*(?:npm|pnpm|yarn|bun|pytest|ruff|mypy|cargo|go test|make|just)[^`\n]*)`")

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
    if issue_id in {"large-context-file", "vague-rule", "duplicate-rule", "overconstrained-rules"}:
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
        severity = "medium" if project_mode == "new_project_bootstrap" else "high"
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


def audit_repo(root: Path, deterministic: bool = False, project_mode: str = "existing_project_audit") -> dict[str, Any]:
    context_files, issues, duplicates = analyze_context(root)
    commands = discover_commands(root)
    add_global_issues(context_files, commands, issues, project_mode)
    scoring = aggregate_score(context_files, commands, issues)
    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "root": str(root.resolve()),
        "project_mode": project_mode,
        "confidence_state": "static_only",
        "static_context_score": {
            "total": scoring["total"],
            "dimensions": scoring["dimensions"],
        },
        "benchmark_evidence": {
            "status": "not_provided",
            "reason": "No paired benchmark runs were provided.",
        },
        "summary": {
            "context_file_count": len(context_files),
            "total_context_tokens": sum(item.token_estimate for item in context_files),
            "command_count": len(commands),
            "issue_count": len(issues),
            "duplicate_rule_count": len(duplicates),
        },
        "context_files": [asdict(item) for item in context_files],
        "commands": [asdict(item) for item in commands],
        "findings": [finding_from_issue(item) for item in issues],
        "recommendations": build_recommendations(context_files, commands, issues),
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    static_score = report["static_context_score"]
    lines = [
        "# ContextProof Report",
        "",
        f"Static context score: {static_score['total']} / 100",
        f"Confidence state: {report['confidence_state']}",
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
    lines.extend(["", "## Findings", ""])
    if report["findings"]:
        for issue in report["findings"]:
            lines.append(f"- [{issue['severity']}] {issue['id']} in {issue['path']}: {issue['rationale']}")
            if issue["evidence"]:
                lines.append(f"  Evidence: {issue['evidence']}")
            lines.append(f"  Fix: {issue['recommendation']}")
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
        f"- Findings: {len(findings)} total, {len(high_findings)} critical/high",
        "",
    ]
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


def summarize_runs(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ContextProofInputError(f"Benchmark runs file does not exist: {path}")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ContextProofInputError(f"Invalid JSON on line {number}: {exc}") from exc
    variants: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        variants.setdefault(str(row.get("variant", "unknown")), []).append(row)

    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_evidence": {
            "status": "insufficient_evidence",
            "reason": "Recorded runs were summarized without paired-group inference.",
        },
        "run_count": len(rows),
        "variants": {},
    }
    for variant, items in sorted(variants.items()):
        successes = [bool(item.get("success")) for item in items]
        tests = [bool(item.get("tests_passed")) for item in items if "tests_passed" in item]
        input_tokens = [
            float(item.get("tokens_input", item.get("input_tokens", 0)))
            for item in items
            if item.get("tokens_input", item.get("input_tokens")) is not None
        ]
        output_tokens = [
            float(item.get("tokens_output", item.get("output_tokens", 0)))
            for item in items
            if item.get("tokens_output", item.get("output_tokens")) is not None
        ]
        durations = [float(item.get("duration_seconds", 0)) for item in items if item.get("duration_seconds") is not None]
        files_changed = [
            float(item.get("files_changed", item.get("files_touched", 0)))
            for item in items
            if item.get("files_changed", item.get("files_touched")) is not None
        ]
        files_read = [float(item.get("files_read", 0)) for item in items if item.get("files_read") is not None]
        summary["variants"][variant] = {
            "runs": len(items),
            "success_rate": sum(successes) / len(successes) if successes else 0.0,
            "tests_pass_rate": sum(tests) / len(tests) if tests else None,
            "avg_tokens_input": statistics.fmean(input_tokens) if input_tokens else None,
            "avg_tokens_output": statistics.fmean(output_tokens) if output_tokens else None,
            "avg_duration_seconds": statistics.fmean(durations) if durations else None,
            "avg_files_read": statistics.fmean(files_read) if files_read else None,
            "avg_files_changed": statistics.fmean(files_changed) if files_changed else None,
        }
    return summary


def render_runs_markdown(summary: dict[str, Any]) -> str:
    evidence = summary["benchmark_evidence"]
    lines = [
        "# ContextProof Benchmark Summary",
        "",
        f"Runs: {summary['run_count']}",
        f"Evidence status: `{evidence['status']}`",
        f"Evidence note: {evidence['reason']}",
        "",
        "## Variants",
        "",
    ]
    for variant, item in summary["variants"].items():
        lines.append(f"### {variant}")
        lines.append("")
        lines.append(f"- Runs: {item['runs']}")
        lines.append(f"- Success rate: {item['success_rate']:.2%}")
        if item["tests_pass_rate"] is not None:
            lines.append(f"- Tests pass rate: {item['tests_pass_rate']:.2%}")
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
    report = audit_repo(root, deterministic=args.deterministic, project_mode=args.project_mode)

    output_dir = Path(args.output_dir) if args.output_dir else root / ".contextproof"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = args.json_out or str(output_dir / "report.json")
    md_out = args.md_out or str(output_dir / "report.md")

    write_outputs(report, json_out, md_out)
    if args.pr_comment:
        target = output_dir / "pr-comment.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_pr_comment(report), encoding="utf-8")
    if args.minimize:
        (output_dir / "context.min.md").write_text(build_minimal_agents_md(report), encoding="utf-8")
        (output_dir / "minimize-rationale.md").write_text(
            "# ContextProof Minimize Rationale\n\n"
            "Generated from deterministic repository scan and command discovery. "
            "Review before replacing any existing agent context.\n",
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
    summary = summarize_runs(Path(args.runs))
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
    audit.add_argument(
        "--project-mode",
        choices=["existing_project_audit", "new_project_bootstrap"],
        default="existing_project_audit",
        help="Declare whether this is an existing-project audit or a new-project bootstrap.",
    )
    audit.add_argument("--fail-under", type=int, help="Exit 1 when score is below this threshold.")
    audit.set_defaults(func=command_audit)

    minimize = subparsers.add_parser("minimize", help="Generate a minimal AGENTS.md candidate.")
    minimize.add_argument("repo", help="Repository path.")
    minimize.add_argument("--output", help="Write candidate to this path. Defaults to stdout.")
    minimize.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    minimize.add_argument(
        "--project-mode",
        choices=["existing_project_audit", "new_project_bootstrap"],
        default="existing_project_audit",
        help="Declare whether this is an existing-project audit or a new-project bootstrap.",
    )
    minimize.set_defaults(func=command_minimize)

    quickstart = subparsers.add_parser("quickstart", help="Run a first-time ContextProof check.")
    quickstart.add_argument("repo", nargs="?", default=".", help="Repository path.")
    quickstart.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    quickstart.add_argument(
        "--project-mode",
        choices=["existing_project_audit", "new_project_bootstrap"],
        default="existing_project_audit",
        help="Declare whether this is an existing-project audit or a new-project bootstrap.",
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
    runs.set_defaults(func=command_summarize_runs)

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
