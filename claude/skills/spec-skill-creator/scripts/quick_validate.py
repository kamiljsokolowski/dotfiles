#!/usr/bin/env python3
"""Validate a skill directory against the Agent Skills spec.

Two targets, because the spec and Claude Code disagree on what a valid
frontmatter is:

  spec         the open-spec field set; also what claude.ai uploads and the
               Skills API accept. Anything else is a hard error there.
  claude-code  spec fields plus Claude Code extensions, which are not portable.

Usage:
    quick_validate.py <skill-dir> [--target spec|claude-code] [--strict]

Exit codes: 0 valid, 1 validation errors, 2 environment problem.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Importing the sibling lint module would otherwise drop __pycache__ into the skill.
sys.dont_write_bytecode = True

from best_practices import lint_best_practices  # noqa: E402

try:
    import yaml
except ImportError:
    print("PyYAML is required: python3 -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
CLAUDE_CODE_EXTENSIONS = {
    "when_to_use", "argument-hint", "arguments", "disable-model-invocation",
    "user-invocable", "disallowed-tools", "model", "effort", "context", "agent",
    "background", "hooks", "paths", "shell",
}
CLAUDE_CODE_FIELDS = SPEC_FIELDS | CLAUDE_CODE_EXTENSIONS

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024
# Listing truncation limit for description + when_to_use in Claude Code.
LISTING_MAX = 1536
COMPATIBILITY_MAX = 500
BODY_LINES_MAX = 500
EFFORT_VALUES = {"low", "medium", "high", "xhigh", "max"}
SHELL_VALUES = {"bash", "powershell"}
BOOLEAN_FIELDS = ("disable-model-invocation", "user-invocable", "background")
STRING_FIELDS = ("when_to_use", "argument-hint", "model")
STRING_OR_LIST_FIELDS = ("paths", "disallowed-tools", "arguments")

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
URI_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"\[TODO\b", re.IGNORECASE)
CODE_FENCE_RE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.MULTILINE | re.DOTALL)
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")

Findings = Tuple[List[str], List[str]]


def _strip_code(markdown: str) -> str:
    # Documentation about placeholders or links shows them in code; only
    # live prose should count.
    return CODE_SPAN_RE.sub("", CODE_FENCE_RE.sub("", markdown))


def split_frontmatter(text: str) -> Tuple[str, str]:
    lines = text.splitlines()
    # Claude Code treats the whole file as body unless '---' is on line 1.
    if not lines or lines[0].rstrip() != "---":
        raise ValueError("opening '---' must be on line 1")
    for index in range(1, len(lines)):
        if lines[index].rstrip() == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1:])
    raise ValueError("closing '---' not found")


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _local_link_target(link: str) -> Optional[str]:
    if URI_SCHEME_RE.match(link) or link.startswith("#"):
        return None
    return link.split("#", 1)[0] or None


def _check_name(frontmatter: Dict[str, Any], skill_dir: Path, target: str,
                errors: List[str], warnings: List[str]) -> None:
    if "name" not in frontmatter:
        if target == "spec":
            errors.append("missing required field 'name'")
        else:
            warnings.append("'name' omitted; Claude Code falls back to the "
                            "directory name (not spec-valid)")
        return
    name = frontmatter["name"]
    if not isinstance(name, str) or not name:
        errors.append("'name' must be a non-empty string")
        return
    if len(name) > NAME_MAX:
        errors.append(f"'name' is {len(name)} chars; max {NAME_MAX}")
    if not NAME_RE.match(name):
        errors.append(f"'name' {name!r} must be lowercase a-z/0-9 with single "
                      "hyphens, not starting or ending with '-'")
    if name != skill_dir.name:
        message = f"'name' {name!r} does not match directory name {skill_dir.name!r}"
        (errors if target == "spec" else warnings).append(message)


def _check_description(frontmatter: Dict[str, Any], target: str,
                       errors: List[str], warnings: List[str]) -> None:
    if "description" not in frontmatter:
        if target == "spec":
            errors.append("missing required field 'description'")
        else:
            warnings.append("'description' omitted; Claude Code uses the first "
                            "body line and triggering will be unreliable")
        return
    description = frontmatter["description"]
    if not isinstance(description, str) or not description.strip():
        errors.append("'description' must be a non-empty string")
        return
    if PLACEHOLDER_RE.search(description):
        errors.append("'description' still contains a [TODO] placeholder")
    if len(description) > DESCRIPTION_MAX:
        message = f"'description' is {len(description)} chars; spec max is {DESCRIPTION_MAX}"
        (errors if target == "spec" else warnings).append(message)
    if target == "claude-code":
        when_to_use = frontmatter.get("when_to_use", "")
        total = len(description) + (len(when_to_use) if isinstance(when_to_use, str) else 0)
        if total > LISTING_MAX:
            warnings.append(f"description + when_to_use is {total} chars; the "
                            f"skill listing truncates at {LISTING_MAX}")


def _check_metadata(metadata: Any, target: str,
                    errors: List[str], warnings: List[str]) -> None:
    if not isinstance(metadata, dict):
        errors.append("'metadata' must be a map of string to string")
        return
    for key, value in metadata.items():
        if not isinstance(key, str) or not isinstance(value, str):
            errors.append(f"'metadata' entry {key!r} must map a string to a "
                          "string (quote numbers and booleans)")
        elif target == "claude-code" and key in CLAUDE_CODE_FIELDS:
            warnings.append(f"'metadata' key {key!r} collides with a frontmatter field name")


def _check_allowed_tools(tools: Any, target: str,
                         errors: List[str], warnings: List[str]) -> None:
    if target == "spec":
        if not isinstance(tools, str):
            errors.append("'allowed-tools' must be a space-separated string in the spec")
        else:
            warnings.append("'allowed-tools' is experimental in the spec; "
                            "support varies by agent")
    elif not (isinstance(tools, str) or _is_string_list(tools)):
        errors.append("'allowed-tools' must be a string or a list of strings")


def _check_optional_spec_fields(frontmatter: Dict[str, Any], target: str,
                                errors: List[str], warnings: List[str]) -> None:
    license_value = frontmatter.get("license", "unset")
    if "license" in frontmatter and (not isinstance(license_value, str) or not license_value.strip()):
        errors.append("'license' must be a non-empty string")

    if "compatibility" in frontmatter:
        compatibility = frontmatter["compatibility"]
        if not isinstance(compatibility, str) or not compatibility.strip():
            errors.append("'compatibility' must be a non-empty string")
        elif len(compatibility) > COMPATIBILITY_MAX:
            errors.append(f"'compatibility' is {len(compatibility)} chars; "
                          f"max {COMPATIBILITY_MAX}")

    if "metadata" in frontmatter:
        _check_metadata(frontmatter["metadata"], target, errors, warnings)
    if "allowed-tools" in frontmatter:
        _check_allowed_tools(frontmatter["allowed-tools"], target, errors, warnings)


def _check_extensions(frontmatter: Dict[str, Any],
                      errors: List[str], warnings: List[str]) -> None:
    for key in BOOLEAN_FIELDS:
        if key in frontmatter and not isinstance(frontmatter[key], bool):
            errors.append(f"{key!r} must be a boolean")
    for key in STRING_FIELDS:
        if key in frontmatter and not isinstance(frontmatter[key], str):
            errors.append(f"{key!r} must be a string")
    for key in STRING_OR_LIST_FIELDS:
        value = frontmatter.get(key, "")
        if key in frontmatter and not (isinstance(value, str) or _is_string_list(value)):
            errors.append(f"{key!r} must be a string or a list of strings")
    if "effort" in frontmatter and frontmatter["effort"] not in EFFORT_VALUES:
        errors.append(f"'effort' must be one of {sorted(EFFORT_VALUES)}")
    if "shell" in frontmatter and frontmatter["shell"] not in SHELL_VALUES:
        errors.append(f"'shell' must be one of {sorted(SHELL_VALUES)}")
    if "context" in frontmatter and frontmatter["context"] != "fork":
        errors.append("'context' only supports the value 'fork'")
    if "hooks" in frontmatter and not isinstance(frontmatter["hooks"], dict):
        errors.append("'hooks' must be a map")
    for key in ("agent", "background"):
        if key in frontmatter and frontmatter.get("context") != "fork":
            warnings.append(f"{key!r} has no effect without 'context: fork'")


def _check_unknown_fields(frontmatter: Dict[str, Any], target: str,
                          errors: List[str], warnings: List[str]) -> None:
    allowed = SPEC_FIELDS if target == "spec" else CLAUDE_CODE_FIELDS
    unknown = ", ".join(sorted(set(frontmatter) - allowed))
    if not unknown:
        return
    if target == "spec":
        errors.append(f"field(s) not in the spec: {unknown}. Remove them, or "
                      "validate with --target claude-code if they are "
                      "intentional (the skill is then not portable and "
                      "cannot be uploaded)")
    else:
        warnings.append(f"unknown field(s) {unknown}; Claude Code silently ignores them")


def _check_body(body: str, skill_dir: Path,
                errors: List[str], warnings: List[str]) -> None:
    if not body.strip():
        warnings.append("SKILL.md body is empty")
    line_count = len(body.splitlines())
    if line_count > BODY_LINES_MAX:
        warnings.append(f"body is {line_count} lines; keep SKILL.md under "
                        f"{BODY_LINES_MAX} and move detail into references/")
    prose = _strip_code(body)
    if PLACEHOLDER_RE.search(prose):
        warnings.append("body still contains [TODO] placeholders")

    root = skill_dir.resolve()
    for link in sorted(set(LINK_RE.findall(prose))):
        relative = _local_link_target(link)
        if relative is None:
            continue
        resolved = (root / relative).resolve()
        if root not in resolved.parents and resolved != root:
            errors.append(f"link {link!r} escapes the skill directory")
        elif not resolved.exists():
            errors.append(f"link {link!r} points to a file that does not exist")


def _check_reference_depth(skill_dir: Path, warnings: List[str]) -> None:
    references = skill_dir / "references"
    if not references.is_dir():
        return
    for markdown_file in sorted(references.rglob("*.md")):
        text = markdown_file.read_text(encoding="utf-8", errors="replace")
        for link in LINK_RE.findall(text):
            relative = _local_link_target(link)
            if relative and relative.endswith(".md"):
                warnings.append(f"{markdown_file.relative_to(skill_dir)} links to "
                                f"{link!r}; keep references one level deep from SKILL.md")


def _load_frontmatter(skill_md: Path) -> Tuple[Optional[Dict[str, Any]], str, Optional[str]]:
    """Return (frontmatter, body, error)."""
    try:
        front_text, body = split_frontmatter(skill_md.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        return None, "", f"frontmatter: {exc}"
    try:
        frontmatter = yaml.safe_load(front_text)
    except yaml.YAMLError as exc:
        # Claude Code loads such a skill with empty metadata, so it would
        # silently never trigger.
        return None, "", f"invalid YAML in frontmatter: {exc}"
    if not isinstance(frontmatter, dict):
        return None, "", "frontmatter must be a YAML map"
    return frontmatter, body, None


def validate_skill(skill_path: Any, target: str = "spec") -> Findings:
    """Return (errors, warnings). An empty error list means the skill is valid."""
    errors: List[str] = []
    warnings: List[str] = []
    skill_dir = Path(skill_path).resolve()

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"SKILL.md not found in {skill_dir}"], warnings

    frontmatter, body, load_error = _load_frontmatter(skill_md)
    if frontmatter is None:
        return [load_error or "unreadable frontmatter"], warnings

    _check_unknown_fields(frontmatter, target, errors, warnings)
    _check_name(frontmatter, skill_dir, target, errors, warnings)
    _check_description(frontmatter, target, errors, warnings)
    _check_optional_spec_fields(frontmatter, target, errors, warnings)
    if target == "claude-code":
        _check_extensions(frontmatter, errors, warnings)
    _check_body(body, skill_dir, errors, warnings)
    _check_reference_depth(skill_dir, warnings)
    warnings.extend(lint_best_practices(frontmatter, body, skill_dir, target))
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("skill_dir")
    parser.add_argument("--target", choices=("spec", "claude-code"), default="spec")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()

    errors, warnings = validate_skill(args.skill_dir, args.target)
    for error in errors:
        print(f"ERROR: {error}")
    for warning in warnings:
        print(f"WARN:  {warning}")
    failed = bool(errors) or (args.strict and bool(warnings))
    print(f"{'FAIL' if failed else 'OK'} ({args.target}): "
          f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
