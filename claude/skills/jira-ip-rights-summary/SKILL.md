---
name: jira-ip-rights-summary
description: >
  Fetch a JIRA ticket and produce bilingual (English/Polish) IP rights
  documentation. Outputs a JIRA link, a bilingual title (≤60 chars), and 1–5
  past-tense bullets describing completed work. Triggers: "ip rights",
  "prawa autorskie", "IP documentation", "dokumentacja IP", "ip summary".
allowed-tools: Bash(acli-pii jira *)
argument-hint: "<TICKET-KEY>"
---

# jira-ip-rights-summary

## Step 0 — Parse arguments

Extract the ticket key from `$ARGUMENTS`. If empty or missing, print:

```text
Usage: /jira-ip-rights-summary <TICKET-KEY>
Example: /jira-ip-rights-summary CLIN-12345
```

Then stop.

## Step 1 — Fetch ticket

```bash
acli-pii jira workitem view <KEY> --json 2>/dev/null | jq '{
  key: .key,
  summary: .fields.summary,
  description: .fields.description
}'
```

If the command fails or returns empty output: report the error and stop.
Do not retry silently.

## Step 2 — Extract content

From the JSON:

- **KEY** — `.key` (top-level field)
- **SUMMARY** — `.fields.summary` (plain string)
- **DESCRIPTION** — `.fields.description` (ADF JSON)

**ADF extraction rules:**

- Traverse `content` arrays recursively; collect text from `text` nodes
- Treat `heading` node text as section names ("How", "What", "Implementation")
- `paragraph` and `listItem` content = bullet point candidates
- Ignore `mention`, `emoji`, `inlineCard`, and `media` nodes

## Step 3 — Build output

### Ticket link

```text
JIRA: [<KEY>](https://dt-rnd.atlassian.net/browse/<KEY>)
```

### Title line

Derive a bilingual title from SUMMARY:

- Format: `<English> / <Polish>`
- Max 60 characters total including the ` / ` separator
- English: title case; Polish: sentence case
- Keep technical terms, product names, and acronyms in English in both versions
- If translation pushes past 60 chars: condense without mid-word truncation

### Bullet points

Extract key accomplishments from DESCRIPTION:

1. Prefer content under a heading matching `How` or `Implementation`
   (case-insensitive)
2. Fall back to content under a `What` heading
3. Fall back to full description body
4. Produce 1–5 bullets — only as many as meaningful content supports
5. If more than 5 exist: select the 5 most technically significant

Format each bullet as:

```text
- <English past tense> / <Polish past tense>
```

- English verbs: Implemented, Added, Refactored, Configured, Wrote,
  Extracted, Optimised
- Polish verbs: Zaimplementowano, Dodano, Zrefaktoryzowano,
  Skonfigurowano, Napisano, Wydzielono, Zoptymalizowano
- Technical terms, product names, acronyms: keep in English in both columns
- English and Polish must describe the same action — not independent summaries

**Edge cases:**

| Scenario | Behaviour |
| --- | --- |
| Empty description | `- No description provided / Brak opisu` |
| No "How"/"What"/"Implementation" heading | Summarise full body |
| More than 5 logical points | Select 5 most technically significant |
| Title exceeds 60 chars after translation | Condense; no mid-word cut |
| Non-English ticket content | Translate to English first, then Polish |

## Step 4 — Grammar and alignment review

Before printing, review the draft for the issues below. Fix inline.

### English

- **Title case**: all major words capitalised in the English title;
  prepositions ≤4 chars, articles, and conjunctions stay lowercase
- **Past tense**: all verbs must be past tense — fix any present-tense
  or infinitive slip
- **Participial comma**: insert a comma before a participial phrase
  modifying the whole clause:
  `Added X to script, triggering Y` — not `Added X to script triggering Y`

### Polish

- **Impersonal past forms only**: use third-person impersonal past
  (Zaimplementowano, Dodano) — never `-ąc` gerunds in purpose clauses
  (e.g. "umożliwiając", "wywołując")
- **Purpose clauses**: use `w celu + bezokolicznik` ("w celu poprawnego
  przekazania") not `-ąc` gerunds when expressing intent
- **Technical precision**: do not paraphrase technical specifics from
  the English — if English says "JSON input", Polish must say
  "wejścia JSON", not a vague equivalent like "wywołania"

### Bilingual alignment

- Each Polish bullet must convey exactly the same meaning as its English
  counterpart — no additions, no omissions of substantive content
- If English carries a scope qualifier ("end-to-end", "per-stack",
  "nuke option"), Polish must carry an equivalent — do not drop or
  substitute silently
- Technical terms, tool names, and acronyms appear unchanged in both
  columns

Apply all fixes to the draft, then proceed to Step 5.

## Step 5 — Output

Print **only** the formatted result. No preamble, no explanation, no metadata.

```text
JIRA: [<KEY>](https://dt-rnd.atlassian.net/browse/<KEY>)
<English title> / <Polish title>
- <English> / <Polish>
- <English> / <Polish>
```

### Example

```text
JIRA: [PROJ-123](https://dt-rnd.atlassian.net/browse/PROJ-123)
Rate limiting implementation / Implementacja limitowania
- Added Bucket4j integration / Dodano integrację Bucket4j
- Configured per-user rate limits / Skonfigurowano limity na użytkownika
- Added 429 handler with Retry-After / Dodano obsługę 429 z Retry-After
```
