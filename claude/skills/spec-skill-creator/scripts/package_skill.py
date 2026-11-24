#!/usr/bin/env python3
"""Validate a skill and package it into <name>.skill (a zip archive).

Usage:
    package_skill.py <skill-dir> [-o OUTPUT_DIR] [--target spec|claude-code] [--strict]

Defaults to the 'spec' target because the usual reason to package is upload to
claude.ai or the Skills API, which reject any frontmatter field outside the spec.
Archive entries are rooted at the skill directory name, as uploaders expect.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import zipfile
from pathlib import Path

# Importing the sibling validator would otherwise drop __pycache__ into the skill.
sys.dont_write_bytecode = True

from quick_validate import validate_skill  # noqa: E402

EXCLUDED_NAMES = {".git", "__pycache__", ".DS_Store", "node_modules", ".gitkeep"}
# Dev artifacts, not part of the shipped skill.
EXCLUDED_ROOT_DIRS = {"evals"}
EXCLUDED_SUFFIXES = (".pyc", ".skill")


def _excluded(rel: Path) -> bool:
    if rel.parts[0] in EXCLUDED_ROOT_DIRS or rel.parts[0].endswith("-workspace"):
        return True
    return any(part in EXCLUDED_NAMES for part in rel.parts) or rel.name.endswith(EXCLUDED_SUFFIXES)


def collect_files(skill_dir: Path) -> list:
    files = []
    for dirpath, dirnames, filenames in os.walk(skill_dir):
        dirnames[:] = sorted(name for name in dirnames if name not in EXCLUDED_NAMES)
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            relative = path.relative_to(skill_dir)
            if _excluded(relative):
                continue
            if path.is_symlink():
                # A symlink could pull files from outside the skill into the archive.
                print(f"  Skipped symlink: {relative}")
                continue
            files.append(path)
    return files


def package_skill(skill_path: str, output_dir: str, target: str, strict: bool) -> Path:
    skill_dir = Path(skill_path).resolve()
    if not skill_dir.is_dir():
        raise NotADirectoryError(f"not a directory: {skill_dir}")

    errors, warnings = validate_skill(skill_dir, target)
    for warning in warnings:
        print(f"WARN:  {warning}")
    if errors or (strict and warnings):
        for error in errors:
            print(f"ERROR: {error}")
        raise ValueError("validation failed; fix the issues above before packaging")

    out_dir = Path(output_dir).resolve()
    if out_dir == skill_dir or skill_dir in out_dir.parents:
        raise ValueError("output directory must be outside the skill directory")
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{skill_dir.name}.skill"

    # Write to a temp file in the target dir so a failure never leaves a truncated archive.
    descriptor, partial_name = tempfile.mkstemp(suffix=".skill.tmp", dir=out_dir)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(partial_name, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in collect_files(skill_dir):
                entry_name = path.relative_to(skill_dir.parent)
                bundle.write(path, entry_name)
                print(f"  Added: {entry_name}")
        os.replace(partial_name, archive)
    except BaseException:
        Path(partial_name).unlink(missing_ok=True)
        raise
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("skill_dir")
    parser.add_argument("-o", "--output", default=".", help="output directory (default: cwd)")
    parser.add_argument("--target", choices=("spec", "claude-code"), default="spec")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()

    try:
        archive = package_skill(args.skill_dir, args.output, args.target, args.strict)
    except (ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"Packaged: {archive}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
