#!/usr/bin/env python3
"""Scaffold a spec-compliant skill directory from assets/SKILL.template.md.

Usage:
    init_skill.py <skill-name> [--path DIR] [--description TEXT]
                  [--resources scripts,references,assets]

Creates <DIR>/<skill-name>/SKILL.md. Resource directories are created only when
requested; the spec treats them as optional and empty placeholders just add
noise the agent has to read past.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_MAX = 64
RESOURCE_DIRS = ("scripts", "references", "assets")
DEFAULT_DESCRIPTION = (
    "[TODO] Say what this skill does and when to use it: the user intents, file types "
    "or contexts that should activate it, including cases where the domain is not named."
)
TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "SKILL.template.md"


def validate_name(name: str) -> str:
    if len(name) > NAME_MAX:
        return f"name is {len(name)} chars; max {NAME_MAX}"
    if not NAME_RE.match(name):
        return ("name must be lowercase a-z/0-9 with single hyphens, "
                "not starting or ending with '-'")
    return ""


def render(template: str, name: str, description: str) -> str:
    title = " ".join(word.capitalize() for word in name.split("-"))
    # A JSON string is a valid YAML double-quoted scalar, so colons and
    # brackets in the description cannot break the frontmatter.
    return (template
            .replace("{{name}}", name)
            .replace("{{title}}", title)
            .replace("{{description}}", json.dumps(description, ensure_ascii=False)))


def init_skill(name: str, base: Path, description: str, resources: list) -> Path:
    problem = validate_name(name)
    if problem:
        raise ValueError(problem)
    if not TEMPLATE.is_file():
        raise FileNotFoundError(f"template not found: {TEMPLATE}")

    skill_dir = base.resolve() / name
    if skill_dir.exists():
        raise FileExistsError(f"already exists: {skill_dir}")

    content = render(TEMPLATE.read_text(encoding="utf-8"), name, description)

    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    for resource in resources:
        resource_dir = skill_dir / resource
        resource_dir.mkdir()
        # Keeps the directory in git; package_skill.py leaves it out of archives.
        (resource_dir / ".gitkeep").touch()
    return skill_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("name")
    parser.add_argument("--path", default=".", help="parent directory (default: cwd)")
    parser.add_argument("--description", default=DEFAULT_DESCRIPTION)
    parser.add_argument("--resources", default="",
                        help="comma-separated subset of: " + ",".join(RESOURCE_DIRS))
    args = parser.parse_args()

    resources = [item.strip() for item in args.resources.split(",") if item.strip()]
    unknown_resources = [item for item in resources if item not in RESOURCE_DIRS]
    if unknown_resources:
        print(f"ERROR: unknown resource dir(s): {', '.join(unknown_resources)}", file=sys.stderr)
        return 1

    try:
        skill_dir = init_skill(args.name, Path(args.path), args.description, resources)
    except (ValueError, FileExistsError, FileNotFoundError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Created {skill_dir}/SKILL.md")
    for res in resources:
        print(f"Created {skill_dir}/{res}/")
    print("Next: fill every [TODO], then run scripts/quick_validate.py on the directory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
