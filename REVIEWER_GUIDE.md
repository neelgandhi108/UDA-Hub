# Reviewer Guide

From the repository root, run:

```bash
# 1. Activate the environment (created with Python 3.12)
source .venv/bin/activate

# 2. Run all unit and integration tests (15 tests)
pytest tests -v

# 3. Run the end-to-end scenario demonstration
python -m scripts.demo

# 4. Run single-ticket CLI evaluations
# Technical question (RAG resolution)
python 03_agentic_app.py --once "I cannot log in and my password reset email never arrived" --user-id a4ab87 --urgency high

# Billing operation (Safe preview vs. explicit action)
python 03_agentic_app.py --once "Cancel my subscription" --user-id f556c0 --execute-actions

# 5. Interactive Chat Mode
python 03_agentic_app.py --user-id a4ab87 --thread-id session-1
```

Expect 15 tests. The suite includes a same-thread login follow-up proving that checkpoint content informs classification and retrieval. The demo displays grounded resolution, subscription tool execution, cross-session preference recall, low-confidence escalation, article sources, confidence scores, and structured decisions. Generated databases stay under `data/`; JSONL audit records appear under `logs/`. Review `agentic/design/architecture.md` for the diagram, agent responsibilities, routing, RAG scoring, state contract, memory design, safety gates, and error handling. No API key or `.env` file is required.
