#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_JUNK_PATHS = [
    ".codex-tmp-pyc",
    "test_cam.py",
    "bug.png",
    "bug.txt",
    "session.txt",
    "b2.png",
    "b3.png",
    "b4.jpg",
    "Use_case_restaurant_model.svg",
]

SOURCE_DIRS = [
    "accounts",
    "ai_engine",
    "api",
    "document_templates",
    "documents",
    "flutter_frontend/lib",
    "my_tennis_club",
    "prompts",
    "signing",
]

SOURCE_FILES = [
    "manage.py",
]

PATTERNS = {
    "legacy_runtime_tokens": re.compile(r"\blegacy\b|_unused_|passthrough|social-auth|social_django"),
    "legacy_view_imports": re.compile(r"\b(documents|document_templates|accounts)\.views\b"),
}

SKIP_DIRS = {".git", "__pycache__", ".dart_tool", "build", "migrations", "media"}
SCAN_SUFFIXES = {".py", ".dart"}


def should_scan(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.suffix.lower() in SCAN_SUFFIXES


def iter_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel_dir in SOURCE_DIRS:
        base_dir = root / rel_dir
        if not base_dir.exists():
            continue
        for file_path in base_dir.rglob("*"):
            if file_path.is_file() and should_scan(file_path):
                files.append(file_path)
    for rel_file in SOURCE_FILES:
        file_path = root / rel_file
        if file_path.is_file() and should_scan(file_path):
            files.append(file_path)
    return files


def scan_files(root: Path) -> list[str]:
    findings: list[str] = []
    for file_path in iter_source_files(root):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            findings.append(f"[read-error] {file_path}: {exc}")
            continue
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                line_no = content.count("\n", 0, match.start()) + 1
                findings.append(f"[{label}] {file_path}:{line_no}: {match.group(0)}")
    return findings


def scan_junk_paths(root: Path) -> list[str]:
    findings: list[str] = []
    for rel_path in DEFAULT_JUNK_PATHS:
        path = root / rel_path
        if path.exists():
            findings.append(f"[junk-path] {path}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan this repository for common legacy cleanup leftovers.")
    parser.add_argument("path", nargs="?", default=".", help="Repository root to scan")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"Path does not exist: {root}")
        return 1

    findings = []
    findings.extend(scan_junk_paths(root))
    findings.extend(scan_files(root))

    if not findings:
        print("No legacy findings detected.")
        return 0

    for item in findings:
        print(item)
    print(f"\nTotal findings: {len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
