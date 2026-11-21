"""LangSmith tracing for the OpenAI Agents SDK (every agent turn, model call and tool call).

On only when LANGSMITH_TRACING is true and the API key, agent id and agent environment are all set
(LANGSMITH_AGENT_ENVIRONMENT: local | development | staging | production). Otherwise the app runs untraced.
Traces include the user's words and tool results (emails, receipts), so the LangSmith project must stay private.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("purser.tracing")
ENVIRONMENTS = {"local", "development", "staging", "production"}
_done = False


def setup() -> bool:
    global _done
    if _done:
        return True
    if os.getenv("LANGSMITH_TRACING", "").lower() not in ("true", "1"):
        return False
    key = os.getenv("LANGSMITH_API_KEY", "")
    agent_id, env = os.getenv("LANGSMITH_AGENT_ID", ""), os.getenv("LANGSMITH_AGENT_ENVIRONMENT", "")
    if not key or key == "replace-me" or not agent_id or env not in ENVIRONMENTS:
        log.warning("LangSmith tracing requested but not configured (need API key, LANGSMITH_AGENT_ID and an environment of %s)",
                    "/".join(sorted(ENVIRONMENTS)))
        return False
    try:
        from agents import set_trace_processors
        from langsmith.integrations.openai_agents_sdk import OpenAIAgentsTracingProcessor

        # LangSmith replaces the SDK's default exporter, so traces are not also uploaded to the OpenAI dashboard.
        set_trace_processors([OpenAIAgentsTracingProcessor(metadata={"app": "purser", "environment": env})])
    except Exception as e:  # tracing must never stop the app from starting
        log.warning("LangSmith tracing disabled: %s", e)
        return False
    _done = True
    log.info("LangSmith tracing on (agent %s, environment %s)", agent_id, env)
    return True
