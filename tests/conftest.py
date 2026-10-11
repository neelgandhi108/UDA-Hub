from __future__ import annotations

import sys
from pathlib import Path

import pytest


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
if str(SOLUTION_ROOT) not in sys.path:
    sys.path.insert(0, str(SOLUTION_ROOT))

from agentic.tools import CoreRepository, CultPassRepository, SupportTools
from agentic.workflow import build_workflow
from scripts.setup_databases import setup_all


@pytest.fixture()
def project(tmp_path):
    external_db, core_db = setup_all(tmp_path / "cultpass.db", tmp_path / "udahub.db")
    log_path = tmp_path / "audit.jsonl"
    graph = build_workflow(core_db_path=core_db, external_db_path=external_db, log_path=log_path)
    tools = SupportTools(CultPassRepository(external_db), CoreRepository(core_db))
    return {
        "external_db": external_db,
        "core_db": core_db,
        "log_path": log_path,
        "graph": graph,
        "tools": tools,
    }


def ticket(text: str, user_id: str = "f556c0", **metadata):
    return {
        "account_id": "cultpass",
        "external_user_id": user_id,
        "user_name": "Test Customer",
        "text": text,
        "channel": "chat",
        "urgency": "normal",
        **metadata,
    }
