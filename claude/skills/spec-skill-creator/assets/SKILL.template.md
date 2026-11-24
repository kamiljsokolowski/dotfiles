---
name: {{name}}
description: {{description}}
---

# {{title}}

<!-- Filled in by scripts/init_skill.py. Delete this comment and every
[TODO] marker before packaging. -->

## When to use

[TODO] Name the user intents and contexts that should activate this skill,
including ones where the domain is not named explicitly. The `description`
frontmatter is the only text the agent sees before activation, so anything
about *when* belongs there as well.

## Workflow

[TODO] Numbered, verifiable steps. Prefer a default approach over a menu of
options. Spend words on what the agent would get wrong without this skill.

1. [TODO]
2. [TODO]

## Gotchas

[TODO] Environment-specific facts that defy reasonable assumptions: naming
quirks, soft-deleted records, endpoints that differ from what the name
suggests. This is the highest-value section; add an entry every time the agent
makes a correction.

## Validation

[TODO] A check the agent can run to prove the result is right (command, exit
code, expected output), and what to do when it fails.

## Resources

[TODO] Link bundled files with paths relative to this directory, one level
deep, and say *when* to load each one. Delete this section if the skill
bundles nothing.

- `scripts/`: executable helpers; must run non-interactively and print
  structured output
- `references/`: focused docs loaded on demand
- `assets/`: templates and static files used in output
