# UDA-Hub: CultPass Support Decision System

UDA-Hub is a LangGraph multi-agent support workflow for the first customer,
CultPass. It classifies natural-language tickets, routes them to a specialist,
retrieves grounded knowledge, safely invokes customer-support tools, resolves or
escalates the issue, and persists both ticket history and cross-session memory.

The application is deliberately deterministic and works without an LLM or API
key. This makes the routing, confidence thresholds, database actions, and tests
fully reproducible. The graph is created directly with `StateGraph`; it does not
use a prebuilt agent or workflow.

## Requirements

- Python 3.11 or 3.12 (tested with Python 3.12)
- `langgraph==1.0.7`
- `langchain-core==1.2.18`
- `SQLAlchemy==2.0.46`
- `python-dotenv==1.2.2`
- `pytest==9.0.2`
- `ipykernel==7.2.0`, `nbclient==0.10.4`, and `nbformat==5.10.4` for notebooks

The exact dependency list is in `requirements.txt`. No `.env` or API key is
required.

## Install and initialize

Run every command from the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.setup_databases
```

The setup command is the non-interactive equivalent of running
`notebooks/01_external_db_setup.ipynb` followed by
`notebooks/02_core_db_setup.ipynb`. It creates:

- `data/external/cultpass.db` (CultPass operational data)
- `data/core/udahub.db` (UDA-Hub account, ticket, knowledge, and memory data)

Both generated databases are intentionally git-ignored. The source JSONL and
setup code are submitted, so they can always be recreated. The knowledge source
contains 16 articles: the original 4 plus 12 new articles spanning billing,
accounts, reservations, accessibility, safety, technical issues, and privacy.

You may instead run the two setup notebooks in numeric order. Each notebook
automatically uses the repository root and imports only files within this project.

## Run

Interactive chat:

```bash
python 03_agentic_app.py --user-id a4ab87 --thread-id demo-session
```

One-ticket JSON output (useful for demonstrations):

```bash
python 03_agentic_app.py \
  --once "I cannot log in and the password reset email has not arrived" \
  --user-id a4ab87 --urgency high
```

An explicit operational mutation is only performed when `--execute-actions` is
set. Without it, billing actions remain a safe preview:

```bash
python 03_agentic_app.py --once "Cancel my subscription" \
  --user-id f556c0 --execute-actions
```

The graph accepts a `SupportTicket` dictionary and a LangGraph config containing
`configurable.thread_id`. See `agentic/workflow.py::process_ticket` for the
programmatic API.

## Test

```bash
pytest -q
python -m scripts.demo
```

The tests use isolated temporary SQLite databases and cover:

- all required schemas and the 16-article knowledge base;
- content + metadata classification and conditional graph routing;
- successful RAG retrieval and low-confidence escalation;
- customer lookup, reservation lookup, and subscription mutation tools;
- structured decision/tool logs;
- short-term checkpoint memory, context-dependent follow-ups, and cross-session persistent memory;
- complete resolution and escalation paths.

The demo also sends “That did not work” after a login/password-reset turn under
the same `thread_id`, showing that classification, retrieval, and the escalation
hand-off retain the original issue.

## Submission map

- `agentic/design/architecture.md` — pre-implementation architecture, diagram,
  state contract, routing, RAG, memory, and failure handling
- `agentic/agents/` — specialized graph node implementations
- `agentic/tools/` — SQLite/SQLAlchemy abstractions, retrieval, and audit logging
- `agentic/workflow.py` — from-scratch LangGraph graph and public API
- `data/models/` — CultPass and UDA-Hub SQLAlchemy models
- `data/external/*.jsonl` — reproducible seed data
- `notebooks/01_external_db_setup.ipynb` — initializes the CultPass external database
- `notebooks/02_core_db_setup.ipynb` — initializes the core database with 16 knowledge articles
- `notebooks/03_agentic_app.ipynb` — demonstrates RAG, tools, memory, and state history
- `03_agentic_app.py` — command-line/interactive entry point
- `scripts/setup_databases.py` — deterministic script equivalent of the setup notebooks
- `scripts/demo.py` — successful resolution, tool use, memory, and escalation demo
- `tests/` — automated rubric-focused test suite

## Safety and expected behavior

Knowledge answers include source article titles and IDs. A request escalates if
retrieval confidence is below `0.42`, if the classifier detects a high-risk issue
(fraud, safety, legal, data breach), or if a tool fails. Tool errors are returned
as structured data rather than leaking exceptions. Every routing decision and
tool outcome is written as searchable JSON Lines under `logs/` (or a test-supplied
path), while ticket messages and long-term memories are stored in the core DB.

For full design rationale, see `agentic/design/architecture.md`.
