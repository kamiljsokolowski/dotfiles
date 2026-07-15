#!/bin/bash
input=$(cat)
model=$(jq -r '.tool_input.model // empty' <<<"$input")
subtype=$(jq -r '.tool_input.subagent_type // empty' <<<"$input")

if [[ "$subtype" != "fork" && -z "$model" ]]; then
	jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Set model explicitly for this Agent call per task complexity (see ~/.claude/rules/delegation.md model/effort matrix — user-level file, not project-relative)."
    }
  }'
fi
exit 0
