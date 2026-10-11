"""Helpers shared by specialized graph nodes."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig


def context(state: dict, config: RunnableConfig | None = None) -> tuple[str, str]:
    configurable = (config or {}).get("configurable", {})
    thread_id = str(configurable.get("thread_id") or state.get("thread_id") or "unknown")
    ticket_id = str(state.get("ticket", {}).get("ticket_id", "unknown"))
    return thread_id, ticket_id


def safe_tool_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Keep useful audit fields while excluding email and other PII."""

    data = result.get("data")
    if isinstance(data, dict):
        data = {key: value for key, value in data.items() if key not in {"email", "full_name"}}
    elif isinstance(data, list):
        data = {"record_count": len(data)}
    return {"ok": result.get("ok"), "tool": result.get("tool"), "data": data, "error": result.get("error")}
