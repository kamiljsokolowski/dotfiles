"""Heuristic best-practice lints for a skill directory.

Warnings only, never errors: these are pattern matches over prose and code,
so they can misfire. Imported by quick_validate.py.
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

BODY_TOKENS_MAX = 5000
CHARS_PER_TOKEN = 4
REFERENCE_TOC_LINES = 100
SCRIPT_SUFFIXES = (".py", ".sh", ".bash")

SIDE_EFFECT_RE = re.compile(
    r"\b(git push|git reset --hard|terraform (apply|destroy)"
    r"|kubectl (apply|delete|patch|rollout)|helm (install|upgrade|uninstall)"
    r"|docker push|gh (pr|release|issue) (create|merge|close)"
    r"|argocd app (sync|delete)|rm -rf)\b"
    r"|curl\b[^\n]*-X\s*(POST|PUT|PATCH|DELETE)"
)
TRIGGER_PHRASE_RE = re.compile(r"\b(when|whenever|triggers? on|use (this|it|for))\b", re.IGNORECASE)
FIRST_PERSON_RE = re.compile(r"\b(I|I'm|I'll|I've|my|we|our)\b")
GOTCHA_HEADING_RE = re.compile(r"^#{1,6}\s+.*(gotcha|pitfall|caveat|known issue)", re.IGNORECASE | re.MULTILINE)
VERIFY_HEADING_RE = re.compile(r"^#{1,6}\s+.*(validat|verif)", re.IGNORECASE | re.MULTILINE)
# Inline injection is only live at line start; a fenced block is opened with ```!
INJECTION_RE = re.compile(r"^\s*(!`[^`\n]+`|```!)", re.MULTILINE)
TOC_RE = re.compile(r"^#{1,6}\s*(table of contents|contents|toc)\b", re.IGNORECASE | re.MULTILINE)
HELP_SUPPORT_RE = re.compile(r"argparse|click|typer|--help")
SHELL_PROMPT_RE = re.compile(r"\bread\s+(-\w+\s+)*-p\b|/dev/tty")


def _lint_side_effects(frontmatter: Dict[str, Any], body: str) -> List[str]:
    if frontmatter.get("disable-model-invocation") is True:
        return []
    match = SIDE_EFFECT_RE.search(body)
    if not match:
        return []
    return [f"body runs a side-effecting command ({match.group(0)!r}) but "
            "'disable-model-invocation: true' is not set; Claude could trigger "
            "it unprompted, and must-hold rules belong in a hook"]


def _lint_description(frontmatter: Dict[str, Any]) -> List[str]:
    description = frontmatter.get("description")
    if not isinstance(description, str):
        return []
    warnings = []
    if not TRIGGER_PHRASE_RE.search(description):
        warnings.append("description never says when to use the skill "
                        "(e.g. 'Use when ...'); it is the only routing signal")
    if FIRST_PERSON_RE.search(description):
        warnings.append("description uses first person; write it imperatively "
                        "about the user's intent")
    return warnings


def _lint_headings(body: str) -> List[str]:
    warnings = []
    if not GOTCHA_HEADING_RE.search(body):
        warnings.append("no Gotchas section; it is the highest-value content "
                        "and should grow with every correction")
    if not VERIFY_HEADING_RE.search(body):
        warnings.append("no validation/verification step; end with a check the "
                        "agent can run and report evidence from")
    return warnings


def _lint_injection(frontmatter: Dict[str, Any], body: str) -> List[str]:
    if "allowed-tools" in frontmatter or not INJECTION_RE.search(body):
        return []
    return ["body uses !`command` injection without 'allowed-tools'; outside "
            "auto mode an unapproved command aborts the whole invocation"]


def _lint_body_size(body: str) -> List[str]:
    tokens = len(body) // CHARS_PER_TOKEN
    if tokens <= BODY_TOKENS_MAX:
        return []
    return [f"body is roughly {tokens} tokens; the guidance is under "
            f"{BODY_TOKENS_MAX}, so move detail into references/"]


def _lint_reference_tocs(skill_dir: Path) -> List[str]:
    warnings = []
    for reference in sorted((skill_dir / "references").rglob("*.md")):
        text = reference.read_text(encoding="utf-8", errors="replace")
        if len(text.splitlines()) > REFERENCE_TOC_LINES and not TOC_RE.search(text):
            warnings.append(f"{reference.relative_to(skill_dir)} exceeds "
                            f"{REFERENCE_TOC_LINES} lines without a table of "
                            "contents; agents may preview it partially")
    return warnings


def _is_name_guard(node: ast.stmt) -> bool:
    return (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__")


def _is_bare_call(node: ast.stmt) -> bool:
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)


def _is_python_entrypoint(tree: ast.Module) -> bool:
    # A `__main__` guard or a top-level call statement such as `main()`.
    return any(_is_name_guard(node) or _is_bare_call(node) for node in tree.body)


def _lint_python_script(path: Path, label: str, text: str) -> List[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [f"{label}: does not parse under Python "
                f"{sys.version_info.major}.{sys.version_info.minor} "
                f"({exc.msg}, line {exc.lineno})"]
    warnings = []
    calls_input = any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                      and node.func.id == "input" for node in ast.walk(tree))
    if calls_input:
        warnings.append(f"{label}: calls input(); agents run scripts "
                        "non-interactively and the call would hang")
    # Importable modules are not run directly, so shebang and --help do not apply.
    if _is_python_entrypoint(tree):
        warnings.extend(_lint_entrypoint(path, label, text))
    return warnings


def _lint_entrypoint(path: Path, label: str, text: str) -> List[str]:
    warnings = []
    if not text.startswith("#!"):
        warnings.append(f"{label}: missing shebang")
    elif not os.access(path, os.X_OK):
        warnings.append(f"{label}: has a shebang but is not executable (chmod +x)")
    if not HELP_SUPPORT_RE.search(text):
        warnings.append(f"{label}: no --help support (use argparse)")
    return warnings


def _lint_shell_script(path: Path, label: str, text: str) -> List[str]:
    warnings = _lint_entrypoint(path, label, text)
    if SHELL_PROMPT_RE.search(text):
        warnings.append(f"{label}: prompts interactively (read -p or /dev/tty); "
                        "agents run scripts non-interactively")
    return warnings


def _lint_script(path: Path, skill_dir: Path) -> List[str]:
    label = str(path.relative_to(skill_dir))
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".py":
        return _lint_python_script(path, label, text)
    return _lint_shell_script(path, label, text)


def _lint_scripts(skill_dir: Path) -> List[str]:
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []
    warnings = []
    for path in sorted(scripts_dir.rglob("*")):
        if path.is_file() and path.suffix in SCRIPT_SUFFIXES and "__pycache__" not in path.parts:
            warnings.extend(_lint_script(path, skill_dir))
    return warnings


def lint_best_practices(frontmatter: Dict[str, Any], body: str,
                        skill_dir: Path, target: str) -> List[str]:
    warnings = _lint_description(frontmatter)
    warnings += _lint_headings(body)
    warnings += _lint_body_size(body)
    warnings += _lint_reference_tocs(skill_dir)
    warnings += _lint_scripts(skill_dir)
    if target == "claude-code":
        # These fields only exist in Claude Code, so the checks are meaningless for spec.
        warnings += _lint_side_effects(frontmatter, body)
        warnings += _lint_injection(frontmatter, body)
    return warnings
