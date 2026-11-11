"""Shared, read-only lab fixtures and Strands configuration."""
import json
import logging
import os
from pathlib import Path

from strands import Agent, tool
from strands.memory import MemoryManager
from strands.vended_memory_stores.test_memory_store import TestMemoryStore

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state"
STATE.mkdir(exist_ok=True)
MEMORY_FILE = STATE / "operator_preferences.json"

# Entirely synthetic information. Tools do not access AWS or production systems.
INCIDENT = {
    "incident_id": "INC-1042",
    "service": "checkout-api",
    "environment": "training-sandbox",
    "metric_window": "2026-11-10T08:00:00Z/2026-11-10T08:15:00Z",
    "p95_latency_ms": {"baseline": 180, "observed": 2450},
    "http_5xx_pct": 8.1,
    "database_connections": {"max": 100, "observed": 99},
    "cpu_pct": 48,
    "log_samples": [
        "08:03:10 ERROR checkout-api database connection acquisition timed out",
        "08:04:11 WARN checkout-api connection pool near capacity",
        "08:06:05 ERROR checkout-api request failed: DB pool exhausted",
    ],
    "recent_change": "checkout-api release 2.7 at 07:55 UTC",
}


@tool
def get_incident_metrics(incident_id: str) -> str:
    """Return synthetic read-only metrics for incident INC-1042."""
    if incident_id != INCIDENT["incident_id"]:
        return json.dumps({"error": "Unknown training incident"})
    keys = ("incident_id", "service", "metric_window", "p95_latency_ms", "http_5xx_pct", "database_connections", "cpu_pct")
    return json.dumps({k: INCIDENT[k] for k in keys}, indent=2)


@tool
def get_incident_logs(incident_id: str) -> str:
    """Return synthetic read-only log excerpts and recent change for incident INC-1042."""
    if incident_id != INCIDENT["incident_id"]:
        return json.dumps({"error": "Unknown training incident"})
    return json.dumps({"incident_id": incident_id, "logs": INCIDENT["log_samples"], "recent_change": INCIDENT["recent_change"]}, indent=2)

# 	A project-defined function intended to create or configure the MemoryManager
def make_memory_manager(*, allow_writes: bool = False) -> MemoryManager:
    """Use a local JSON test store. Only memory_demo enables agent writes."""
    store = TestMemoryStore(name="operator_preferences", path=str(MEMORY_FILE))
    return MemoryManager(stores=[store], add_tool_config=allow_writes)


def build_agent(*, name: str, description: str, system_prompt: str,
                tools=None, use_memory=False, session_manager=None) -> Agent:
    args = dict(
        name=name,
        description=description,
        system_prompt=system_prompt + "\nUse only synthetic lab evidence. Never claim a real AWS check or make changes.",
        tools=list(tools or []),
        context_manager="auto",  # Experimental: see current Strands docs
    )
    if use_memory:
        args["memory_manager"] = make_memory_manager()
    if session_manager is not None:
        args["session_manager"] = session_manager
    return Agent(**args)


def setup_observability() -> None:
    """Console OTEL spans when LAB_TRACE=1; always provide normal Python logs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    logging.getLogger("strands.multiagent").setLevel(logging.INFO)
    if os.getenv("LAB_TRACE", "0") == "1":
        from strands.telemetry import StrandsTelemetry
        StrandsTelemetry().setup_console_exporter()
        print("OpenTelemetry console tracing enabled (may contain prompts/tool data).")
