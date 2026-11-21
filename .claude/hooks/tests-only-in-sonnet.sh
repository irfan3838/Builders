#!/usr/bin/env bash
# Project rule (user, 2026-11-21): only the Sonnet subagent runs tests.
# PreToolUse/Bash: deny test-runner invocations issued by the main session; allow them inside subagents.
# Only a runner at the start of a command segment counts (start, newline, ;, &&, ||, |), optionally
# prefixed by env vars, `uv run`, `python -m`, `npx` or `npm run`. Words inside quoted text or heredocs don't.
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
agent_id=$(printf '%s' "$input" | jq -r '.agent_id // empty')
if [ -n "${MUNSHI_HOOK_DEBUG:-}" ]; then
  mkdir -p /tmp/claude-1000
  printf '%s keys=%s agent_id=%s\n' "$(date +%T)" "$(printf '%s' "$input" | jq -c 'keys')" "$agent_id" >> /tmp/claude-1000/munshi-hook-debug.log
fi
runner='(([A-Z_][A-Z0-9_]*=[^[:space:]]+[[:space:]]+)*)((uv run|python3? -m|npx|npm run|timeout [0-9]+)[[:space:]]+)*(pytest|py\.test|vitest|jest)([[:space:]]|$)'
npm_test='npm[[:space:]]+(run[[:space:]]+)?test([[:space:]]|$)'
if printf '%s\n' "$cmd" | sed -E 's/(&&|\|\||;|\|)/\n/g' | sed -E 's/^[[:space:]]+//; s/^cd [^[:space:]]+[[:space:]]*$//' \
   | grep -Eq "^(${runner}|${npm_test})"; then
  if [ -z "$agent_id" ]; then
    jq -n '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny",
      permissionDecisionReason: "Project rule: tests run only in a Sonnet subagent. Spawn or message an Agent with model \"sonnet\" (e.g. the sonnet-tester) to run or write tests, then relay its results."}}'
  fi
fi
exit 0
