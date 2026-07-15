---
name: atomic-note-validator
description: >
  Validates and optionally improves Obsidian knowledge base notes against atomic note principles.
  Use this skill whenever the user wants to audit, review, validate, or improve one or more Obsidian
  notes — whether ad-hoc ("does this note look right?"), during a cleanup pass, or in a batch review.
  Also trigger when the user pastes raw note content and asks if it's well-formed, atomic, clear,
  or appropriately titled. Works with pasted content, file paths, or raw markdown.
---

# Atomic Note Validator

Validates Obsidian knowledge base notes against atomic note principles and suggests improvements
when needed. Works in both Claude.ai (pasted content) and Claude Code (file paths).

---

## Note Quality Criteria

A valid note must satisfy all four of these:

| # | Criterion | What it means |
|---|-----------|---------------|
| 1 | **Atomic** | One idea only. If you can split it into two independent notes, it should be split. |
| 2 | **Minimal** | Only the essence. No padding, preamble, or restating the obvious. |
| 3 | **Self-contained** | Readable without context. Title alone should tell you what's inside. |
| 4 | **Title as API** | Title = the query someone would type to find this note. Specific, not categorical. |

---

## Workflow

### Step 1 — Receive input

**In Claude.ai**: User pastes note content (with or without a filename).  
**In Claude Code**: User provides a file path. Read the file before proceeding.

```bash
# Claude Code only
cat "<path-to-note>.md"
```

### Step 2 — Validate

Evaluate the note against all four criteria. For each criterion, determine:

- ✅ Pass — criterion is met
- ⚠️ Weak — partially met, could be improved
- ❌ Fail — criterion is not met

### Step 3 — Output validation report

Always output the report in this format:

```
## Validation: <current note title>

| Criterion       | Status | Notes |
|-----------------|--------|-------|
| Atomic          | ✅/⚠️/❌ | <brief reason> |
| Minimal         | ✅/⚠️/❌ | <brief reason> |
| Self-contained  | ✅/⚠️/❌ | <brief reason> |
| Title as API    | ✅/⚠️/❌ | <brief reason> |

**Verdict**: Pass / Needs improvement
```

If verdict is **Pass** — stop here. Say so clearly.

### Step 4 — Suggest improvements (only if verdict is "Needs improvement")

Suggestions are always **advisory**, never applied automatically.

Structure suggestions as follows:

#### If the title needs improvement

```
**Suggested title**: <proposed title>
**Why**: <one sentence rationale>
```

#### If the content needs improvement

```
**Suggested content**:
---
<full revised note content in markdown>
---
**What changed**: <brief bullet list of what was changed and why>
```

#### If the note should be split

```
**Split into**:
- `<Note title 1>` — <one line on what it covers>
- `<Note title 2>` — <one line on what it covers>
**Why**: <one sentence rationale>
```

Do not combine split suggestions with rewrite suggestions — if splitting is needed, suggest the
split first and let the user decide before rewriting.

---

## Title as API — Guidance

Good titles are specific queries, not categories:

| ❌ Categorical (bad) | ✅ Query-like (good) |
|----------------------|----------------------|
| Python | Init a Python project |
| Kubernetes | Drain a Kubernetes node safely |
| Networking | How TCP handshake works |
| Git | Undo the last Git commit |

If the current title is categorical or vague, always suggest a replacement.

---

## Atomic Split Signals

Split the note if it contains:

- Two or more distinct "how to" steps that could each stand alone
- A concept *and* a procedure (separate them)
- Multiple technologies or tools, each described independently
- Sections with their own subheadings that don't depend on each other

Do **not** split if:

- Context from one part is required to understand another
- The note is a deliberate comparison between two things
- Removing either part would make the remaining note incomplete

---

## Minimalism — What to Strip

Flag for removal:

- Introductory sentences that restate the title ("This note covers...")
- Conclusion sentences ("In summary...")
- Filler transitions ("First, it's worth noting that...")
- Redundant examples when one suffices
- Background context that belongs in a separate linked note

Keep:

- In-context links `[[related note]]`
- Inline references, sources, or footnotes
- Code blocks, commands, or examples that are the core content

---

## Batch Mode (Claude Code)

If the user provides a directory or a list of files, validate each note in sequence.

```bash
# List all markdown files
find "<vault-path>" -name "*.md" | sort
```

After validating all notes, output a summary table:

```
## Batch Validation Summary

| Note | Atomic | Minimal | Self-contained | Title as API | Verdict |
|------|--------|---------|----------------|--------------|---------|
| <title> | ✅ | ✅ | ⚠️ | ❌ | Needs improvement |
...

**Total**: X passed, Y need improvement
```

Then offer to show full details and suggestions for each failing note, one at a time.
