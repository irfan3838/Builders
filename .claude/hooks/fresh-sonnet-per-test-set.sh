#!/usr/bin/env bash
# Project rule (user, 2026-11-21): every set of tests gets a NEW Sonnet agent.
# PreToolUse/Agent|SendMessage:
#  * SendMessage to an existing tester agent (name contains "test") is denied -> spawn a fresh one instead.
#  * Agent spawns whose prompt is about writing/running tests must use model "sonnet" and not be a fork
#    (forks always run on the parent model).
input=$(cat)
tool=$(printf '%s' "$input" | jq -r '.tool_name // ""')
deny() {
  jq -n --arg r "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}}'
  exit 0
}
case "$tool" in
  SendMessage)
    to=$(printf '%s' "$input" | jq -r '.tool_input.to // ""')
    if printf '%s' "$to" | grep -qi 'test'; then
      deny "Project rule: each set of tests needs a NEW Sonnet agent. Do not reuse \"$to\"; spawn a fresh Agent with model \"sonnet\" (give it a new name, e.g. sonnet-tester-<round>) and include the context it needs in the prompt."
    fi
    ;;
  Agent)
    prompt=$(printf '%s' "$input" | jq -r '.tool_input.prompt // ""')
    model=$(printf '%s' "$input" | jq -r '.tool_input.model // ""')
    stype=$(printf '%s' "$input" | jq -r '.tool_input.subagent_type // ""')
    if printf '%s' "$prompt" | grep -Eqi '\b(pytest|vitest|jest|test suite|(write|run|add|re-?run) (the )?tests?)\b'; then
      if [ "$stype" = "fork" ] || [ "$model" != "sonnet" ]; then
        deny "Project rule: test work runs only in a NEW Sonnet agent. Spawn a fresh Agent with model \"sonnet\" (not a fork)."
      fi
    fi
    ;;
esac
exit 0
