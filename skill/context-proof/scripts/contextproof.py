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


SCHEMA_VERSION = "0.5.0"

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
    ".contextproof",
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
    "INIT.md",
    "init.md",
    "AGENT_CONTEXT.md",
    "agent-context.md",
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
VALIDATION_GAP_PATTERNS = [
    r"\bno validation command exists\b",
    r"\bno (test|lint|build|typecheck) command exists\b",
    r"\breport (that )?(validation|test|testing) gap\b",
    r"\breport the reason\b.*\btests? cannot run\b",
]
NEGATION_PREFIX_RE = re.compile(
    r"\b(do\s+not|don't|never|must\s+not|should\s+not|skip|avoid|without|no\s+need\s+to|not\s+required\s+to)\b",
    re.I,
)
NEGATION_SUFFIX_RE = re.compile(
    r"\b(can\s+be\s+skipped|may\s+be\s+skipped|should\s+be\s+skipped|is\s+optional|are\s+optional|not\s+required)\b",
    re.I,
)
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

SCENARIO_DEFINITIONS: dict[str, dict[str, Any]] = {
    "new-project-init-summary": {
        "name": "New-project /init summary",
        "template": "new-project-init.md",
        "doc_role": "bootstrap-agent-brief",
        "description": "A saved /init-style repository brief that should become concise project onboarding context.",
        "default_focus": ["repository-map", "validation", "acceptance-criteria", "token-reduction"],
    },
    "existing-project-agent-rules": {
        "name": "Existing-project agent rules",
        "template": "existing-project-rules.md",
        "doc_role": "persistent-agent-instructions",
        "description": "Repository-level rules for a coding agent working in an established codebase.",
        "default_focus": ["executability", "validation", "rule-clarity", "token-reduction"],
    },
    "multi-agent-context-migration": {
        "name": "Multi-agent context migration",
        "template": "multi-agent-migration.md",
        "doc_role": "agent-context-migration",
        "description": "Overlapping context across multiple agent surfaces that should be consolidated or de-duplicated.",
        "default_focus": ["deduplication", "conflict-resolution", "canonical-context", "preservation"],
    },
    "workflow-sop-context": {
        "name": "Workflow or SOP context",
        "template": "workflow-sop.md",
        "doc_role": "repeatable-agent-workflow",
        "description": "A repeatable workflow, runbook, review, release, or validation procedure for an agent.",
        "default_focus": ["ordered-steps", "preconditions", "commands", "acceptance-criteria"],
    },
    "safety-sensitive-context": {
        "name": "Safety-sensitive context",
        "template": "safety-sensitive.md",
        "doc_role": "safety-bound-agent-instructions",
        "description": "Agent context that touches destructive commands, secrets, production data, deploys, or migrations.",
        "default_focus": ["negative-constraints", "approval-gates", "safe-defaults", "validation"],
    },
    "token-heavy-context": {
        "name": "Token-heavy context",
        "template": "token-heavy.md",
        "doc_role": "oversized-agent-context",
        "description": "Long or repetitive agent context where the main risk is token waste and low information density.",
        "default_focus": ["compression", "deduplication", "information-density", "preservation"],
    },
}

SCENARIO_PRIORITY = [
    "safety-sensitive-context",
    "multi-agent-context-migration",
    "new-project-init-summary",
    "workflow-sop-context",
    "token-heavy-context",
    "existing-project-agent-rules",
]


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


def is_under_path(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


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
    if name == "SKILL.md" and "skills" in parts and "context-proof" in parts:
        return False
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
    if name == "SKILL.md" and "skills" in parts and "context-proof" in parts:
        return False
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
    if path.name == "GEMINI.md":
        return "gemini"
    if ".cursor/rules/" in relative:
        return "cursor"
    if path.name == "SKILL.md":
        return "skill"
    if path.name in {"INIT.md", "init.md", "AGENT_CONTEXT.md", "agent-context.md"}:
        return "init-brief"
    if path.name in {"MCP.md", "MCP-SERVER.md"}:
        return "mcp"
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


def context_discovery_reason(path: Path, kind: str, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    if relative == "AGENTS.md":
        return "Repository-level agent instructions loaded by many coding agents."
    if path.name == "CLAUDE.md":
        return "Claude Code repository context file."
    if path.name == "GEMINI.md":
        return "Gemini-style repository context file."
    if ".cursor/rules/" in relative:
        return "Cursor rule file under .cursor/rules."
    if relative == ".github/copilot-instructions.md":
        return "GitHub Copilot repository instruction file."
    if path.name == "SKILL.md":
        return "Agent skill instruction file that may be loaded into prompt context."
    if kind == "mcp":
        return "MCP note file that can guide tool or server usage."
    if kind == "init-brief":
        return "Saved /init-style repository brief that may be reused as agent context."
    return "Supported persistent agent-context filename."


def discover_context_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path, kind in discover_context_files(root):
        text = read_text(path)
        relative = rel(path, root)
        entries.append(
            {
                "path": relative,
                "absolute_path": str(path.resolve()),
                "kind": kind,
                "chars": len(text),
                "lines": len(text.splitlines()),
                "token_estimate": estimate_tokens(text),
                "reason": context_discovery_reason(path, kind, root),
            }
        )
    return entries


def ordinary_markdown_files(root: Path, limit: int = 20) -> list[str]:
    items: list[str] = []
    for path in iter_repo_files(root):
        if path.suffix.lower() not in {".md", ".mdc", ".txt"}:
            continue
        if is_context_file(path, root):
            continue
        items.append(rel(path, root))
        if len(items) >= limit:
            break
    return sorted(items)


def discover_context_report(
    root: Path,
    deterministic: bool = False,
    project_mode: str = "existing_project",
) -> dict[str, Any]:
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise ContextProofInputError(f"Repository path does not exist or is not a directory: {root}")
    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    entries = discover_context_entries(root)
    ordinary = ordinary_markdown_files(root)
    warnings: list[str] = []
    if not entries:
        warnings.append(
            "No supported agent-facing context files were found. Ordinary README or docs files are not audited unless they are loaded into agent context."
        )
    if not entries and ordinary:
        warnings.append(
            "Ordinary Markdown files were found, but they are outside ContextProof scope unless a coding agent reads them as persistent context."
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "discovery_type": "agent_context_files",
        "root": str(root),
        "project_mode": normalize_project_mode(project_mode),
        "context_file_count": len(entries),
        "context_files": entries,
        "ordinary_markdown_examples": ordinary,
        "warnings": warnings,
        "scope_note": "ContextProof audits persistent Markdown loaded into coding-agent prompt context, not general project documentation.",
    }


def render_context_discovery_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ContextProof Context Discovery",
        "",
        f"Root: `{report['root']}`",
        f"Agent-context files: {report['context_file_count']}",
        "",
        "## In Scope",
        "",
    ]
    if report["context_files"]:
        for item in report["context_files"]:
            lines.append(f"- `{item['path']}` ({item['kind']}): {item['reason']}")
    else:
        lines.append("- No supported agent-facing context files found.")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    if report["ordinary_markdown_examples"]:
        lines.extend(["", "## Ordinary Markdown Examples", ""])
        for item in report["ordinary_markdown_examples"][:10]:
            lines.append(f"- `{item}`")
        lines.append("")
        lines.append("These files are not optimization targets unless they are explicitly loaded as agent context.")
    lines.append("")
    return "\n".join(lines)


def has_validation_gap_policy(text: str) -> bool:
    return any(re.search(pattern, text, re.I | re.M) for pattern in VALIDATION_GAP_PATTERNS)


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
        if has_validation_gap_policy(text):
            commands.append(Command("validation-gap", "report validation gap and manual checks", relative, "low"))

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


def context_output_dir(source: Path) -> Path:
    anchor = source if source.is_dir() else source.parent
    try:
        root = git_output(anchor, ["rev-parse", "--show-toplevel"]).strip()
        if root:
            return Path(root) / ".contextproof"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return anchor / ".contextproof"


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


def text_negates_item(text: str, item: str) -> bool:
    item = item.strip()
    if not item or item not in text:
        return False
    escaped = re.escape(item)
    item_pattern = rf"`?{escaped}`?"
    for line in text.splitlines():
        if item not in line:
            continue
        negated_before = rf"{NEGATION_PREFIX_RE.pattern}[^.\n;:]{{0,90}}{item_pattern}"
        negated_after = rf"{item_pattern}[^.\n;:]{{0,90}}{NEGATION_SUFFIX_RE.pattern}"
        if re.search(negated_before, line, re.I) or re.search(negated_after, line, re.I):
            return True
    return False


def negated_items(text: str, items: Iterable[str]) -> list[str]:
    return sorted({item for item in items if text_negates_item(text, str(item))})


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


def count_regex_matches(text: str, patterns: list[str]) -> int:
    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, text, re.I | re.M))
    return total


def add_signal(
    scores: dict[str, int],
    evidence: dict[str, list[str]],
    scenario_id: str,
    points: int,
    reason: str,
) -> None:
    scores[scenario_id] = scores.get(scenario_id, 0) + points
    evidence.setdefault(scenario_id, []).append(reason)


def classify_context_scenario(
    path: Path,
    deterministic: bool = False,
    project_mode: str = "existing_project",
) -> dict[str, Any]:
    path = path.resolve()
    if not path.exists():
        raise ContextProofInputError(f"Context path does not exist: {path}")
    normalized_project_mode = normalize_project_mode(project_mode)
    text = context_input_text(path)
    lower = text.lower()
    report = audit_context_input(path, deterministic=deterministic, project_mode=normalized_project_mode)
    issue_ids = {str(item["id"]) for item in report.get("findings", [])}
    context_files = report.get("context_files", [])
    context_file_count = int(report.get("summary", {}).get("context_file_count", 0))
    total_tokens = int(report.get("summary", {}).get("total_context_tokens", estimate_tokens(text)))
    command_count = int(report.get("summary", {}).get("command_count", 0))

    scores = {scenario_id: 0 for scenario_id in SCENARIO_DEFINITIONS}
    evidence: dict[str, list[str]] = {scenario_id: [] for scenario_id in SCENARIO_DEFINITIONS}

    add_signal(scores, evidence, "existing-project-agent-rules", 1, "baseline route for persistent agent instructions")
    if normalized_project_mode == "existing_project":
        add_signal(scores, evidence, "existing-project-agent-rules", 2, "project mode is existing_project")
    if context_file_count:
        add_signal(scores, evidence, "existing-project-agent-rules", 1, f"{context_file_count} agent context file(s) detected")

    new_project_hits = count_regex_matches(
        lower,
        [
            r"/init\b",
            r"\binitial (project|repository) brief\b",
            r"\bnew project\b",
            r"\bbootstrap\b",
            r"\bproject overview\b",
            r"\brepository overview\b",
            r"\bscaffold\b",
        ],
    )
    if normalized_project_mode == "new_project":
        add_signal(scores, evidence, "new-project-init-summary", 4, "project mode is new_project")
    if new_project_hits:
        add_signal(scores, evidence, "new-project-init-summary", min(4, new_project_hits), "init or repository-overview language detected")
    if normalized_project_mode == "new_project" and context_file_count <= 1:
        add_signal(scores, evidence, "new-project-init-summary", 1, "single-file new-project context")

    agent_surface_hits = count_regex_matches(
        lower,
        [
            r"\bagents\.md\b",
            r"\bclaude\.md\b",
            r"\bgemini\.md\b",
            r"\.cursor/rules",
            r"\.windsurfrules",
            r"\.clinerules",
            r"\bcopilot-instructions\.md\b",
            r"\bopencode\b",
        ],
    )
    if normalized_project_mode == "migration_project":
        add_signal(scores, evidence, "multi-agent-context-migration", 4, "project mode is migration_project")
    if context_file_count >= 2:
        add_signal(scores, evidence, "multi-agent-context-migration", 3, "multiple agent context files detected")
    if agent_surface_hits >= 3:
        add_signal(scores, evidence, "multi-agent-context-migration", 2, "multiple agent surfaces are referenced")
    if (context_file_count >= 2 or normalized_project_mode == "migration_project" or agent_surface_hits >= 3) and {
        "duplicate-rule",
        "conflicting-rule",
    } & issue_ids:
        add_signal(scores, evidence, "multi-agent-context-migration", 2, "duplicate or conflicting rules detected")

    workflow_hits = count_regex_matches(
        lower,
        [
            r"\bworkflow\b",
            r"\bsop\b",
            r"\brunbook\b",
            r"\brelease\b",
            r"\bdeploy\b",
            r"\breview checklist\b",
            r"\bbefore (merging|release|deploying)\b",
            r"\bafter (editing|changing|release)\b",
            r"^#+\s*(workflow|release|deploy|review|validation|runbook)\b",
        ],
    )
    if workflow_hits:
        add_signal(scores, evidence, "workflow-sop-context", min(5, workflow_hits), "workflow, runbook, release, deploy, or review language detected")
    if command_count >= 2 and workflow_hits:
        add_signal(scores, evidence, "workflow-sop-context", 1, "multiple commands appear in workflow-like context")

    safety_hits = count_regex_matches(
        lower,
        [
            r"\bproduction\b",
            r"\bprod\b",
            r"\bdatabase\b",
            r"\bdb\b",
            r"\bmigration\b",
            r"\bsecrets?\b",
            r"\bcredentials?\b",
            r"\bdeploy\b",
            r"\bdelete\b",
            r"\bdrop\b",
            r"\bdestroy\b",
            r"\brm -rf\b",
            r"\bsudo\b",
            r"\bchmod 777\b",
            r"\b\.env\b",
        ],
    )
    if "risky-shell" in issue_ids:
        add_signal(scores, evidence, "safety-sensitive-context", 5, "risky shell or prompt-injection-like pattern detected")
    if safety_hits:
        add_signal(scores, evidence, "safety-sensitive-context", min(5, safety_hits), "production, data, secret, deploy, or destructive-operation language detected")

    if total_tokens >= 1200:
        add_signal(scores, evidence, "token-heavy-context", 3, f"context is large for persistent prompt use ({total_tokens} estimated tokens)")
    if total_tokens >= 2000:
        add_signal(scores, evidence, "token-heavy-context", 2, "context is very large")
    if {"large-context-file", "large-context-set"} & issue_ids:
        add_signal(scores, evidence, "token-heavy-context", 3, "large context finding detected")
    if {"vague-rule", "overbroad-context"} <= issue_ids and "duplicate-rule" in issue_ids:
        add_signal(scores, evidence, "token-heavy-context", 3, "repeated low-density context rules detected")
    if "misplaced-general-docs" in issue_ids:
        add_signal(scores, evidence, "token-heavy-context", 5, "ordinary product or planning documentation is mixed into agent context")
    monorepo_hits = count_regex_matches(
        lower,
        [
            r"\bmonorepo\b",
            r"\bworkspace\b",
            r"\bapps/",
            r"\bservices/",
            r"\bpackages/",
            r"\brepeat",
        ],
    )
    if monorepo_hits >= 4 and "duplicate-rule" in issue_ids:
        add_signal(scores, evidence, "token-heavy-context", 4, "repetitive monorepo map detected")
    if {"duplicate-rule", "vague-rule", "overbroad-context", "misplaced-general-docs"} & issue_ids:
        add_signal(scores, evidence, "token-heavy-context", 1, "low-density context findings detected")

    primary = max(
        SCENARIO_DEFINITIONS,
        key=lambda scenario_id: (scores[scenario_id], -SCENARIO_PRIORITY.index(scenario_id)),
    )
    if scores[primary] <= 0:
        primary = "existing-project-agent-rules"
    secondary = [
        scenario_id
        for scenario_id in SCENARIO_PRIORITY
        if scenario_id != primary and scores.get(scenario_id, 0) >= 2
    ][:4]
    sorted_scores = sorted(scores.values(), reverse=True)
    score_gap = sorted_scores[0] - (sorted_scores[1] if len(sorted_scores) > 1 else 0)
    confidence = "high" if scores[primary] >= 5 and score_gap >= 2 else "medium" if scores[primary] >= 3 else "low"

    focus = list(SCENARIO_DEFINITIONS[primary]["default_focus"])
    focus_by_issue = {
        "missing-test-command": "validation",
        "vague-rule": "executability",
        "overbroad-context": "task-scoped-discovery",
        "duplicate-rule": "deduplication",
        "conflicting-rule": "conflict-resolution",
        "risky-shell": "safety",
        "misplaced-general-docs": "context-boundary",
        "large-context-file": "token-reduction",
        "large-context-set": "token-reduction",
        "overconstrained-rules": "negative-constraint-pruning",
    }
    for issue_id in sorted(issue_ids):
        mapped = focus_by_issue.get(issue_id)
        if mapped and mapped not in focus:
            focus.append(mapped)
    for scenario_id in secondary:
        for item in SCENARIO_DEFINITIONS[scenario_id]["default_focus"][:2]:
            if item not in focus:
                focus.append(item)

    critical_high = severity_count(report, {"critical", "high"})
    if primary == "safety-sensitive-context" or "risky-shell" in issue_ids:
        risk_level = "high"
    elif critical_high or {"conflicting-rule", "missing-test-command"} & issue_ids:
        risk_level = "medium"
    else:
        risk_level = "low"

    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    template = SCENARIO_DEFINITIONS[primary]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "classification_type": "agent_context_scenario",
        "source_path": str(path),
        "project_mode": normalized_project_mode,
        "primary_scenario": primary,
        "primary_scenario_name": template["name"],
        "secondary_scenarios": secondary,
        "doc_role": template["doc_role"],
        "optimization_focus": focus,
        "risk_level": risk_level,
        "confidence": confidence,
        "selected_template": {
            "id": primary,
            "name": template["name"],
            "reference_path": f"references/templates/{template['template']}",
            "description": template["description"],
        },
        "scenario_scores": {
            scenario_id: {
                "score": scores[scenario_id],
                "evidence": evidence.get(scenario_id, []),
            }
            for scenario_id in SCENARIO_PRIORITY
        },
        "audit_summary": compact_report_summary(report),
    }


def render_classification_markdown(classification: dict[str, Any]) -> str:
    lines = [
        "# ContextProof Context Classification",
        "",
        f"Source: `{classification['source_path']}`",
        f"Primary scenario: `{classification['primary_scenario']}`",
        f"Template: `{classification['selected_template']['reference_path']}`",
        f"Doc role: `{classification['doc_role']}`",
        f"Risk level: `{classification['risk_level']}`",
        f"Confidence: `{classification['confidence']}`",
        "",
        "## Optimization Focus",
        "",
    ]
    for item in classification["optimization_focus"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Secondary Scenarios", ""])
    if classification["secondary_scenarios"]:
        for item in classification["secondary_scenarios"]:
            lines.append(f"- `{item}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Scenario Evidence", ""])
    for scenario_id, item in classification["scenario_scores"].items():
        if item["score"] <= 0:
            continue
        lines.append(f"### {scenario_id}")
        lines.append("")
        lines.append(f"- Score: {item['score']}")
        for reason in item["evidence"]:
            lines.append(f"- {reason}")
        lines.append("")
    lines.extend(
        [
            "## Audit Summary",
            "",
            f"- Static score: {classification['audit_summary']['score']} / 100",
            f"- Estimated tokens: {classification['audit_summary']['total_context_tokens']}",
            f"- Critical/high findings: {classification['audit_summary']['critical_high_finding_count']}",
            "",
        ]
    )
    return "\n".join(lines)


def candidate_output_hint(path: Path) -> str:
    if path.is_file():
        stem = path.stem or "AGENTS"
        suffix = path.suffix if path.suffix in {".md", ".mdc", ".txt"} else ".md"
        return f".contextproof/candidates/{stem}.contextproof{suffix}"
    return ".contextproof/candidates/AGENTS.contextproof.md"


def build_optimizer_route(
    path: Path,
    deterministic: bool = False,
    project_mode: str = "existing_project",
) -> dict[str, Any]:
    classification = classify_context_scenario(path, deterministic=deterministic, project_mode=project_mode)
    source = Path(classification["source_path"])
    candidate_hint = candidate_output_hint(source)
    template = classification["selected_template"]
    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    instruction = render_optimizer_instruction(classification, candidate_hint)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "route_type": "optimizer_template_route",
        "source_path": classification["source_path"],
        "candidate_output_hint": candidate_hint,
        "selected_template": template,
        "classification": classification,
        "instruction": instruction,
    }


def render_optimizer_instruction(classification: dict[str, Any], candidate_hint: str) -> str:
    template = classification["selected_template"]
    focus = ", ".join(classification["optimization_focus"])
    secondary = ", ".join(classification["secondary_scenarios"]) or "none"
    source_path = classification["source_path"]
    return "\n".join(
        [
            "# ContextProof Optimizer Route",
            "",
            "Use this instruction as the scenario-specific prompt for the coding agent that will draft the optimized context candidate.",
            "",
            "## Route",
            "",
            f"- Source: `{source_path}`",
            f"- Primary scenario: `{classification['primary_scenario']}`",
            f"- Secondary scenarios: {secondary}",
            f"- Template reference: `{template['reference_path']}`",
            f"- Candidate path: `{candidate_hint}`",
            f"- Risk level: `{classification['risk_level']}`",
            f"- Optimization focus: {focus}",
            "",
            "## Agent Task",
            "",
            f"Read `{template['reference_path']}` and the ContextProof audit report before editing.",
            f"Draft a safer, shorter, more executable candidate for `{source_path}` at `{candidate_hint}`.",
            "Preserve explicit validation commands, repository paths, package names, architecture facts, and active safety constraints.",
            "Remove generic quality advice, duplicated rules, stale planning prose, and instructions that cannot be verified.",
            "Do not overwrite source context files.",
            "",
            "After writing the candidate, run:",
            "",
            "```bash",
            f"contextproof compare-context \"{source_path}\" \"{candidate_hint}\"",
            "```",
            "",
            "Report the candidate path, selected template, score delta, token delta, preserved commands, unresolved risks, and regression flags.",
            "",
        ]
    )


def render_optimizer_route_markdown(route: dict[str, Any]) -> str:
    return route["instruction"]


def workflow_source_path(root: Path, discovery: dict[str, Any]) -> Path:
    files = discovery.get("context_files", [])
    if len(files) == 1:
        return Path(str(files[0]["absolute_path"])).resolve()
    return root.resolve()


def build_workflow_packet(
    root: Path,
    deterministic: bool = False,
    project_mode: str = "existing_project",
    output_dir: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise ContextProofInputError(f"Repository path does not exist or is not a directory: {root}")
    normalized_project_mode = normalize_project_mode(project_mode)
    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    output_dir = (output_dir.resolve() if output_dir else root / ".contextproof")
    discovery = discover_context_report(root, deterministic=deterministic, project_mode=normalized_project_mode)
    audit = audit_repo(root, deterministic=deterministic, project_mode=normalized_project_mode)
    source = workflow_source_path(root, discovery)
    route = build_optimizer_route(source, deterministic=deterministic, project_mode=normalized_project_mode)
    classification = route["classification"]
    candidate_hint = route["candidate_output_hint"]
    candidate_path = (root / candidate_hint).resolve()
    workflow_markdown = output_dir / "workflow.md"
    compare_command = f'contextproof review-candidate "{source}" "{candidate_hint}"'
    next_instruction = (
        "Read .contextproof/workflow.md and .contextproof/optimizer-instructions.md. "
        f"Draft the optimized agent-context candidate at {candidate_hint}. "
        "Do not overwrite source context files. After writing the candidate, run "
        f"{compare_command} and report the candidate review status."
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "workflow_type": "one_prompt_context_optimization",
        "root": str(root),
        "project_mode": normalized_project_mode,
        "output_dir": str(output_dir),
        "source_path": str(source),
        "selected_context_files": discovery["context_files"],
        "warnings": discovery["warnings"],
        "audit_summary": compact_report_summary(audit),
        "classification": classification,
        "candidate": {
            "relative_path": candidate_hint,
            "absolute_path": str(candidate_path),
        },
        "outputs": {
            "discovery_json": str(output_dir / "context-discovery.json"),
            "discovery_md": str(output_dir / "context-discovery.md"),
            "audit_json": str(output_dir / "report.json"),
            "audit_md": str(output_dir / "report.md"),
            "classification_json": str(output_dir / "context-classification.json"),
            "classification_md": str(output_dir / "context-classification.md"),
            "optimizer_route_json": str(output_dir / "optimizer-route.json"),
            "optimizer_instructions_md": str(output_dir / "optimizer-instructions.md"),
            "workflow_json": str(output_dir / "workflow.json"),
            "workflow_md": str(workflow_markdown),
        },
        "next_agent_instruction": next_instruction,
    }


def render_workflow_markdown(workflow: dict[str, Any]) -> str:
    classification = workflow["classification"]
    audit = workflow["audit_summary"]
    candidate = workflow["candidate"]
    lines = [
        "# ContextProof Workflow",
        "",
        "Use this packet to draft one optimized agent-context candidate. Do not overwrite source context files.",
        "",
        "## Source Scope",
        "",
        f"- Root: `{workflow['root']}`",
        f"- Source for comparison: `{workflow['source_path']}`",
    ]
    if workflow["selected_context_files"]:
        lines.append("- In-scope context files:")
        for item in workflow["selected_context_files"]:
            lines.append(f"  - `{item['path']}`: {item['reason']}")
    else:
        lines.append("- No existing agent-context file was found. Draft a new candidate only under `.contextproof/candidates/`.")
    if workflow["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in workflow["warnings"]:
            lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "## Route",
            "",
            f"- Primary scenario: `{classification['primary_scenario']}`",
            f"- Template: `{classification['selected_template']['reference_path']}`",
            f"- Risk level: `{classification['risk_level']}`",
            f"- Confidence: `{classification['confidence']}`",
            "",
            "## Current Audit",
            "",
            f"- Static score: {audit['score']} / 100",
            f"- Estimated tokens: {audit['total_context_tokens']}",
            f"- Critical/high findings: {audit['critical_high_finding_count']}",
            "",
            "## Candidate Task",
            "",
            f"- Write candidate to `{candidate['relative_path']}`.",
            "- Preserve explicit validation commands, project paths, architecture facts, and safety constraints.",
            "- Remove or tighten vague, duplicated, overbroad, unsafe, stale, or non-verifiable instructions.",
            "- Keep ordinary README/product documentation out of persistent agent context unless it is actually loaded by the agent.",
            "- Do not overwrite `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `SKILL.md`, or any other source context file.",
            "",
            "## Next Agent Instruction",
            "",
            "```text",
            workflow["next_agent_instruction"],
            "```",
            "",
            "## After Candidate Is Written",
            "",
            "Run:",
            "",
            "```bash",
            f"contextproof review-candidate \"{workflow['source_path']}\" \"{candidate['relative_path']}\"",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


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
    negated_commands = negated_items(candidate_text, source_commands & candidate_commands)
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
    if negated_commands:
        regression_flags.append("negated-validation-command")
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
            "negated_validation_commands": negated_commands,
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


def build_candidate_review(comparison: dict[str, Any]) -> dict[str, Any]:
    flags = set(comparison.get("regression_flags", []))
    preservation = comparison.get("preservation", {})
    deltas = comparison.get("deltas", {})
    source_tokens = int(comparison.get("source", {}).get("total_context_tokens") or 0)
    candidate_tokens = int(comparison.get("candidate", {}).get("total_context_tokens") or 0)
    introduced = comparison.get("introduced_findings", [])
    blockers: list[dict[str, Any]] = []

    def add_blocker(blocker_id: str, severity: str, message: str, evidence: str) -> None:
        blockers.append(
            {
                "id": blocker_id,
                "severity": severity,
                "message": message,
                "evidence": evidence,
            }
        )

    if "safety-score-decreased" in flags or any(item.get("id") == "risky-shell" for item in introduced):
        add_blocker(
            "unsafe-regression",
            "critical",
            "Candidate introduces or weakens safety-critical context.",
            "Safety score decreased or risky-shell finding was introduced.",
        )
    if "dropped-all-validation-commands" in flags or "removed-some-validation-commands" in flags:
        removed = preservation.get("removed_validation_commands", [])
        add_blocker(
            "removed-validation-command",
            "high",
            "Candidate removed validation commands from the source context.",
            ", ".join(f"`{item}`" for item in removed) if removed else "All validation commands were dropped.",
        )
    if "negated-validation-command" in flags:
        negated = preservation.get("negated_validation_commands", [])
        add_blocker(
            "negated-validation-command",
            "high",
            "Candidate kept a validation command but told the agent not to run it.",
            ", ".join(f"`{item}`" for item in negated) if negated else "Validation command was negated.",
        )
    if "dropped-all-path-markers" in flags or "dropped-most-path-markers" in flags:
        removed_paths = preservation.get("removed_path_markers", [])
        add_blocker(
            "removed-project-path-anchor",
            "high",
            "Candidate removed too many project path anchors.",
            ", ".join(f"`{item}`" for item in removed_paths[:10]) if removed_paths else "Project path anchors were removed.",
        )
    if "introduced-critical-or-high-finding" in flags:
        high_items = [item for item in introduced if item.get("severity") in {"critical", "high"}]
        add_blocker(
            "new-critical-high-issue",
            "high",
            "Candidate introduced a critical or high severity context issue.",
            ", ".join(f"`{item.get('id')}`" for item in high_items[:10]) if high_items else "Critical/high finding introduced.",
        )
    if source_tokens and candidate_tokens <= max(1, int(source_tokens * 0.45)):
        preservation_loss = bool(
            preservation.get("removed_validation_commands")
            or preservation.get("removed_path_markers")
            or preservation.get("negated_validation_commands")
        )
        if preservation_loss or int(deltas.get("score_delta") or 0) <= 0:
            add_blocker(
                "overcompression",
                "medium",
                "Candidate is much shorter and may have removed useful execution context.",
                f"Token estimate changed from {source_tokens} to {candidate_tokens}.",
            )

    hard_blockers = {
        "unsafe-regression",
        "removed-validation-command",
        "negated-validation-command",
        "removed-project-path-anchor",
        "new-critical-high-issue",
    }
    blocker_ids = {item["id"] for item in blockers}
    if blocker_ids & hard_blockers:
        adoption_status = "do_not_adopt_yet"
    elif blockers:
        adoption_status = "review_required"
    elif comparison.get("verdict") == "improved":
        adoption_status = "safe_to_consider"
    else:
        adoption_status = "review_required"

    if adoption_status == "safe_to_consider":
        recommendation = "Safe to consider after manual review. Do not overwrite the source file until the user explicitly approves."
    elif adoption_status == "do_not_adopt_yet":
        recommendation = "Do not adopt this candidate yet. Resolve blockers and run ContextProof review again."
    else:
        recommendation = "Review required. The candidate is not clearly safer and more useful than the source."

    return {
        "schema_version": comparison["schema_version"],
        "generated_at": comparison["generated_at"],
        "review_type": "candidate_adoption_review",
        "source_path": comparison["source_path"],
        "candidate_path": comparison["candidate_path"],
        "adoption_status": adoption_status,
        "recommendation": recommendation,
        "blockers": blockers,
        "comparison": comparison,
    }


def render_candidate_review_markdown(review: dict[str, Any]) -> str:
    comparison = review["comparison"]
    deltas = comparison["deltas"]
    lines = [
        "# ContextProof Candidate Review",
        "",
        f"Adoption status: `{review['adoption_status']}`",
        f"Comparison verdict: `{comparison['verdict']}`",
        f"Source: `{review['source_path']}`",
        f"Candidate: `{review['candidate_path']}`",
        "",
        "## Blockers",
        "",
    ]
    if review["blockers"]:
        for item in review["blockers"]:
            lines.append(f"- **{item['severity']}** `{item['id']}`: {item['message']}")
            if item["evidence"]:
                lines.append(f"  Evidence: {item['evidence']}")
    else:
        lines.append("- No adoption blockers detected by deterministic checks.")
    lines.extend(
        [
            "",
            "## Score And Size",
            "",
            f"- Source score: {comparison['source']['score']} / 100",
            f"- Candidate score: {comparison['candidate']['score']} / 100",
            f"- Score delta: {deltas['score_delta']:+d}",
            f"- Estimated token delta: {deltas['token_delta']:+d}",
            f"- Critical/high finding delta: {deltas['critical_high_finding_delta']:+d}",
            f"- Resolved findings: {deltas['resolved_finding_count']}",
            f"- Introduced findings: {deltas['introduced_finding_count']}",
            "",
            "## Recommendation",
            "",
            review["recommendation"],
            "",
        ]
    )
    return "\n".join(lines)


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
    if preservation.get("negated_validation_commands"):
        lines.append("")
        lines.append("Negated validation commands:")
        for item in preservation["negated_validation_commands"]:
            lines.append(f"- `{item}`")
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


def resolve_gold_path(scenario_dir: Path, expected: dict[str, Any]) -> Path:
    raw = str(expected.get("gold_path") or "gold/AGENTS.gold.md")
    return (scenario_dir / raw).resolve()


def required_gold_preservation(expected: dict[str, Any]) -> list[str]:
    values = expected.get("gold_must_preserve") or expected.get("preserve") or []
    return [str(item) for item in values if str(item).strip()]


def is_validation_like_preservation(item: str) -> bool:
    return bool(re.search(r"\b(npm|pnpm|yarn|bun|pytest|ruff|mypy|cargo|go test|make|just)\b", item, re.I))


def issue_ids_from_summary(summary: dict[str, Any]) -> set[str]:
    return {str(item.get("id")) for item in summary.get("findings", []) if item.get("id")}


def high_finding_count_from_summary(summary: dict[str, Any]) -> int:
    return sum(1 for item in summary.get("findings", []) if item.get("severity") in {"critical", "high"})


def evaluate_gold_candidate(
    scenario_dir: Path,
    candidate_path: Path,
    deterministic: bool = False,
) -> dict[str, Any]:
    scenario_dir = scenario_dir.resolve()
    if not scenario_dir.exists() or not scenario_dir.is_dir():
        raise ContextProofInputError(f"Scenario directory does not exist: {scenario_dir}")
    expected = load_scenario_expected(scenario_dir)
    source = scenario_dir / "source"
    if not source.exists():
        raise ContextProofInputError(f"Scenario source directory does not exist: {source}")
    candidate_path = candidate_path.resolve()
    if not candidate_path.exists():
        raise ContextProofInputError(f"Candidate path does not exist: {candidate_path}")
    gold_path = resolve_gold_path(scenario_dir, expected)
    if not gold_path.exists():
        raise ContextProofInputError(f"Gold candidate does not exist: {gold_path}")

    project_mode = normalize_project_mode(str(expected.get("project_mode") or "existing_project"))
    source_candidate = compare_contexts(source, candidate_path, deterministic=deterministic, project_mode=project_mode)
    source_gold = compare_contexts(source, gold_path, deterministic=deterministic, project_mode=project_mode)
    gold_candidate = compare_contexts(gold_path, candidate_path, deterministic=deterministic, project_mode=project_mode)
    classification = classify_context_scenario(source, deterministic=deterministic, project_mode=project_mode)

    candidate_text = context_input_text(candidate_path)
    gold_text = context_input_text(gold_path)
    required_preserve = required_gold_preservation(expected)
    missing_preservation = [item for item in required_preserve if item not in candidate_text]
    negated_preservation = [
        item
        for item in required_preserve
        if item in candidate_text and is_validation_like_preservation(item) and text_negates_item(candidate_text, item)
    ]
    missing_gold_preservation = [item for item in required_preserve if item not in gold_text]

    expected_removed = {str(item) for item in expected.get("gold_must_remove_issue_ids", [])}
    candidate_issue_ids = issue_ids_from_summary(source_candidate["candidate"])
    gold_issue_ids = issue_ids_from_summary(source_gold["candidate"])
    unresolved_expected_issues = sorted(expected_removed & candidate_issue_ids)
    extra_candidate_findings_vs_gold = sorted(candidate_issue_ids - gold_issue_ids)

    source_candidate_flags = set(source_candidate["regression_flags"])
    gold_candidate_flags = set(gold_candidate["regression_flags"])
    candidate_critical_high = high_finding_count_from_summary(source_candidate["candidate"])
    source_critical_high = high_finding_count_from_summary(source_candidate["source"])
    unsafe_regression_count = 0
    if "safety-score-decreased" in source_candidate_flags:
        unsafe_regression_count += 1
    if "risky-shell" in candidate_issue_ids:
        unsafe_regression_count += 1

    overcompression_flags: list[str] = []
    for flag in ["dropped-all-path-markers", "dropped-most-path-markers"]:
        if flag in source_candidate_flags or flag in gold_candidate_flags:
            overcompression_flags.append(flag)
    candidate_tokens = int(source_candidate["candidate"]["total_context_tokens"])
    gold_tokens = int(source_gold["candidate"]["total_context_tokens"])
    if gold_tokens and candidate_tokens < max(5, math.floor(gold_tokens * 0.45)):
        overcompression_flags.append("candidate-much-shorter-than-gold")
    overcompression_flags = sorted(set(overcompression_flags))

    alignment_score = 100
    alignment_score -= 25 * (len(missing_preservation) + len(negated_preservation))
    alignment_score -= 20 * unsafe_regression_count
    alignment_score -= 15 * len(overcompression_flags)
    alignment_score -= 10 * len(unresolved_expected_issues)
    alignment_score -= 5 * len(extra_candidate_findings_vs_gold)
    if int(source_candidate["deltas"]["score_delta"]) < 0:
        alignment_score -= 20
    if int(source_candidate["deltas"]["critical_high_finding_delta"]) > 0:
        alignment_score -= 20
    alignment_score = max(0, min(100, alignment_score))

    if unsafe_regression_count:
        verdict = "unsafe_regression"
    elif missing_preservation or negated_preservation or missing_gold_preservation:
        verdict = "missing_required_preservation"
    elif overcompression_flags:
        verdict = "overcompressed"
    elif source_candidate["verdict"] == "regression" or int(source_candidate["deltas"]["score_delta"]) < 0:
        verdict = "not_improved"
    elif alignment_score >= 90 and not unresolved_expected_issues and candidate_critical_high <= source_critical_high:
        verdict = "gold_aligned"
    elif alignment_score >= 70:
        verdict = "partially_aligned"
    else:
        verdict = "not_improved"

    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "evaluation_type": "gold_candidate",
        "scenario_id": str(expected.get("scenario_id") or scenario_dir.name),
        "scenario_dir": str(scenario_dir),
        "project_mode": project_mode,
        "source_path": str(source.resolve()),
        "candidate_path": str(candidate_path),
        "gold_path": str(gold_path),
        "verdict": verdict,
        "gold_alignment_score": alignment_score,
        "primary_scenario": classification["primary_scenario"],
        "expected_primary_scenario": expected.get("expected_primary_scenario"),
        "gold_primary_scenario": expected.get("gold_primary_scenario"),
        "selected_template": classification["selected_template"]["reference_path"],
        "missing_gold_preservation": missing_preservation,
        "negated_gold_preservation": negated_preservation,
        "gold_reference_missing_preservation": missing_gold_preservation,
        "unresolved_expected_issue_ids": unresolved_expected_issues,
        "extra_candidate_findings_vs_gold": extra_candidate_findings_vs_gold,
        "overcompression_flags": overcompression_flags,
        "unsafe_regression_count": unsafe_regression_count,
        "critical_high_introduced_count": max(0, candidate_critical_high - source_critical_high),
        "source_candidate": {
            "verdict": source_candidate["verdict"],
            "score_delta": source_candidate["deltas"]["score_delta"],
            "token_delta": source_candidate["deltas"]["token_delta"],
            "critical_high_finding_delta": source_candidate["deltas"]["critical_high_finding_delta"],
            "regression_flags": source_candidate["regression_flags"],
        },
        "source_gold": {
            "verdict": source_gold["verdict"],
            "score_delta": source_gold["deltas"]["score_delta"],
            "token_delta": source_gold["deltas"]["token_delta"],
            "critical_high_finding_delta": source_gold["deltas"]["critical_high_finding_delta"],
            "regression_flags": source_gold["regression_flags"],
        },
        "gold_candidate": {
            "verdict": gold_candidate["verdict"],
            "score_delta": gold_candidate["deltas"]["score_delta"],
            "token_delta": gold_candidate["deltas"]["token_delta"],
            "critical_high_finding_delta": gold_candidate["deltas"]["critical_high_finding_delta"],
            "regression_flags": gold_candidate["regression_flags"],
        },
    }


def render_gold_evaluation_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ContextProof Gold Evaluation",
        "",
        f"Scenario: `{report['scenario_id']}`",
        f"Verdict: `{report['verdict']}`",
        f"Gold alignment score: {report['gold_alignment_score']} / 100",
        f"Source: `{report['source_path']}`",
        f"Candidate: `{report['candidate_path']}`",
        f"Gold: `{report['gold_path']}`",
        f"Selected template: `{report['selected_template']}`",
        "",
        "## Source vs Candidate",
        "",
        f"- Verdict: `{report['source_candidate']['verdict']}`",
        f"- Score delta: {report['source_candidate']['score_delta']:+d}",
        f"- Token delta: {report['source_candidate']['token_delta']:+d}",
        f"- Critical/high finding delta: {report['source_candidate']['critical_high_finding_delta']:+d}",
        "",
        "## Gold Checks",
        "",
        f"- Missing preservation count: {len(report['missing_gold_preservation'])}",
        f"- Negated preservation count: {len(report.get('negated_gold_preservation', []))}",
        f"- Unsafe regression count: {report['unsafe_regression_count']}",
        f"- Critical/high introduced findings: {report['critical_high_introduced_count']}",
        f"- Overcompression flags: {len(report['overcompression_flags'])}",
        "",
    ]
    if report["missing_gold_preservation"]:
        lines.append("Missing required preservation:")
        for item in report["missing_gold_preservation"]:
            lines.append(f"- `{item}`")
        lines.append("")
    if report.get("negated_gold_preservation"):
        lines.append("Negated required preservation:")
        for item in report["negated_gold_preservation"]:
            lines.append(f"- `{item}`")
        lines.append("")
    if report["unresolved_expected_issue_ids"]:
        lines.append("Unresolved expected issue ids:")
        for item in report["unresolved_expected_issue_ids"]:
            lines.append(f"- `{item}`")
        lines.append("")
    if report["extra_candidate_findings_vs_gold"]:
        lines.append("Extra candidate findings compared with gold:")
        for item in report["extra_candidate_findings_vs_gold"]:
            lines.append(f"- `{item}`")
        lines.append("")
    if report["overcompression_flags"]:
        lines.append("Overcompression flags:")
        for item in report["overcompression_flags"]:
            lines.append(f"- `{item}`")
        lines.append("")
    return "\n".join(lines)


def score_bucket(score: int) -> str:
    if score >= 90:
        return "lean_actionable"
    if score >= 75:
        return "usable_cleanup_needed"
    if score >= 60:
        return "risky_context"
    return "blocked_context"


def load_calibration_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise ContextProofInputError(f"Calibration JSONL does not exist: {path}")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ContextProofInputError(f"Invalid calibration JSON on line {index}: {exc}") from exc
        if not isinstance(row, dict):
            raise ContextProofInputError(f"Calibration row {index} must be an object.")
        rows.append(row)
    if not rows:
        raise ContextProofInputError(f"Calibration JSONL has no cases: {path}")
    return rows


def audit_calibration_case(row: dict[str, Any], base_dir: Path, deterministic: bool) -> dict[str, Any]:
    project_mode = normalize_project_mode(str(row.get("project_mode") or "existing_project"))
    if row.get("fixture_path"):
        target = (base_dir / str(row["fixture_path"])).resolve()
        return audit_context_input(target, deterministic=deterministic, project_mode=project_mode)
    if row.get("context") is not None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text(str(row["context"]), encoding="utf-8")
            return audit_context_input(path, deterministic=deterministic, project_mode=project_mode)
    raise ContextProofInputError(f"Calibration case {row.get('case_id', '<unknown>')} must provide fixture_path or context.")


def calibrate_scorer(path: Path, deterministic: bool = False) -> dict[str, Any]:
    path = path.resolve()
    rows = load_calibration_cases(path)
    cases: list[dict[str, Any]] = []
    total_expected = 0
    total_missing = 0
    total_unexpected = 0
    severity_checked = 0
    severity_mismatches = 0
    dimension_checked = 0
    dimension_mismatches = 0
    score_bucket_checked = 0
    score_bucket_mismatches = 0

    for row in rows:
        report = audit_calibration_case(row, path.parent, deterministic)
        findings = report.get("findings", [])
        findings_by_id: dict[str, list[dict[str, Any]]] = {}
        for finding in findings:
            findings_by_id.setdefault(str(finding.get("id")), []).append(finding)
        actual_issue_ids = set(findings_by_id)
        expected_issue_ids = {str(item) for item in row.get("expected_issue_ids", [])}
        total_expected += len(expected_issue_ids)
        missing = sorted(expected_issue_ids - actual_issue_ids)
        unexpected = sorted(actual_issue_ids - expected_issue_ids)
        total_missing += len(missing)
        total_unexpected += len(unexpected)

        expected_severity = {str(key): str(value) for key, value in dict(row.get("expected_severity", {})).items()}
        severity_mismatch_items: list[dict[str, str]] = []
        for issue_id, severity in expected_severity.items():
            if issue_id not in findings_by_id:
                continue
            severity_checked += 1
            actual_severities = {str(item.get("severity")) for item in findings_by_id[issue_id]}
            if severity not in actual_severities:
                severity_mismatches += 1
                severity_mismatch_items.append(
                    {
                        "issue_id": issue_id,
                        "expected": severity,
                        "actual": ", ".join(sorted(actual_severities)),
                    }
                )

        expected_dimension = {str(key): str(value) for key, value in dict(row.get("expected_dimension", {})).items()}
        dimension_mismatch_items: list[dict[str, str]] = []
        for issue_id, dimension in expected_dimension.items():
            if issue_id not in findings_by_id:
                continue
            dimension_checked += 1
            actual_dimensions = {str(item.get("category")) for item in findings_by_id[issue_id]}
            if dimension not in actual_dimensions:
                dimension_mismatches += 1
                dimension_mismatch_items.append(
                    {
                        "issue_id": issue_id,
                        "expected": dimension,
                        "actual": ", ".join(sorted(actual_dimensions)),
                    }
                )

        total_score = int(report["static_context_score"]["total"])
        actual_bucket = score_bucket(total_score)
        expected_bucket = str(row.get("expected_score_bucket") or "")
        score_bucket_match = None
        if expected_bucket:
            score_bucket_checked += 1
            score_bucket_match = expected_bucket == actual_bucket
            if not score_bucket_match:
                score_bucket_mismatches += 1

        cases.append(
            {
                "case_id": str(row.get("case_id") or len(cases) + 1),
                "rationale": str(row.get("rationale") or ""),
                "score": total_score,
                "expected_score_bucket": expected_bucket or None,
                "actual_score_bucket": actual_bucket,
                "score_bucket_match": score_bucket_match,
                "expected_issue_ids": sorted(expected_issue_ids),
                "actual_issue_ids": sorted(actual_issue_ids),
                "missing_expected_issue_ids": missing,
                "unexpected_issue_ids": unexpected,
                "severity_mismatches": severity_mismatch_items,
                "dimension_mismatches": dimension_mismatch_items,
            }
        )

    missing_rate = total_missing / total_expected if total_expected else 0.0
    unexpected_rate = total_unexpected / total_expected if total_expected else 0.0
    severity_mismatch_rate = severity_mismatches / severity_checked if severity_checked else 0.0
    dimension_mismatch_rate = dimension_mismatches / dimension_checked if dimension_checked else 0.0
    score_bucket_mismatch_rate = score_bucket_mismatches / score_bucket_checked if score_bucket_checked else 0.0
    generated_at = "1970-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "calibration_type": "scorer",
        "source_path": str(path),
        "case_count": len(cases),
        "summary": {
            "missing_expected_issue_rate": missing_rate,
            "unexpected_issue_rate": unexpected_rate,
            "severity_mismatch_rate": severity_mismatch_rate,
            "dimension_mismatch_rate": dimension_mismatch_rate,
            "score_bucket_mismatch_rate": score_bucket_mismatch_rate,
            "total_expected_issue_count": total_expected,
            "missing_expected_issue_count": total_missing,
            "unexpected_issue_count": total_unexpected,
            "severity_checked_count": severity_checked,
            "severity_mismatch_count": severity_mismatches,
            "dimension_checked_count": dimension_checked,
            "dimension_mismatch_count": dimension_mismatches,
            "score_bucket_checked_count": score_bucket_checked,
            "score_bucket_mismatch_count": score_bucket_mismatches,
        },
        "cases": cases,
    }


def render_calibration_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# ContextProof Scorer Calibration",
        "",
        f"Cases: {report['case_count']}",
        f"Missing expected issue rate: {summary['missing_expected_issue_rate']:.2%}",
        f"Unexpected issue rate: {summary['unexpected_issue_rate']:.2%}",
        f"Severity mismatch rate: {summary['severity_mismatch_rate']:.2%}",
        f"Dimension mismatch rate: {summary['dimension_mismatch_rate']:.2%}",
        f"Score bucket mismatch rate: {summary['score_bucket_mismatch_rate']:.2%}",
        "",
        "## Failed Cases",
        "",
    ]
    failed_cases = [
        case
        for case in report["cases"]
        if case["missing_expected_issue_ids"]
        or case["unexpected_issue_ids"]
        or case["severity_mismatches"]
        or case["dimension_mismatches"]
        or case["score_bucket_match"] is False
    ]
    if failed_cases:
        for case in failed_cases:
            reasons = []
            if case["missing_expected_issue_ids"]:
                reasons.append("missing expected issues")
            if case["unexpected_issue_ids"]:
                reasons.append("unexpected issues")
            if case["severity_mismatches"]:
                reasons.append("severity mismatch")
            if case["dimension_mismatches"]:
                reasons.append("dimension mismatch")
            if case["score_bucket_match"] is False:
                reasons.append("score bucket mismatch")
            lines.append(f"- `{case['case_id']}`: {', '.join(reasons)}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Cases",
            "",
        ]
    )
    for case in report["cases"]:
        lines.append(f"### {case['case_id']}")
        lines.append("")
        lines.append(f"- Score: {case['score']} / 100")
        lines.append(f"- Score bucket: `{case['actual_score_bucket']}`")
        if case["expected_score_bucket"]:
            lines.append(f"- Expected bucket: `{case['expected_score_bucket']}`")
            lines.append(f"- Bucket match: `{case['score_bucket_match']}`")
        if case["missing_expected_issue_ids"]:
            lines.append(f"- Missing expected issues: {', '.join(f'`{item}`' for item in case['missing_expected_issue_ids'])}")
        if case["unexpected_issue_ids"]:
            lines.append(f"- Unexpected issues: {', '.join(f'`{item}`' for item in case['unexpected_issue_ids'])}")
        if case["severity_mismatches"]:
            lines.append(f"- Severity mismatches: {len(case['severity_mismatches'])}")
        if case["dimension_mismatches"]:
            lines.append(f"- Dimension mismatches: {len(case['dimension_mismatches'])}")
        if not (
            case["missing_expected_issue_ids"]
            or case["unexpected_issue_ids"]
            or case["severity_mismatches"]
            or case["dimension_mismatches"]
            or case["score_bucket_match"] is False
        ):
            lines.append("- Calibration checks passed.")
        lines.append("")
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
        classification = classify_context_scenario(source, deterministic=deterministic, project_mode=project_mode)
        expected_primary_scenario = str(expected.get("expected_primary_scenario") or "")
        classification_match = (
            None
            if not expected_primary_scenario
            else classification["primary_scenario"] == expected_primary_scenario
        )
        for candidate in discover_candidate_inputs(scenario_dir):
            comparison = compare_contexts(source, candidate, deterministic=deterministic, project_mode=project_mode)
            gold_evaluation: dict[str, Any] | None = None
            gold_path = resolve_gold_path(scenario_dir, expected)
            if gold_path.exists():
                gold_evaluation = evaluate_gold_candidate(scenario_dir, candidate, deterministic=deterministic)
            candidate_text = context_input_text(candidate)
            missing_preservation = [item for item in preserve if item not in candidate_text]
            variant = infer_prompt_variant(candidate, scenario_dir, prompt_variant)
            regression_flags = list(comparison["regression_flags"])
            if missing_preservation:
                regression_flags.append("missing-expected-preservation")
            if gold_evaluation and gold_evaluation["verdict"] in {"unsafe_regression", "missing_required_preservation"}:
                regression_flags.append(gold_evaluation["verdict"])
            score_delta = int(comparison["deltas"]["score_delta"])
            token_delta = int(comparison["deltas"]["token_delta"])
            critical_high_delta = int(comparison["deltas"]["critical_high_finding_delta"])
            candidate_tokens = int(comparison["candidate"]["total_context_tokens"])
            source_tokens = int(comparison["source"]["total_context_tokens"])
            gold_tokens = (
                source_tokens + int(gold_evaluation["source_gold"]["token_delta"])
                if gold_evaluation
                else source_tokens
            )
            gold_allows_token_growth = bool(
                gold_evaluation
                and token_delta > 0
                and int(gold_evaluation["source_gold"]["token_delta"]) > 0
                and gold_evaluation["verdict"] in {"gold_aligned", "partially_aligned"}
                and candidate_tokens <= math.ceil(gold_tokens * 1.10)
            )
            success = (
                comparison["verdict"] == "improved"
                and score_delta >= 0
                and (token_delta <= 0 or gold_allows_token_growth)
                and critical_high_delta <= 0
                and not regression_flags
                and (
                    not gold_evaluation
                    or gold_evaluation["verdict"] in {"gold_aligned", "partially_aligned"}
                )
            )
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "generated_at": generated_at,
                    "run_id": f"{scenario_id}:{variant}:{candidate.name}",
                    "scenario_id": scenario_id,
                    "classified_primary_scenario": classification["primary_scenario"],
                    "classified_secondary_scenarios": classification["secondary_scenarios"],
                    "selected_template": classification["selected_template"]["reference_path"],
                    "classification_confidence": classification["confidence"],
                    "classification_match": classification_match,
                    "prompt_variant": variant,
                    "project_mode": project_mode,
                    "source_path": str(source.resolve()),
                    "candidate_path": str(candidate.resolve()),
                    "verdict": comparison["verdict"],
                    "success": success,
                    "score_delta": score_delta,
                    "token_delta": token_delta,
                    "gold_token_growth_allowed": gold_allows_token_growth,
                    "critical_high_finding_delta": critical_high_delta,
                    "resolved_finding_count": comparison["deltas"]["resolved_finding_count"],
                    "introduced_finding_count": comparison["deltas"]["introduced_finding_count"],
                    "source_score": comparison["source"]["score"],
                    "candidate_score": comparison["candidate"]["score"],
                    "source_tokens": comparison["source"]["total_context_tokens"],
                    "candidate_tokens": comparison["candidate"]["total_context_tokens"],
                    "regression_flags": regression_flags,
                    "removed_validation_commands": comparison["preservation"]["removed_validation_commands"],
                    "negated_validation_commands": comparison["preservation"].get("negated_validation_commands", []),
                    "missing_expected_preservation": missing_preservation,
                    "gold_path": str(gold_path) if gold_path.exists() else None,
                    "gold_alignment_verdict": gold_evaluation["verdict"] if gold_evaluation else None,
                    "gold_alignment_score": gold_evaluation["gold_alignment_score"] if gold_evaluation else None,
                    "missing_gold_preservation": gold_evaluation["missing_gold_preservation"] if gold_evaluation else [],
                    "negated_gold_preservation": gold_evaluation["negated_gold_preservation"] if gold_evaluation else [],
                    "extra_candidate_findings_vs_gold": gold_evaluation["extra_candidate_findings_vs_gold"] if gold_evaluation else [],
                    "overcompression_flags": gold_evaluation["overcompression_flags"] if gold_evaluation else [],
                    "unsafe_regression_count": gold_evaluation["unsafe_regression_count"] if gold_evaluation else 0,
                }
            )
    return rows


def gold_alignment_rate(rows: list[dict[str, Any]]) -> float | None:
    gold_rows = [row for row in rows if row.get("gold_alignment_verdict")]
    if not gold_rows:
        return None
    aligned = [
        1.0 if row.get("gold_alignment_verdict") in {"gold_aligned", "partially_aligned"} else 0.0
        for row in gold_rows
    ]
    return mean_or_none(aligned)


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
            "gold_alignment_rate": gold_alignment_rate(items),
            "avg_score_delta": mean_or_none(score_deltas),
            "avg_token_delta": mean_or_none(token_deltas),
            "avg_critical_high_finding_delta": mean_or_none(critical_deltas),
            "regression_count": sum(1 for item in items if item.get("regression_flags")),
            "unsafe_regression_count": sum(int(item.get("unsafe_regression_count") or 0) for item in items),
            "overcompression_count": sum(1 for item in items if item.get("overcompression_flags")),
            "missing_preservation_count": sum(1 for item in items if item.get("missing_gold_preservation")),
        }
    scenario_routes: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        scenario_routes.setdefault(str(row["classified_primary_scenario"]), []).append(row)
    scenario_summaries: dict[str, dict[str, Any]] = {}
    for scenario_id, items in sorted(scenario_routes.items()):
        successes = [1.0 if item.get("success") else 0.0 for item in items]
        matches = [item.get("classification_match") for item in items if item.get("classification_match") is not None]
        scenario_summaries[scenario_id] = {
            "runs": len(items),
            "success_rate": mean_or_none(successes) or 0.0,
            "gold_alignment_rate": gold_alignment_rate(items),
            "classification_match_rate": mean_or_none([1.0 if item else 0.0 for item in matches]) if matches else None,
            "templates": sorted({str(item["selected_template"]) for item in items}),
            "regression_count": sum(1 for item in items if item.get("regression_flags")),
            "unsafe_regression_count": sum(int(item.get("unsafe_regression_count") or 0) for item in items),
            "overcompression_count": sum(1 for item in items if item.get("overcompression_flags")),
            "missing_preservation_count": sum(1 for item in items if item.get("missing_gold_preservation")),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_type": "context_optimizer",
        "default_prompt_variant": prompt_variant,
        "run_count": len(rows),
        "scenario_count": len({str(row["scenario_id"]) for row in rows}),
        "gold_alignment_rate": gold_alignment_rate(rows),
        "unsafe_regression_count": sum(int(item.get("unsafe_regression_count") or 0) for item in rows),
        "overcompression_count": sum(1 for item in rows if item.get("overcompression_flags")),
        "missing_preservation_count": sum(1 for item in rows if item.get("missing_gold_preservation")),
        "variants": variant_summaries,
        "scenario_routes": scenario_summaries,
    }


def render_optimizer_benchmark_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# ContextProof Optimizer Benchmark",
        "",
        f"Runs: {summary['run_count']}",
        f"Scenarios: {summary['scenario_count']}",
        f"Gold alignment rate: {summary['gold_alignment_rate']:.2%}" if summary["gold_alignment_rate"] is not None else "Gold alignment rate: n/a",
        f"Unsafe regressions: {summary['unsafe_regression_count']}",
        f"Overcompression count: {summary['overcompression_count']}",
        f"Missing preservation count: {summary['missing_preservation_count']}",
        "",
        "## Variants",
        "",
    ]
    for variant, item in summary["variants"].items():
        lines.append(f"### {variant}")
        lines.append("")
        lines.append(f"- Runs: {item['runs']}")
        lines.append(f"- Success rate: {item['success_rate']:.2%}")
        if item["gold_alignment_rate"] is not None:
            lines.append(f"- Gold alignment rate: {item['gold_alignment_rate']:.2%}")
        if item["avg_score_delta"] is not None:
            lines.append(f"- Avg score delta: {item['avg_score_delta']:+.1f}")
        if item["avg_token_delta"] is not None:
            lines.append(f"- Avg token delta: {item['avg_token_delta']:+.1f}")
        if item["avg_critical_high_finding_delta"] is not None:
            lines.append(f"- Avg critical/high finding delta: {item['avg_critical_high_finding_delta']:+.1f}")
        lines.append(f"- Regression count: {item['regression_count']}")
        lines.append(f"- Unsafe regressions: {item['unsafe_regression_count']}")
        lines.append(f"- Overcompression count: {item['overcompression_count']}")
        lines.append(f"- Missing preservation count: {item['missing_preservation_count']}")
        lines.append("")
    lines.extend(["## Scenario Routes", ""])
    if summary["scenario_routes"]:
        for scenario_id, item in summary["scenario_routes"].items():
            lines.append(f"### {scenario_id}")
            lines.append("")
            lines.append(f"- Runs: {item['runs']}")
            lines.append(f"- Success rate: {item['success_rate']:.2%}")
            if item["gold_alignment_rate"] is not None:
                lines.append(f"- Gold alignment rate: {item['gold_alignment_rate']:.2%}")
            if item["classification_match_rate"] is not None:
                lines.append(f"- Classification match rate: {item['classification_match_rate']:.2%}")
            lines.append(f"- Templates: {', '.join(f'`{template}`' for template in item['templates'])}")
            lines.append(f"- Regression count: {item['regression_count']}")
            lines.append(f"- Unsafe regressions: {item['unsafe_regression_count']}")
            lines.append(f"- Overcompression count: {item['overcompression_count']}")
            lines.append(f"- Missing preservation count: {item['missing_preservation_count']}")
            lines.append("")
    else:
        lines.append("- No scenario route data.")
        lines.append("")
    lines.extend(["## Runs", ""])
    if not rows:
        lines.append("- No candidate runs found.")
    for row in rows:
        lines.append(f"### {row['scenario_id']} / {row['prompt_variant']}")
        lines.append("")
        lines.append(f"- Classified scenario: `{row['classified_primary_scenario']}`")
        lines.append(f"- Template: `{row['selected_template']}`")
        if row["classification_match"] is not None:
            lines.append(f"- Classification match: `{row['classification_match']}`")
        if row.get("gold_alignment_verdict"):
            lines.append(f"- Gold verdict: `{row['gold_alignment_verdict']}`")
            lines.append(f"- Gold alignment score: {row['gold_alignment_score']}")
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
        target = Path(args.output)
        if not target.is_absolute():
            target = Path.cwd() / target
        target = target.resolve()
        output_root = root / ".contextproof"
        if not is_under_path(target, output_root):
            raise ContextProofInputError(
                "minimize --output must write under the target repository's .contextproof/ directory. "
                "Use .contextproof/context.min.md or run without --output to print to stdout."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(candidate, encoding="utf-8")
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
    output_dir = Path(args.output_dir) if args.output_dir else context_output_dir(source.resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = Path(args.json_out) if args.json_out else output_dir / "candidate-report.json"
    md_out = Path(args.md_out) if args.md_out else output_dir / "candidate-report.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_candidate_report(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def command_discover_context(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    report = discover_context_report(
        root,
        deterministic=args.deterministic,
        project_mode=args.project_mode,
    )
    output_dir = Path(args.output_dir) if args.output_dir else root / ".contextproof"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = Path(args.json_out) if args.json_out else output_dir / "context-discovery.json"
    md_out = Path(args.md_out) if args.md_out else output_dir / "context-discovery.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_context_discovery_markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def command_prepare_workflow(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else root / ".contextproof"
    workflow = build_workflow_packet(
        root,
        deterministic=args.deterministic,
        project_mode=args.project_mode,
        output_dir=output_dir,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    discovery = discover_context_report(root, deterministic=args.deterministic, project_mode=args.project_mode)
    audit = audit_repo(root, deterministic=args.deterministic, project_mode=args.project_mode)
    source = Path(workflow["source_path"])
    route = build_optimizer_route(source, deterministic=args.deterministic, project_mode=args.project_mode)
    classification = route["classification"]

    (output_dir / "context-discovery.json").write_text(json.dumps(discovery, indent=2) + "\n", encoding="utf-8")
    (output_dir / "context-discovery.md").write_text(render_context_discovery_markdown(discovery), encoding="utf-8")
    (output_dir / "report.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (output_dir / "report.md").write_text(render_markdown_report(audit), encoding="utf-8")
    (output_dir / "context-classification.json").write_text(json.dumps(classification, indent=2) + "\n", encoding="utf-8")
    (output_dir / "context-classification.md").write_text(render_classification_markdown(classification), encoding="utf-8")
    (output_dir / "optimizer-route.json").write_text(json.dumps(route, indent=2) + "\n", encoding="utf-8")
    (output_dir / "optimizer-instructions.md").write_text(render_optimizer_route_markdown(route), encoding="utf-8")

    json_out = Path(args.json_out) if args.json_out else output_dir / "workflow.json"
    md_out = Path(args.md_out) if args.md_out else output_dir / "workflow.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(workflow, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_workflow_markdown(workflow), encoding="utf-8")
    print(json.dumps(workflow, indent=2))
    return 0


def command_review_candidate(args: argparse.Namespace) -> int:
    source = Path(args.source)
    candidate = Path(args.candidate)
    if not source.exists():
        raise ContextProofInputError(f"Source context path does not exist: {source}")
    if not candidate.exists():
        raise ContextProofInputError(f"Candidate context path does not exist: {candidate}")
    comparison = compare_contexts(
        source,
        candidate,
        deterministic=args.deterministic,
        project_mode=args.project_mode,
    )
    review = build_candidate_review(comparison)
    output_dir = Path(args.output_dir) if args.output_dir else context_output_dir(source.resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = Path(args.json_out) if args.json_out else output_dir / "candidate-review.json"
    md_out = Path(args.md_out) if args.md_out else output_dir / "candidate-review.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_candidate_review_markdown(review), encoding="utf-8")
    (output_dir / "candidate-report.json").write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    (output_dir / "candidate-report.md").write_text(render_candidate_report(comparison), encoding="utf-8")
    print(json.dumps(review, indent=2))
    return 0


def command_classify_context(args: argparse.Namespace) -> int:
    source = Path(args.source)
    if not source.exists():
        raise ContextProofInputError(f"Context path does not exist: {source}")
    classification = classify_context_scenario(
        source,
        deterministic=args.deterministic,
        project_mode=args.project_mode,
    )
    output_dir = Path(args.output_dir) if args.output_dir else context_output_dir(source.resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = Path(args.json_out) if args.json_out else output_dir / "context-classification.json"
    md_out = Path(args.md_out) if args.md_out else output_dir / "context-classification.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(classification, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_classification_markdown(classification), encoding="utf-8")
    print(json.dumps(classification, indent=2))
    return 0


def command_route_optimizer(args: argparse.Namespace) -> int:
    source = Path(args.source)
    if not source.exists():
        raise ContextProofInputError(f"Context path does not exist: {source}")
    route = build_optimizer_route(
        source,
        deterministic=args.deterministic,
        project_mode=args.project_mode,
    )
    output_dir = Path(args.output_dir) if args.output_dir else context_output_dir(source.resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = Path(args.json_out) if args.json_out else output_dir / "optimizer-route.json"
    md_out = Path(args.md_out) if args.md_out else output_dir / "optimizer-instructions.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(route, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_optimizer_route_markdown(route), encoding="utf-8")
    print(json.dumps(route, indent=2))
    return 0


def command_evaluate_gold(args: argparse.Namespace) -> int:
    scenario = Path(args.scenario)
    candidate = Path(args.candidate)
    if not scenario.exists() or not scenario.is_dir():
        raise ContextProofInputError(f"Scenario directory does not exist: {scenario}")
    if not candidate.exists():
        raise ContextProofInputError(f"Candidate path does not exist: {candidate}")
    report = evaluate_gold_candidate(
        scenario,
        candidate,
        deterministic=args.deterministic,
    )
    output_dir = Path(args.output_dir) if args.output_dir else context_output_dir(scenario.resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = Path(args.json_out) if args.json_out else output_dir / "gold-evaluation.json"
    md_out = Path(args.md_out) if args.md_out else output_dir / "gold-evaluation.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_gold_evaluation_markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def command_calibrate_scorer(args: argparse.Namespace) -> int:
    cases = Path(args.cases)
    if not cases.exists():
        raise ContextProofInputError(f"Calibration cases file does not exist: {cases}")
    report = calibrate_scorer(cases, deterministic=args.deterministic)
    output_dir = Path(args.output_dir) if args.output_dir else context_output_dir(cases.resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    json_out = Path(args.json_out) if args.json_out else output_dir / "scorer-calibration.json"
    md_out = Path(args.md_out) if args.md_out else output_dir / "scorer-calibration.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_calibration_markdown(report), encoding="utf-8")
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
    minimize.add_argument("--output", help="Write candidate under .contextproof/. Defaults to stdout.")
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

    discover = subparsers.add_parser("discover-context", help="Discover agent-facing context files in a repository.")
    discover.add_argument("repo", nargs="?", default=".", help="Repository path.")
    discover.add_argument("--json-out", help="Write JSON discovery report to this path.")
    discover.add_argument("--md-out", help="Write markdown discovery report to this path.")
    discover.add_argument("--output-dir", help="Write default discovery outputs to this directory.")
    discover.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    discover.add_argument(
        "--project-mode",
        choices=["existing_project", "new_project", "migration_project", "existing_project_audit", "new_project_bootstrap"],
        default="existing_project",
        help="Declare whether this is an existing, new, or migration project context.",
    )
    discover.set_defaults(func=command_discover_context)

    workflow = subparsers.add_parser("prepare-workflow", help="Prepare the one-prompt ContextProof optimization workflow packet.")
    workflow.add_argument("repo", nargs="?", default=".", help="Repository path.")
    workflow.add_argument("--json-out", help="Write JSON workflow report to this path.")
    workflow.add_argument("--md-out", help="Write markdown workflow packet to this path.")
    workflow.add_argument("--output-dir", help="Write default workflow outputs to this directory.")
    workflow.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    workflow.add_argument(
        "--project-mode",
        choices=["existing_project", "new_project", "migration_project", "existing_project_audit", "new_project_bootstrap"],
        default="existing_project",
        help="Declare whether this is an existing, new, or migration project context.",
    )
    workflow.set_defaults(func=command_prepare_workflow)

    review = subparsers.add_parser("review-candidate", help="Review whether a candidate agent context is safe to consider.")
    review.add_argument("source", help="Original context file or repository directory.")
    review.add_argument("candidate", help="Candidate context file or repository directory.")
    review.add_argument("--json-out", help="Write JSON candidate review to this path.")
    review.add_argument("--md-out", help="Write markdown candidate review to this path.")
    review.add_argument("--output-dir", help="Write default candidate review outputs to this directory.")
    review.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    review.add_argument(
        "--project-mode",
        choices=["existing_project", "new_project", "migration_project", "existing_project_audit", "new_project_bootstrap"],
        default="existing_project",
        help="Declare whether this is an existing, new, or migration project context.",
    )
    review.set_defaults(func=command_review_candidate)

    classify = subparsers.add_parser("classify-context", help="Classify agent-context scenario and optimizer template.")
    classify.add_argument("source", help="Agent context file or repository directory.")
    classify.add_argument("--json-out", help="Write JSON classification report to this path.")
    classify.add_argument("--md-out", help="Write markdown classification report to this path.")
    classify.add_argument("--output-dir", help="Write default classification outputs to this directory.")
    classify.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    classify.add_argument(
        "--project-mode",
        choices=["existing_project", "new_project", "migration_project", "existing_project_audit", "new_project_bootstrap"],
        default="existing_project",
        help="Declare whether this is an existing, new, or migration project context.",
    )
    classify.set_defaults(func=command_classify_context)

    route = subparsers.add_parser("route-optimizer", help="Render scenario-specific optimizer instructions.")
    route.add_argument("source", help="Agent context file or repository directory.")
    route.add_argument("--json-out", help="Write JSON optimizer route to this path.")
    route.add_argument("--md-out", help="Write markdown optimizer instructions to this path.")
    route.add_argument("--output-dir", help="Write default optimizer route outputs to this directory.")
    route.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    route.add_argument(
        "--project-mode",
        choices=["existing_project", "new_project", "migration_project", "existing_project_audit", "new_project_bootstrap"],
        default="existing_project",
        help="Declare whether this is an existing, new, or migration project context.",
    )
    route.set_defaults(func=command_route_optimizer)

    gold = subparsers.add_parser("evaluate-gold", help="Compare a scenario candidate against the gold reference.")
    gold.add_argument("scenario", help="Scenario directory containing source/, expected.json, and gold/.")
    gold.add_argument("candidate", help="Candidate context file or directory to evaluate.")
    gold.add_argument("--json-out", help="Write JSON gold evaluation to this path.")
    gold.add_argument("--md-out", help="Write markdown gold evaluation to this path.")
    gold.add_argument("--output-dir", help="Write default gold evaluation outputs to this directory.")
    gold.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    gold.set_defaults(func=command_evaluate_gold)

    calibration = subparsers.add_parser("calibrate-scorer", help="Run deterministic scorer calibration cases.")
    calibration.add_argument("cases", help="Calibration JSONL file.")
    calibration.add_argument("--json-out", help="Write scorer calibration JSON to this path.")
    calibration.add_argument("--md-out", help="Write scorer calibration markdown to this path.")
    calibration.add_argument("--output-dir", help="Write default scorer calibration outputs to this directory.")
    calibration.add_argument("--deterministic", action="store_true", help="Normalize volatile metadata for snapshots.")
    calibration.set_defaults(func=command_calibrate_scorer)

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
