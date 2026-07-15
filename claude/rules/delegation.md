---
description: Subagent delegation policy — when to delegate vs inline, how to batch parallel work, and which model/effort tier to pick per task complexity.
---

# Subagent Delegation Policy

## Objective

Delegate every subtask that has a clear, independent goal to a subagent —
in parallel wherever multiple subtasks are independent — using a model and
effort tier matched to that subtask's complexity. The objective is targeted
delegation, not maximum spawn count: delegation has real costs (fresh-context
re-briefing, no shared state between parallel siblings, ~N× quota burn for N
agents), so under-delegating and over-delegating are both failure modes.

## Enforcement ceiling

No hook or setting can force decomposition — splitting work and spawning
subagents is always a model judgment call. `~/.claude/hooks/require-model.sh`
only enforces that *a* model is set on every non-`fork` `Agent` call; it has
no way to know which model is *correct* for the task. This file is the
rubric that fills that gap, and `~/.claude/hooks/delegation-nudge.py` is the
per-turn nudge that surfaces it when a prompt looks decomposable.

## Decide: delegate or inline

Delegate a subtask when it is **independent** of the other work in flight
AND at least one of the following holds:

- It can run in parallel with other independent subtasks.
- Its output is context-heavy (logs, file dumps, doc fetches) and would
  bloat the main conversation if read inline.
- It is mechanical enough for a cheaper model — see the matrix below.
- A purpose-built agent already exists for it.

Keep a subtask inline when:

- It is interdependent — a later step needs a sibling's result mid-flight,
  and parallel siblings cannot see each other's work.
- It needs live user interaction — subagents cannot call `AskUserQuestion`
  or any plan-mode-only tool.
- It is trivial and context-bound — briefing a fresh subagent would cost
  more than just doing the work directly.

Never spawn a subagent to re-derive information already in context.

## Batch parallel work in one turn

When two or more subtasks are independent, dispatch each as a separate
`Agent` call **in a single assistant turn** so they run concurrently. Only
sequence subtasks that genuinely depend on each other's output.

## Model / effort matrix

| Task signal | Model | Effort | Delegate |
|---|---|---|---|
| Mechanical: lookup, status check, single-file read | `haiku` | low | If parallel or output-heavy, else inline |
| Focused research or single-file edit with a clear spec | `sonnet` | medium | Yes |
| Standard multi-file implementation | `sonnet` | medium-high | Yes, with `isolation: "worktree"` |
| Judgment-heavy: architecture tradeoffs, hard debugging, plan review | `opus` | high-xhigh | Yes if parallel or context-heavy, else inline |
| Interdependent, interactive, or tiny context-bound work | n/a | n/a | Inline |

On every non-`fork` `Agent` call, set `model` explicitly per this matrix —
`~/.claude/hooks/require-model.sh` denies the call otherwise. A `fork`
inherits the parent's model and full context; never set `model` on a `fork`
call.

## Subagent constraints to brief for

Every subagent starts with a **fresh context** — it has no visibility into
the main conversation, so brief it fully rather than assuming shared
history. Parallel siblings cannot see each other's work mid-flight.
Subagents cannot call `AskUserQuestion` or other plan-mode-only tools.
Nested subagent spawning is supported to a depth of 5 below the main
session; a `fork` cannot itself spawn another `fork`.
