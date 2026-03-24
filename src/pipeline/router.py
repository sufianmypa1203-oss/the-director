"""
Pipeline Router — Slash Command Dispatcher

Routes /director, /designer, /motion-architect, /builder to their
respective agent classes. Maintains session state across pipeline stages.
"""
from __future__ import annotations
import asyncio
import re
from typing import Any


# ── Agent Registry ────────────────────────────────────────────────────────────
# Each agent is lazy-imported to avoid circular dependencies and keep
# startup fast. Only /director is implemented — others are placeholders.

def _get_director():
    from director.agent import DirectorAgent
    return DirectorAgent

AGENT_REGISTRY: dict[str, callable] = {
    "/director": _get_director,
    # "/designer":         _get_designer,          # Agent 2 — not yet built
    # "/motion-architect": _get_motion_architect,   # Agent 3 — not yet built
    # "/builder":          _get_builder,            # Agent 4 — not yet built
}


# ── Session State ─────────────────────────────────────────────────────────────

class PipelineSession:
    """
    Maintains state across the full pipeline.
    Persists project_id and completed phases.
    """

    def __init__(self):
        self.project_id: str | None = None
        self.completed_phases: list[str] = []
        self.current_agent: str | None = None

    def mark_phase_complete(self, agent_name: str, project_id: str | None = None):
        self.completed_phases.append(agent_name)
        if project_id:
            self.project_id = project_id

    def get_status(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "completed_phases": self.completed_phases,
            "current_agent": self.current_agent,
        }


# ── Router ────────────────────────────────────────────────────────────────────

async def route(command: str, payload: str, session: PipelineSession) -> str:
    """
    Routes slash commands to the correct agent.
    Streams output to console and captures for return.
    """
    # Validate command
    agent_factory = AGENT_REGISTRY.get(command)
    if not agent_factory:
        available = ", ".join(AGENT_REGISTRY.keys())
        return (
            f"❌ Unknown command: `{command}`.\n"
            f"Available agents: {available}\n\n"
            f"Pipeline order: /director → /designer → /motion-architect → /builder"
        )

    # Check pipeline order
    pipeline_order = ["/director", "/designer", "/motion-architect", "/builder"]
    cmd_idx = pipeline_order.index(command) if command in pipeline_order else -1
    if cmd_idx > 0:
        prev_agent = pipeline_order[cmd_idx - 1].lstrip("/")
        if prev_agent not in session.completed_phases:
            return (
                f"⚠️ Pipeline violation: `{command}` requires `{pipeline_order[cmd_idx - 1]}` "
                f"to complete first.\n\n"
                f"Completed phases: {session.completed_phases or 'None'}\n"
                f"Run `{pipeline_order[cmd_idx - 1]}` first."
            )

    # Instantiate and run
    session.current_agent = command
    AgentClass = agent_factory()
    agent = AgentClass(project_id=session.project_id)

    output_chunks: list[str] = []
    async for chunk in agent.run(payload):
        print(chunk, end="", flush=True)
        output_chunks.append(chunk)

    full_output = "".join(output_chunks)

    # Extract project_id from handoff block
    if "📦 Handoff" in full_output:
        match = re.search(r"`([a-z0-9-]+)`", full_output)
        if match:
            session.mark_phase_complete(
                command.lstrip("/"),
                project_id=match.group(1),
            )

    return full_output


# ── CLI Entry Point ──────────────────────────────────────────────────────────

async def main():
    """Run slash commands from the terminal."""
    import sys

    session = PipelineSession()

    if len(sys.argv) < 2:
        print("🎬 Video Factory Pipeline Router")
        print("Usage: python -m pipeline.router /director <input>")
        print("       python -m pipeline.router /designer")
        print("\nPipeline: /director → /designer → /motion-architect → /builder")
        return

    command = sys.argv[1]
    payload = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    result = await route(command, payload, session)
    if not result.endswith("\n"):
        print()

    print(f"\n📊 Session: {session.get_status()}")


if __name__ == "__main__":
    asyncio.run(main())
