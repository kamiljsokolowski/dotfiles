---
name: spec-skill-creator
description: Scaffold, validate, and package agent skills (SKILL.md folders) that follow the open Agent Skills specification, with an explicit choice between portable spec-only frontmatter and Claude Code extension fields. Use when the user wants to create a new skill, write or fix SKILL.md frontmatter, check a skill against the spec, decide whether a skill is portable or uploadable, or build a .skill archive, even if they never say "spec".
---

# Spec Skill Creator

Create skills that pass the open Agent Skills spec, and make the
portability trade-off explicit instead of discovering it at upload time.

For the Dynatrace security audit and the eval/benchmark loop, use
`dt-skill-creator` instead; this skill covers structure, validation and
packaging only.

## Step 0: pick the target

The spec and Claude Code accept different frontmatter. Decide first; it drives
every later step.

- `spec` (default): `name`, `description`, `license`, `compatibility`,
  `metadata`, `allowed-tools`. For skills that must run in other agents or be
  uploaded to claude.ai / the Skills API, where any other key is a hard error.
- `claude-code`: spec fields plus extensions. For local Claude Code skills that
  need side-effect control or isolation.

Claude Code extensions (not portable): `when_to_use`, `argument-hint`,
`arguments`, `disable-model-invocation`, `user-invocable`, `disallowed-tools`,
`model`, `effort`, `context: fork`, `agent`, `background`, `hooks`, `paths`,
`shell`, plus `$ARGUMENTS` substitution and `` !`cmd` `` injection.

If a skill needs both, keep a spec-only copy for distribution and a separate
Claude Code variant; do not strip extensions silently.

## Step 1: capture intent

Ask for 2-3 concrete tasks the skill must handle and the real material it
should encode (runbooks, past incidents, review comments). A skill written
from generic knowledge produces generic advice. If the task is a trivial
one-step action the agent already does with basic tools, recommend no skill.

## Step 2: scaffold

Run from this skill's real directory (resolve with `readlink -f` rather than
using the `~/.claude/skills/` symlink path):

```bash
python3 scripts/init_skill.py <skill-name> --path <parent-dir> \
  [--description "..."] [--resources scripts,references,assets]
```

- Name: lowercase `a-z0-9` and single hyphens, max 64 chars, must equal the
  directory name.
- Resource directories are created only when requested.
- The template is `assets/SKILL.template.md`; edit it to change what every new
  skill starts with.

## Step 3: write the skill

- **Description** (1-1024 chars): imperative, about user intent rather than
  mechanics. State what it does *and* when to use it, including contexts
  where the domain is not named. Descriptions are the only routing signal and
  are always in context, so keep them tight and non-overlapping with other
  skills.
- **Body**: under 500 lines. Procedures over declarations, one default
  approach over a menu, detail the agent lacks rather than what it knows.
- **Gotchas section**: highest-value content. Add an entry per correction.
- **Validation step**: end with a check the agent can run and report evidence
  from.
- **Resources**: link relative to the skill root, one level deep, and say when
  to load each file. Move bulk into `references/`.
- **Scripts**: no interactive prompts, `--help`, structured output on stdout
  and diagnostics on stderr, actionable errors, bounded output, distinct exit
  codes, `--dry-run` for destructive actions, pinned dependencies.
- **Side-effect skills** (deploy, push, post): in `claude-code` target set
  `disable-model-invocation: true`, and put must-hold rules in a hook, since
  skill instructions are advisory.

## Step 4: validate

```bash
python3 scripts/quick_validate.py <skill-dir> [--target spec|claude-code] [--strict]
```

Exit 0 means no errors. It checks frontmatter placement and YAML, field
set and types, name and description limits, name-to-directory match, leftover
`[TODO]` markers, broken or escaping links, reference depth, and body length.
A skill with invalid YAML still loads in Claude Code but never triggers, so do
not skip this.

It also runs heuristic best-practice lints (`scripts/best_practices.py`),
always as warnings, since they are pattern matches that can misfire:

- description lacks a "when to use" phrase, or is written in first person
- no Gotchas section, or no validation/verification step
- body over roughly 5,000 tokens; reference over 100 lines without a TOC
- scripts: `input()` or `read -p` prompts, missing shebang, not executable,
  no `--help` (entry points only)
- `claude-code` target only: side-effecting commands (VCS push, IaC apply,
  cluster apply or delete, registry push, mutating HTTP calls) without
  `disable-model-invocation: true`, and `` !`cmd` `` injection without
  `allowed-tools`

Fix a warning or have a reason to ignore it; `--strict` turns them into
failures for CI.

## Step 5: test triggering

Before packaging, run about 10 realistic prompts that should activate the
skill and 10 near-miss prompts that should not, 3 runs each, and check the
skill is invoked. Fix the description from failures, not the body.

## Step 6: package

```bash
python3 scripts/package_skill.py <skill-dir> -o <output-dir> \
  [--target spec|claude-code] [--strict]
```

Validates first (default target `spec`), then writes `<name>.skill`, a zip
rooted at the skill directory. Left out of the archive: `evals/`,
`*-workspace/`, `.git`, `__pycache__`, `.gitkeep`, symlinks.

## Gotchas

- `---` must be on line 1 of SKILL.md, or the whole file is treated as body.
- Unknown frontmatter keys are ignored by Claude Code without any error, so a
  typo like `disable-model-invokation` silently does nothing; the
  `claude-code` target warns about it.
- `allowed-tools` pre-approves tools for the invoking turn; it does not
  restrict the others.
- Quote `metadata` values: the spec requires string-to-string, and YAML turns
  unquoted `1.0` or `true` into non-strings.
- Skill listing budget is about 1% of the context window; many skills with
  long descriptions get their descriptions dropped, least-used first.
