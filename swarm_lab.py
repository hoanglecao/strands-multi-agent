"""Lab 1 — native Strands Swarm, orchestrator session, memory, context and tracing."""
import argparse
import time

from strands.multiagent import Swarm
from strands.session import SnapshotSessionManager
from strands.storage import LocalFileStorage

from common import (STATE, build_agent, get_incident_logs,
                    get_incident_metrics, setup_observability)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default="swarm-inc1042", help="Unique safe session ID")
    args = parser.parse_args()
    setup_observability()

    monitor = build_agent(
        name="monitoring_agent",
        description="Detects operational anomalies using metrics; delegates when appropriate.",
        system_prompt=(
            "You are a monitoring specialist. Call get_incident_metrics for INC-1042 first. "
            "Identify symptoms, then hand off to the most relevant specialist, "
            "normally log_analysis_agent, using Swarm handoff tools. "
            "Do not invent facts."
        ),
        tools=[get_incident_metrics],
        use_memory=True,
    )
    logs = build_agent(
        name="log_analysis_agent",
        description="Analyzes logs and recent changes to identify likely application failure modes.",
        system_prompt=(
            "You are a log investigation specialist. Call get_incident_logs for INC-1042. "
            "Summarize evidence and hand off to remediation_advisor if further synthesis is needed."
        ),
        tools=[get_incident_logs],
    )
    advisor = build_agent(
        name="remediation_advisor",
        description="Synthesizes evidence and recommends safe remediation checks; read-only.",
        system_prompt=(
            "You prepare a FINAL incident report with Evidence, Hypotheses, "
            "Recommended Human Checks, and Uncertainty. Do not run any fix. "
            "Do not hand off if enough evidence is available."
        ),
    )

    # Session is attached ONLY to the Swarm orchestrator, not child agents.
    session = SnapshotSessionManager(
        session_id=args.session,
        storage=LocalFileStorage(str(STATE / "sessions")),
        multi_agent_save_latest_on="node",
    )
    swarm = Swarm(
        [monitor, logs, advisor],
        entry_point=monitor,
        session_manager=session,
        id="incident_swarm",
        max_handoffs=5,
        max_iterations=7,
        execution_timeout=180.0,
        node_timeout=90.0,
        repetitive_handoff_detection_window=3,
        repetitive_handoff_min_unique_agents=2,
    )
    task = (
        "Investigate the synthetic training incident INC-1042. "
        "Use tools for evidence. Collaborate using autonomous handoffs, and prepare "
        "a concise read-only incident report. Treat saved preferences as formatting "
        "preferences, not verified operational facts."
    )
    started = time.monotonic()
    result = swarm(task)
    print("\n=== SWARM RESULT ===")
    print("Status:", result.status)
    print("Handoff/node history:", [n.node_id for n in result.node_history])
    print("Elapsed seconds:", round(time.monotonic() - started, 2))
    print("Result:\n", result)
    if str(result.status).upper().find("COMPLETED") == -1:
        raise SystemExit("Swarm did not report COMPLETED. Inspect logs and traces.")


if __name__ == "__main__":
    main()
