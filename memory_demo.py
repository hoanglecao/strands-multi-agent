"""Lab 3 — agent memory across separate processes / sessions."""
import argparse
from common import build_agent, make_memory_manager, setup_observability, MEMORY_FILE
from strands import Agent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["write", "read"])
    args = parser.parse_args()
    setup_observability()
    memory_manager = make_memory_manager(allow_writes=(args.action == "write"))
    agent = Agent(
        name="preference_agent",
        system_prompt=(
            "You manage only non-sensitive report formatting preferences. "
            "When asked to save a preference and add_memory is available, call add_memory "
            "and confirm after the tool reports success. "
            "When asked to recall, search_memory is available. Do not invent preferences."
        ),
        memory_manager=memory_manager,
        context_manager="auto",
    )
    if args.action == "write":
        prompt = (
            "Please use add_memory to save this non-sensitive preference: "
            "For incident reports, use Markdown headings Evidence, Hypothesis, "
            "Recommended Checks, and Uncertainty. Do not store credentials."
        )
    else:
        prompt = "What format do I prefer for incident reports? Search memory before answering."
    result = agent(prompt)
    print("\n=== MEMORY RESULT ===\n", result)
    print("Memory storage file:", MEMORY_FILE)
    print("Saved memory depends on a successful add_memory tool call; verify its output/file.")


if __name__ == "__main__":
    main()
