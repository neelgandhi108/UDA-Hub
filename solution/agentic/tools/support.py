"""Structured tools callable by operations and knowledge agents."""

from __future__ import annotations

from typing import Any, Callable

from .repositories import CoreRepository, CultPassRepository


class SupportTools:
    def __init__(self, external: CultPassRepository, core: CoreRepository):
        self.external = external
        self.core = core

    @staticmethod
    def _run(name: str, operation: Callable[[], Any]) -> dict:
        try:
            data = operation()
            if data is None:
                return {"ok": False, "tool": name, "data": None, "error": "Customer was not found"}
            return {"ok": True, "tool": name, "data": data, "error": None}
        except (ValueError, LookupError, PermissionError) as exc:
            return {"ok": False, "tool": name, "data": None, "error": str(exc)}
        except Exception as exc:  # DB failures are controlled but not exposed in detail.
            return {"ok": False, "tool": name, "data": None,
                    "error": f"{type(exc).__name__}: support database operation failed"}

    def lookup_account(self, external_user_id: str) -> dict:
        return self._run("lookup_account", lambda: self.external.lookup_account(external_user_id))

    def list_reservations(self, external_user_id: str) -> dict:
        return self._run("list_reservations", lambda: self.external.list_reservations(external_user_id))

    def update_subscription(self, external_user_id: str, action: str) -> dict:
        return self._run("update_subscription", lambda: self.external.update_subscription(external_user_id, action))

    def search_knowledge(self, account_id: str, query: str, limit: int = 3) -> dict:
        return self._run("search_knowledge", lambda: self.core.search_knowledge(account_id, query, limit))
