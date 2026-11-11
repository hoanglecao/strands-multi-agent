"""Lab 2 — explicit developer-defined Workflow with parallel independent tasks.

This is the documented Workflow PATTERN implemented with Python orchestration,
not a call to an SDK class called Workflow or the legacy strands_tools.workflow.
"""
import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from strands.session import SnapshotSessionManager
from strands.storage import LocalFileStorage

from common import (INCIDENT, STATE, build_agent, get_incident_logs,
                    get_incident_metrics, setup_observability)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default="report-inc1042")
    args = parser.parse_args()
    setup_observability()

    # Collector is deterministic code, not a model call.
    def collect() -> str:
        return json.dumps({"incident_id": INCIDENT["incident_id"], "service": INCIDENT["service"]})

    metrics_agent = build_agent(
        name="workflow_metrics_analyst",
        description="Reviews synthetic metrics and produces a structured summary.",
        system_prompt="Call get_incident_metrics for INC-1042. Return observed values, interpretation, and uncertainty.",
        tools=[get_incident_metrics],
    )
    logs_agent = build_agent(
        name="workflow_logs_analyst",
        description="Reviews synthetic logs and produces a structured summary.",
        system_prompt="Call get_incident_logs for INC-1042. Return evidence, change correlation, and uncertainty.",
        tools=[get_incident_logs],
    )

    # The report-writing Agent persists its conversation between workflow runs.
    # The whole Python workflow does not automatically gain SDK Workflow-session semantics.
    report_session = SnapshotSessionManager(
        session_id=args.session,
        storage=LocalFileStorage(str(STATE / "sessions")),
    )
    report_agent = build_agent(
        name="workflow_report_writer",
        description="Combines parallel analyses into a concise read-only incident report.",
        system_prompt=(
            "Write a concise incident report: Evidence, Most Likely Cause (as hypothesis), "
            "Recommended Human Checks, and Risks. Use saved preferences for output formatting "
            "only. Never substitute remembered facts for current evidence."
        ),
        use_memory=True,
        session_manager=report_session,
    )

    started = time.monotonic()
    collected = collect()                    # Stage 1: collect / prepare
    print("Stage 1 — collected incident metadata:", collected)

    # Stage 2: independent Agent calls run in parallel; no shared Agent instance.
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_metrics = pool.submit(metrics_agent, "Investigate INC-1042 metrics, using your tool.")
        f_logs = pool.submit(logs_agent, "Investigate INC-1042 logs, using your tool.")
        metrics_result = str(f_metrics.result())
        logs_result = str(f_logs.result())
    print("Stage 2 — both analyses complete")

    # Stage 3: join outputs from both branches into the report-writing Agent.
    report = report_agent(
        "Create an incident report using ONLY these synthetic, freshly obtained results.\n"
        f"METADATA:\n{collected}\n\nMETRICS:\n{metrics_result}\n\nLOGS:\n{logs_result}"
    )
    print("\n=== WORKFLOW RESULT ===\n", report)
    print("Elapsed seconds:", round(time.monotonic() - started, 2))

    # Application-level checkpoint for the overall workflow; separate from SDK Agent session.
    run = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident": "INC-1042",
        "stages": ["collect", "metrics_and_logs_parallel", "report"],
        "metrics_excerpt": metrics_result[:250],
        "logs_excerpt": logs_result[:250],
        "report_excerpt": str(report)[:700],
    }
    path = STATE / "workflow_run.json"
    path.write_text(json.dumps(run, indent=2), encoding="utf-8")
    print("Application workflow checkpoint:", path)


if __name__ == "__main__":
    main()
