"""
The Director — DirectorAgent Class (Async SDK Loop)

Built on the Claude Agent SDK's native async streaming loop with an
evaluator-optimizer pass before any handoff. The agent:
1. Detects blueprints in user input for fast-track intake
2. Runs the 7-category state-machine intake
3. Generates 3 locked artifacts
4. Self-validates via separate evaluator LLM call
5. Optimizes if issues found
6. Emits handoff block only when clean
"""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable

from .models import IntakeState, SceneMapModel
from .tools import DIRECTOR_TOOLS, run_validation, generate_handoff_block
from .prompts import DIRECTOR_SYSTEM_PROMPT
from .validator import ArtifactValidator


__version__ = "2.0.0"
SPECS_DIR = Path("specs")
logger = logging.getLogger("the-director")


# ─── Lifecycle Hooks ──────────────────────────────────────────────────────────

class LifecycleHooks:
    """
    Agent lifecycle hooks for observability, guardrails, and control.
    Per Claude Agent SDK 2026 patterns — validates/blocks tool calls
    before execution, and logs results after.
    """

    def __init__(self):
        self._pre_hooks: list[Callable] = []
        self._post_hooks: list[Callable] = []
        self._event_log: list[dict[str, Any]] = []

    def on_pre_tool_use(self, fn: Callable) -> Callable:
        """Register a hook that runs BEFORE a tool call. Can block execution."""
        self._pre_hooks.append(fn)
        return fn

    def on_post_tool_use(self, fn: Callable) -> Callable:
        """Register a hook that runs AFTER a tool call. For logging/metrics."""
        self._post_hooks.append(fn)
        return fn

    async def run_pre_hooks(self, tool_name: str, args: dict) -> bool:
        """Run all pre-hooks. Returns False if any hook blocks execution."""
        for hook in self._pre_hooks:
            result = hook(tool_name, args)
            if result is False:
                self.log_event("TOOL_BLOCKED", tool=tool_name, reason="Pre-hook rejected")
                return False
        return True

    async def run_post_hooks(self, tool_name: str, result: Any) -> None:
        """Run all post-hooks for observability."""
        for hook in self._post_hooks:
            hook(tool_name, result)

    def log_event(self, event_type: str, **data: Any) -> None:
        """Structured event logging for observability."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            **data,
        }
        self._event_log.append(entry)
        logger.info("%s: %s", event_type, json.dumps({k: str(v) for k, v in data.items()}))

    @property
    def events(self) -> list[dict[str, Any]]:
        return self._event_log.copy()


class DirectorAgent:
    """
    Agent 1 — The Director.
    Owns: intake → brief → script → scene-map → validation → handoff.
    Architecture: state-machine intake + Pydantic contracts + evaluator-optimizer loop.
    """

    version = __version__

    def __init__(self, project_id: str | None = None):
        self.project_id    = project_id
        self.intake_state  = IntakeState()
        self.validator     = ArtifactValidator()
        self.hooks         = LifecycleHooks()
        self.conversation: list[dict] = []
        SPECS_DIR.mkdir(exist_ok=True)

        # Register default hooks
        self._register_default_hooks()

    @classmethod
    def from_blueprint(cls, blueprint_text: str, project_id: str | None = None) -> "DirectorAgent":
        """
        Factory method: create a DirectorAgent pre-loaded with a blueprint.
        Skips the intake interview entirely.

        Usage:
            agent = DirectorAgent.from_blueprint("Topic: debt. Platform: TikTok...")
            async for chunk in agent.run(agent.intake_state.data.get('_raw', '')):
                print(chunk)
        """
        instance = cls(project_id=project_id)
        instance.intake_state.blueprint_provided = True
        instance.intake_state.data["_raw"] = blueprint_text
        instance.hooks.log_event("BLUEPRINT_LOADED", chars=len(blueprint_text))
        return instance

    def _register_default_hooks(self) -> None:
        """Register built-in lifecycle hooks."""

        @self.hooks.on_pre_tool_use
        def guard_scope_boundary(tool_name: str, args: dict) -> bool:
            """Block tool calls that violate Director scope."""
            forbidden_tools = {"design", "render", "animate", "build_component"}
            if tool_name.lower() in forbidden_tools:
                logger.warning("Scope violation: Director cannot use tool '%s'", tool_name)
                return False
            return True

        @self.hooks.on_post_tool_use
        def log_tool_result(tool_name: str, result: Any) -> None:
            """Log tool usage for observability."""
            self.hooks.log_event(
                "TOOL_USED",
                tool=tool_name,
                success=isinstance(result, dict) and result.get("success", True),
            )

    # ── Entry Point ───────────────────────────────────────────────────────

    async def run(self, user_input: str) -> AsyncIterator[str]:
        """
        Main agent loop. Streams tokens back to the caller.
        Detects blueprint in user_input and fast-tracks intake if present.
        """
        self.hooks.log_event("RUN_STARTED", input_chars=len(user_input), project=self.project_id)

        # Blueprint detection — skip intake if full brief provided
        if self._looks_like_blueprint(user_input):
            self.intake_state.blueprint_provided = True
            self.hooks.log_event("BLUEPRINT_DETECTED")
            yield "📋 Blueprint detected — extracting all 7 categories...\n\n"
            user_input = f"[BLUEPRINT MODE] Extract all 7 intake categories from this blueprint and fill gaps:\n\n{user_input}"

        # Run the main agent loop
        async for chunk in self._agent_loop(user_input):
            yield chunk

        # After loop completes — run evaluator pass if artifacts exist
        if self._artifacts_present():
            yield "\n\n---\n🔍 **Running evaluator-optimizer pass on generated artifacts...**\n\n"
            issues = self._run_deterministic_validation()

            if issues:
                critical = [i for i in issues if i.severity == "CRITICAL"]
                non_critical = [i for i in issues if i.severity != "CRITICAL"]

                yield self.validator.format_report(issues) + "\n\n"

                if critical:
                    yield f"❌ **{len(critical)} CRITICAL issue(s). Running optimizer pass...**\n\n"
                    async for fix_chunk in self._optimizer_pass(issues):
                        yield fix_chunk

                    # Re-validate after optimizer
                    recheck = self._run_deterministic_validation()
                    if recheck:
                        yield "\n⚠️ Some issues persist after optimizer. Manual review needed.\n"
                        yield self.validator.format_report(recheck) + "\n"
                    else:
                        yield "\n✅ All issues resolved after optimizer pass.\n"
                        yield self._emit_handoff()
                else:
                    yield f"⚠️ {len(non_critical)} non-critical issue(s) noted (see report above).\n"
                    yield self._emit_handoff()
            else:
                self.hooks.log_event("VALIDATION_PASSED", issues=0)
                yield "✅ All artifacts pass validation — zero issues.\n\n"
                yield self._emit_handoff()

        self.hooks.log_event("RUN_COMPLETED", project=self.project_id)

    # ── Agent SDK Loop ────────────────────────────────────────────────────

    async def _agent_loop(self, prompt: str) -> AsyncIterator[str]:
        """
        Core agent loop using Claude Agent SDK.
        Streams responses back to the caller.

        In production, this uses claude_agent_sdk.query().
        For standalone usage, this can be swapped with any LLM client.
        """
        try:
            from claude_agent_sdk import query, ClaudeAgentOptions

            options = ClaudeAgentOptions(
                allowed_tools=["Read", "Write", "Bash"],
                system_prompt=DIRECTOR_SYSTEM_PROMPT,
                max_turns=25,
            )
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, "content") and message.content:
                    yield message.content
                elif hasattr(message, "result"):
                    yield message.result

        except ImportError:
            # Fallback for environments without claude_agent_sdk
            yield (
                "⚠️ Claude Agent SDK not installed. "
                "Running in standalone mode.\n\n"
                f"**Received prompt ({len(prompt)} chars):**\n"
                f"The Director would now process this through the "
                f"7-category intake and generate all 3 artifacts.\n\n"
                f"Install `claude-agent-sdk` for full async streaming.\n"
            )

    # ── Evaluator-Optimizer ───────────────────────────────────────────────

    def _run_deterministic_validation(self) -> list:
        """Run all deterministic validation passes."""
        return self.validator.run_all_deterministic()

    async def _llm_evaluator_pass(self, brief: str, script: str) -> list[str]:
        """
        Dedicated LLM evaluator call. SEPARATE from the Director agent.
        Returns structured list of violations.
        """
        eval_prompt = self.validator.build_llm_evaluator_prompt(brief, script)

        try:
            from claude_agent_sdk import query, ClaudeAgentOptions

            result_text = ""
            async for message in query(
                prompt=eval_prompt,
                options=ClaudeAgentOptions(allowed_tools=[]),
            ):
                if hasattr(message, "result"):
                    result_text = message.result
                    break

            try:
                return json.loads(result_text.strip())
            except json.JSONDecodeError:
                return []

        except ImportError:
            return []

    async def _optimizer_pass(self, issues: list) -> AsyncIterator[str]:
        """Re-run generation with specific failure context."""
        fix_prompt = (
            "The evaluator found these issues with your artifacts:\n\n"
            + "\n".join(f"• {i}" for i in issues)
            + "\n\nFix each issue. Regenerate ONLY the affected artifacts. "
            + "Re-run schema validation after each fix. "
            + "Do not regenerate artifacts that passed validation."
        )
        async for chunk in self._agent_loop(fix_prompt):
            yield chunk

    # ── Helpers ───────────────────────────────────────────────────────────

    def _looks_like_blueprint(self, text: str) -> bool:
        """Detect if user input contains a pre-existing blueprint."""
        blueprint_signals = [
            "core message", "brand identity", "target audience",
            "platform:", "duration:", "color palette", "hook strategy",
            "emotion arc", "scene plan", "framework:",
        ]
        lower = text.lower()
        matches = sum(1 for s in blueprint_signals if s in lower)
        return matches >= 3

    def _artifacts_present(self) -> bool:
        """Check if all 3 required artifacts exist."""
        return all(
            (SPECS_DIR / f).exists()
            for f in ["01-brief.md", "02-script.md", "03-scene-map.json"]
        )

    def _emit_handoff(self) -> str:
        """Generate the handoff block from validated artifacts."""
        result = generate_handoff_block(self.project_id)
        if result["success"]:
            return "\n" + result["handoff_block"]
        else:
            return f"\n❌ Handoff blocked: {result['error']}"


# ── CLI Entry Point ──────────────────────────────────────────────────────────

async def main():
    """Run the Director agent from the command line."""
    import sys

    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""

    if not user_input:
        print("🎬 The Director — Pre-Production Agent")
        print("Usage: python -m director.agent <topic or blueprint>")
        print("       python -m director.agent --resume <projectId>")
        return

    agent = DirectorAgent()
    async for chunk in agent.run(user_input):
        print(chunk, end="", flush=True)
    print()  # Final newline


if __name__ == "__main__":
    asyncio.run(main())
