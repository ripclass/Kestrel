"""AI red-team harness scaffolding.

The corpus + rubric run today against the heuristic provider so the
prompt templates, redaction layer, and routing logic are continuously
exercised in CI even without API keys configured. When provider keys
are wired into Render, swap the orchestrator's provider table to the
real adapters and the same harness becomes a quality gate against
the live model output.
"""
