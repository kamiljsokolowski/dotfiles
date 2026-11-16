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

Extract ticket key from `$ARGUMENTS`. If empty, print usage and stop:
```text
Usage: /jira-ip-rights-summary <TICKET-KEY>
```

## Step 1 — Fetch ticket

```bash
acli-pii jira workitem view <KEY> --json 2>/dev/null | jq '{
  key: .key,
  summary: .fields.summary,
  description: .fields.description
}'
```

Fail and stop on error or empty output.

## Step 2 — Extract content

Extract from JSON:
- KEY: `.key`
- SUMMARY: `.fields.summary` (plain string)
- DESCRIPTION: `.fields.description` (ADF JSON)

**ADF parsing**: Recursively traverse `content` arrays. Collect text from `text` nodes. Use `heading` nodes to identify sections ("How", "What", "Implementation"). Extract `paragraph` and `listItem` content for bullets. Skip `mention`, `emoji`, `inlineCard`, `media` nodes.

## Step 3 — Build output

**Output format:**
```
JIRA: [<KEY>](https://dt-rnd.atlassian.net/browse/<KEY>)
<English title> / <Polish title>
- <English bullet> / <Polish bullet>
```

**Title rules:**
- Max 60 chars total (including ` / `)
- English: title case; Polish: sentence case
- Keep acronyms, config terms, product names in English (HPA, ES_JAVA_OPTS, release-info, istio, nginx)
- Translate only clear domain concepts (gateway→brama, label→etykieta, threshold→próg)

**Bullets:**
- Extract from "How"/"Implementation" section first, then "What", then full description
- Use past tense: Implemented, Added, Refactored, Configured, Wrote, Extracted, Optimised (English) / Zaimplementowano, Dodano, Zrefaktoryzowano, Skonfigurowano, Napisano, Wydzielono, Zoptymalizowano (Polish)
- Keep technical terms in English (config identifiers, acronyms, jargon: emit/fallback, dual-emit, locale provider, release-info)
- Translate only domain concepts with standard Polish words
- 1–5 bullets; pick 5 most significant if more exist
- English and Polish must match exactly in meaning

**Edge cases:**
- Empty description: `- No description provided / Brak opisu`
- No "How"/"What" heading: Use full body
- >5 logical points: Pick 5 most significant
- Title >60 chars: Condense without mid-word break
- Non-English content: Translate to English, then Polish

## Step 4 — Review and fix

**English**: Title case (major words only; keep articles/small prepositions lowercase). All verbs past tense. Participial phrases need comma: `Added X, triggering Y` not `Added X triggering Y`.

**Polish**: Third-person impersonal past only (Zaimplementowano, Dodano). No `-ąc` gerunds. Use `w celu + bezokolicznik` for intent. Match English technical specifics exactly (JSON input → wejścia JSON, not vague equivalents). Preserve technical terms in English.

**Bilingual match**: Polish must mean exactly what English means. Same scope qualifiers. Same technical terms. No additions or omissions.

## Step 5 — Output

Print only the formatted result. No preamble, explanations, or metadata.

```
JIRA: [<KEY>](https://dt-rnd.atlassian.net/browse/<KEY>)
<English title> / <Polish title>
- <English bullet> / <Polish bullet>
- <English bullet> / <Polish bullet>
```
