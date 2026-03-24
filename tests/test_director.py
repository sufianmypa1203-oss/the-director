"""
The Director — Test Suite

Validates that the Pydantic contracts catch all the violations
they're supposed to catch, and that valid data passes clean.
"""
import json
import pytest
from pydantic import ValidationError

from director.models import (
    SceneModel, SceneMapModel, TransitionModel, CanvasModel,
    IntakeState, IntakeCategory, SceneRole, ColorTemp,
    FocalIsolation, NarrativeArc, Framework,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def make_scene(**overrides) -> dict:
    """Factory for valid scene data."""
    defaults = {
        "id": "scene-1",
        "name": "Hook",
        "role": "hook",
        "startFrame": 0,
        "endFrame": 120,
        "durationFrames": 120,
        "durationSeconds": 4.0,
        "emotionalBeat": "alarm",
        "emotionArc": "curiosity → shock",
        "colorTemperature": "warm",
        "focalPoint": "hero-number",
        "focalIsolation": "unique-scale",
        "heroText": "$4,652 leaked this year",
        "subText": "Subscriptions you forgot about",
        "prototypeFile": "Scene1_Hook.html",
        "maxInfoItems": 3,
    }
    defaults.update(overrides)
    return defaults


def make_scene_map(**overrides) -> dict:
    """Factory for valid scene map data."""
    scene1 = make_scene(id="scene-1", startFrame=0, endFrame=120, durationFrames=120, durationSeconds=4.0)
    scene2 = make_scene(
        id="scene-2", name="Reveal", role="build",
        startFrame=120, endFrame=240, durationFrames=120, durationSeconds=4.0,
        heroText="Where it goes", subText="Three apps draining your account",
        prototypeFile="Scene2_Reveal.html",
    )
    defaults = {
        "projectId": "subscription-creep",
        "compositionName": "SubscriptionCreep",
        "totalDuration": 240,
        "fps": 30,
        "canvas": {"width": 1080, "height": 1920},
        "narrativeArc": "shock-build-resolve",
        "framework": "PAS",
        "scenes": [scene1, scene2],
        "transitions": [
            {"from": "scene-1", "to": "scene-2", "narrativeReason": "From shock number to detailed breakdown of where money went"}
        ],
    }
    defaults.update(overrides)
    return defaults


# ─── Scene Validation Tests ──────────────────────────────────────────────────

class TestSceneModel:
    def test_valid_scene(self):
        scene = SceneModel(**make_scene())
        assert scene.id == "scene-1"
        assert scene.durationFrames == 120

    def test_frame_math_mismatch(self):
        with pytest.raises(ValidationError, match="durationFrames"):
            SceneModel(**make_scene(durationFrames=100))  # Should be 120

    def test_duration_seconds_mismatch(self):
        with pytest.raises(ValidationError, match="durationSeconds"):
            SceneModel(**make_scene(durationSeconds=5.0))  # Should be 4.0

    def test_scene_exceeds_5_seconds(self):
        with pytest.raises(ValidationError, match="exceeds"):
            SceneModel(**make_scene(endFrame=200, durationFrames=200, durationSeconds=6.6667))

    def test_hero_text_exceeds_7_words(self):
        with pytest.raises(ValidationError, match="7-word limit"):
            SceneModel(**make_scene(heroText="This hero text has way too many words in it"))

    def test_sub_text_exceeds_12_words(self):
        with pytest.raises(ValidationError, match="12-word limit"):
            SceneModel(**make_scene(
                subText="This sub text has way way way way too many words in the line here"
            ))

    def test_hook_with_logo_rejected(self):
        with pytest.raises(ValidationError, match="logo"):
            SceneModel(**make_scene(role="hook", focalPoint="brand logo placement"))

    def test_max_info_items_exceeds_4(self):
        with pytest.raises(ValidationError):
            SceneModel(**make_scene(maxInfoItems=5))

    def test_invalid_scene_id_format(self):
        with pytest.raises(ValidationError):
            SceneModel(**make_scene(id="bad-id"))


# ─── Scene Map Validation Tests ───────────────────────────────────────────────

class TestSceneMapModel:
    def test_valid_scene_map(self):
        smap = SceneMapModel(**make_scene_map())
        assert smap.projectId == "subscription-creep"
        assert len(smap.scenes) == 2

    def test_total_duration_mismatch(self):
        with pytest.raises(ValidationError, match="totalDuration"):
            SceneMapModel(**make_scene_map(totalDuration=999))

    def test_scene_continuity_gap(self):
        data = make_scene_map()
        data["scenes"][1]["startFrame"] = 130  # Gap of 10 frames
        data["scenes"][1]["endFrame"] = 250
        with pytest.raises(ValidationError, match="contiguous"):
            SceneMapModel(**data)

    def test_missing_transition(self):
        with pytest.raises(ValidationError, match="Missing transition"):
            SceneMapModel(**make_scene_map(transitions=[]))

    def test_first_scene_not_at_zero(self):
        data = make_scene_map()
        data["scenes"][0]["startFrame"] = 10
        data["scenes"][0]["endFrame"] = 130
        with pytest.raises(ValidationError):
            SceneMapModel(**data)

    def test_duplicate_scene_ids(self):
        data = make_scene_map()
        data["scenes"][1]["id"] = "scene-1"  # Duplicate
        data["transitions"] = [{"from": "scene-1", "to": "scene-1", "narrativeReason": "Duplicate test transition"}]
        with pytest.raises(ValidationError, match="Duplicate"):
            SceneMapModel(**data)


# ─── Transition Model Tests ──────────────────────────────────────────────────

class TestTransitionModel:
    def test_valid_transition(self):
        t = TransitionModel(**{
            "from": "scene-1",
            "to": "scene-2",
            "narrativeReason": "From shock number to detailed breakdown"
        })
        assert t.from_scene == "scene-1"

    def test_short_narrative_reason_rejected(self):
        with pytest.raises(ValidationError, match="at least 10 characters"):
            TransitionModel(**{
                "from": "scene-1",
                "to": "scene-2",
                "narrativeReason": "because"  # Too short
            })


# ─── Intake State Machine Tests ──────────────────────────────────────────────

class TestIntakeState:
    def test_initial_state(self):
        state = IntakeState()
        assert not state.is_complete()
        assert len(state.missing()) == 7
        assert state.progress_pct() == 0.0

    def test_complete_all_categories(self):
        state = IntakeState()
        for cat in IntakeCategory:
            state.complete_category(cat, {"test": True})
        assert state.is_complete()
        assert state.progress_pct() == 100.0
        assert len(state.missing()) == 0

    def test_partial_completion(self):
        state = IntakeState()
        state.complete_category(IntakeCategory.MESSAGE_PURPOSE, {"topic": "debt"})
        state.complete_category(IntakeCategory.AUDIENCE_PLATFORM, {"platform": "tiktok"})
        assert not state.is_complete()
        assert state.progress_pct() == pytest.approx(28.6, abs=0.1)
        assert len(state.missing()) == 5


# ─── JSON Schema Export Tests ────────────────────────────────────────────────

class TestSchemaExport:
    def test_json_schema_export(self):
        """Ensure JSON Schema can be exported for downstream tooling."""
        schema = SceneMapModel.to_json_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "projectId" in schema["properties"]
        assert "scenes" in schema["properties"]

    def test_to_example_valid(self):
        """Ensure the to_example() factory produces a valid model."""
        example = SceneMapModel.to_example()
        assert example.projectId == "example-project"
        assert len(example.scenes) == 1
        assert example.totalDuration == 90


# ─── Example Scene Map Validation ────────────────────────────────────────────

class TestExampleSceneMap:
    """Validates that the example scene-map.json stays valid as contracts evolve."""

    def test_example_scene_map_passes_validation(self):
        import pathlib
        example_path = pathlib.Path(__file__).parent.parent / "examples" / "subscription-creep" / "scene-map.json"
        if not example_path.exists():
            pytest.skip("Example scene-map.json not found")

        with open(example_path) as f:
            data = json.load(f)

        scene_map = SceneMapModel(**data)
        assert scene_map.projectId == "subscription-creep"
        assert len(scene_map.scenes) == 5
        assert scene_map.totalDuration == 450


# ─── Lifecycle Hooks Tests ───────────────────────────────────────────────────

class TestLifecycleHooks:
    def test_event_logging(self):
        from director.agent import LifecycleHooks
        hooks = LifecycleHooks()
        hooks.log_event("TEST_EVENT", key="value")
        assert len(hooks.events) == 1
        assert hooks.events[0]["event"] == "TEST_EVENT"
        assert hooks.events[0]["key"] == "value"

    def test_pre_hook_blocks(self):
        import asyncio
        from director.agent import LifecycleHooks
        hooks = LifecycleHooks()

        @hooks.on_pre_tool_use
        def block_all(tool_name, args):
            return False

        result = asyncio.get_event_loop().run_until_complete(
            hooks.run_pre_hooks("any_tool", {})
        )
        assert result is False

    def test_pre_hook_allows(self):
        import asyncio
        from director.agent import LifecycleHooks
        hooks = LifecycleHooks()

        @hooks.on_pre_tool_use
        def allow_all(tool_name, args):
            return True

        result = asyncio.get_event_loop().run_until_complete(
            hooks.run_pre_hooks("any_tool", {})
        )
        assert result is True


# ─── Director Agent Factory Tests ────────────────────────────────────────────

class TestDirectorAgent:
    def test_from_blueprint(self):
        from director.agent import DirectorAgent
        agent = DirectorAgent.from_blueprint(
            "Topic: debt. Platform: TikTok. Duration: 15s.",
            project_id="test-project",
        )
        assert agent.intake_state.blueprint_provided is True
        assert agent.project_id == "test-project"
        assert "_raw" in agent.intake_state.data

    def test_version(self):
        from director.agent import DirectorAgent, __version__
        assert DirectorAgent.version == __version__
        assert DirectorAgent.version == "2.0.0"


# ─── Reading Speed Validation Tests ──────────────────────────────────────────

class TestReadingSpeed:
    """Tests for the reading speed validator logic (in models, not file-based)."""

    def test_hero_at_word_limit(self):
        """7 words in hero text is at the limit — should pass."""
        scene = SceneModel(**make_scene(heroText="One two three four five six seven"))
        assert len(scene.heroText.split()) == 7

    def test_sub_at_word_limit(self):
        """12 words in sub text is at the limit — should pass."""
        scene = SceneModel(**make_scene(
            subText="One two three four five six seven eight nine ten eleven twelve"
        ))
        assert len(scene.subText.split()) == 12


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
