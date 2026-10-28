#!/usr/bin/env python3
"""Fail closed on common privacy and secret leaks before a repository push."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
PROHIBITED_TOP_LEVEL = {".lwc", ".codex", ".agents", "work", "audits", "output", "private", "imports", "intake"}
PROHIBITED_RELATIVE_PREFIXES = (
    "raw/templates/",
    "sources/template-deor-budget-user/",
    "sources/template-task-file-2024/",
    "sources/template-ka220-user/",
    "sources/templates-workbooks/",
)
PROHIBITED_NAMES = {
    "credentials.json", "auth.json", "tokens.json", "cookies.json", ".netrc", ".npmrc", ".pypirc"
}
TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".jsonl", ".toml", ".yaml", ".yml", ".py", ".sh", ".js", ".ts", ".html", ".css"
}

# These expressions target credentials and machine/user identifiers, not ordinary public citations.
DENY_PATTERNS = {
    "absolute-user-home": re.compile(r"(?:^|[\s\"'=])/(?:Users|home)/[^/\s]+/", re.M),
    "github-token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def files(root: Path):
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts or path.is_symlink() or not path.is_file():
            continue
        yield path


def check(root: Path) -> list[dict]:
    issues: list[dict] = []
    for name in sorted(PROHIBITED_TOP_LEVEL):
        if (root / name).exists():
            issues.append({"code": "prohibited-top-level-path", "path": name})

    for path in files(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith("projects/") and rel != "projects/README.md":
            issues.append({"code": "project-data-present", "path": rel})
        if any(rel.startswith(prefix) for prefix in PROHIBITED_RELATIVE_PREFIXES):
            issues.append({"code": "private-template-present", "path": rel})
        lower = path.name.lower()
        if lower in PROHIBITED_NAMES or lower.startswith(".env") or path.suffix.lower() in {".pem", ".key"}:
            issues.append({"code": "credential-file-name", "path": rel})
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"AGENTS.md", "README.md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            issues.append({"code": "invalid-text-encoding", "path": rel})
            continue
        for code, pattern in DENY_PATTERNS.items():
            match = pattern.search(text)
            if match:
                issues.append({"code": code, "path": rel, "line": text.count("\n", 0, match.start()) + 1})

    source_catalog = root / "config/sources.json"
    if source_catalog.exists():
        data = json.loads(source_catalog.read_text(encoding="utf-8"))
        for item in data:
            if item.get("kind") == "user-template" or item.get("id") in {
                "template-ka220-user", "template-task-file-2024", "template-deor-budget-user"
            }:
                issues.append({"code": "private-source-catalogue-entry", "source_id": item.get("id")})

    profile = root / "config/forms/ka220-user-template.json"
    if profile.exists():
        data = json.loads(profile.read_text(encoding="utf-8"))
        if "source" in data or not data.get("distribution_note"):
            issues.append({"code": "unsanitized-reference-form", "path": profile.relative_to(root).as_posix()})

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    issues = check(root)
    result = {"passed": not issues, "root": str(root), "issues": issues}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
