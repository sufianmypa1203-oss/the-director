"""
The Director — Pydantic Contracts (THE source of truth)

Every artifact is type-enforced at generation time. Incorrect frame math,
word count overflows, or logo-in-hook violations raise ValidationError
BEFORE the artifact can be written to disk.
"""
from __future__ import annotations
from enum import Enum
from typing import Annotated
from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class SceneRole(str, Enum):
    HOOK     = "hook"
    SHOCK    = "shock"
    AGITATE  = "agitate"
    BUILD    = "build"
    SOLUTION = "solution"
    RESOLVE  = "resolve"
    CTA      = "cta"


class ColorTemp(str, Enum):
    WARM    = "warm"
    COOL    = "cool"
    NEUTRAL = "neutral"


class FocalIsolation(str, Enum):
    UNIQUE_HUE      = "unique-hue"
    UNIQUE_SCALE     = "unique-scale"
    MOTION_CONTRAST  = "motion-contrast"


class NarrativeArc(str, Enum):
    SHOCK_BUILD_RESOLVE            = "shock-build-resolve"
    BEFORE_AFTER_BRIDGE            = "before-after-bridge"
    ATTENTION_INTEREST_DESIRE_ACT  = "attention-interest-desire-action"


class Framework(str, Enum):
    PAS  = "PAS"
    BAB  = "BAB"
    AIDA = "AIDA"


class EnergyLevel(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class IntakeCategory(str, Enum):
    MESSAGE_PURPOSE   = "message_purpose"
    AUDIENCE_PLATFORM = "audience_platform"
    BRAND_IDENTITY    = "brand_identity"
    EMOTION_TONE      = "emotion_tone"
    VISUAL_DIRECTION  = "visual_direction"
    COPY_TEXT         = "copy_text"
    HARD_CONSTRAINTS  = "hard_constraints"


# ─── Word Count Validators ────────────────────────────────────────────────────

def _enforce_word_limit(value: str, limit: int, field_name: str) -> str:
    """Raises ValueError if word count exceeds limit."""
    count = len(value.split())
    if count > limit:
        raise ValueError(
            f"'{field_name}' has {count} words — exceeds {limit}-word limit. "
            f"Condense or split. Text: '{value}'"
        )
    return value


# ─── Scene Model ──────────────────────────────────────────────────────────────

class SceneModel(BaseModel):
    """
    Represents a single scene in the scene map.
    All validation is enforced at construction time.
    """
    id:               str            = Field(pattern=r"^scene-\d+$")
    name:             str
    role:             SceneRole
    startFrame:       int            = Field(ge=0)
    endFrame:         int            = Field(ge=1)
    durationFrames:   int
    durationSeconds:  float
    emotionalBeat:    str
    emotionArc:       str            = Field(description="format: 'emotion → emotion'")
    colorTemperature: ColorTemp
    focalPoint:       str
    focalIsolation:   FocalIsolation
    heroText:         str
    subText:          str
    prototypeFile:    str            = Field(pattern=r"^Scene\d+_.+\.html$")
    maxInfoItems:     int            = Field(ge=1, le=4)

    @field_validator("heroText")
    @classmethod
    def hero_text_limit(cls, v: str) -> str:
        return _enforce_word_limit(v, 7, "heroText")

    @field_validator("subText")
    @classmethod
    def sub_text_limit(cls, v: str) -> str:
        return _enforce_word_limit(v, 12, "subText")

    @model_validator(mode="after")
    def validate_frame_math(self) -> "SceneModel":
        expected_duration = self.endFrame - self.startFrame
        if self.durationFrames != expected_duration:
            raise ValueError(
                f"[{self.id}] durationFrames ({self.durationFrames}) "
                f"≠ endFrame ({self.endFrame}) - startFrame ({self.startFrame}). "
                f"Expected: {expected_duration}"
            )
        expected_seconds = round(self.durationFrames / 30, 4)
        if abs(self.durationSeconds - expected_seconds) > 0.001:
            raise ValueError(
                f"[{self.id}] durationSeconds ({self.durationSeconds}) "
                f"≠ durationFrames/30 ({expected_seconds})"
            )
        if self.durationFrames > 150:
            raise ValueError(
                f"[{self.id}] Scene is {self.durationFrames} frames "
                f"({self.durationSeconds}s) — exceeds 5s/150-frame max. "
                f"Split this scene into two."
            )
        return self

    @model_validator(mode="after")
    def hook_not_logo(self) -> "SceneModel":
        logo_triggers = {"logo", "brand mark", "wordmark", "brand logo"}
        if self.role in (SceneRole.HOOK, SceneRole.SHOCK):
            fp_lower = self.focalPoint.lower()
            if any(trigger in fp_lower for trigger in logo_triggers):
                raise ValueError(
                    f"[{self.id}] Hook/shock focalPoint cannot be a logo. "
                    f"Lead with a number or pain point. Got: '{self.focalPoint}'"
                )
        return self


# ─── Transition Model ─────────────────────────────────────────────────────────

class TransitionModel(BaseModel):
    """
    Transition between two adjacent scenes.
    Director owns the REASON. Motion Architect owns the TECHNIQUE.
    """
    from_scene:      str = Field(alias="from", pattern=r"^scene-\d+$")
    to_scene:        str = Field(alias="to",   pattern=r"^scene-\d+$")
    narrativeReason: str = Field(
        min_length=10,
        description="WHY these scenes connect (narrative reason). "
                    "Motion Architect owns the technique — never specify HOW."
    )

    model_config = {"populate_by_name": True}


# ─── Canvas Model ─────────────────────────────────────────────────────────────

class CanvasModel(BaseModel):
    width:  int = Field(gt=0)
    height: int = Field(gt=0)


# ─── Scene Map — THE Pipeline Contract ────────────────────────────────────────

class SceneMapModel(BaseModel):
    """
    specs/03-scene-map.json — The contract every downstream agent reads.
    All downstream agents reference this file. It MUST be schema-valid.
    """
    projectId:       str = Field(
        pattern=r"^[a-z0-9-]+$",
        description="kebab-case project identifier"
    )
    compositionName: str = Field(
        pattern=r"^[A-Z][a-zA-Z0-9]+$",
        description="PascalCase Remotion composition name"
    )
    totalDuration:   int = Field(gt=0, description="Total frames")
    fps:             int = Field(default=30, frozen=True)
    canvas:          CanvasModel
    narrativeArc:    NarrativeArc
    framework:       Framework
    scenes:          list[SceneModel] = Field(min_length=1)
    transitions:     list[TransitionModel]

    @model_validator(mode="after")
    def validate_total_duration(self) -> "SceneMapModel":
        computed = sum(s.durationFrames for s in self.scenes)
        if computed != self.totalDuration:
            raise ValueError(
                f"totalDuration ({self.totalDuration}) ≠ "
                f"sum of scene durations ({computed}). "
                f"Fix the scene map or adjust totalDuration."
            )
        return self

    @model_validator(mode="after")
    def validate_scene_continuity(self) -> "SceneMapModel":
        for i in range(1, len(self.scenes)):
            prev = self.scenes[i - 1]
            curr = self.scenes[i]
            if curr.startFrame != prev.endFrame:
                raise ValueError(
                    f"[{curr.id}] startFrame ({curr.startFrame}) "
                    f"≠ previous scene endFrame ({prev.endFrame}). "
                    f"Scenes must be contiguous — no gaps or overlaps."
                )
        return self

    @model_validator(mode="after")
    def validate_first_scene_starts_at_zero(self) -> "SceneMapModel":
        if self.scenes and self.scenes[0].startFrame != 0:
            raise ValueError(
                f"First scene must start at frame 0, "
                f"got startFrame={self.scenes[0].startFrame}"
            )
        return self

    @model_validator(mode="after")
    def validate_all_transitions_present(self) -> "SceneMapModel":
        transition_pairs = {
            (t.from_scene, t.to_scene) for t in self.transitions
        }
        for i in range(len(self.scenes) - 1):
            pair = (self.scenes[i].id, self.scenes[i + 1].id)
            if pair not in transition_pairs:
                raise ValueError(
                    f"Missing transition: {pair[0]} → {pair[1]}. "
                    f"Every adjacent scene pair needs a narrativeReason."
                )
        return self

    @model_validator(mode="after")
    def validate_unique_scene_ids(self) -> "SceneMapModel":
        ids = [s.id for s in self.scenes]
        if len(ids) != len(set(ids)):
            dupes = [sid for sid in ids if ids.count(sid) > 1]
            raise ValueError(f"Duplicate scene IDs found: {set(dupes)}")
        return self

    # ── Export Methods ────────────────────────────────────────────────────

    @classmethod
    def to_json_schema(cls) -> dict:
        """Export JSON Schema for downstream tooling and documentation."""
        return cls.model_json_schema()

    @classmethod
    def to_example(cls) -> "SceneMapModel":
        """
        Generate a minimal valid SceneMapModel for testing and documentation.
        Useful for verifying contract integrity in CI/CD.
        """
        scene = SceneModel(
            id="scene-1", name="Example Hook", role="hook",
            startFrame=0, endFrame=90, durationFrames=90, durationSeconds=3.0,
            emotionalBeat="curiosity", emotionArc="neutral → engaged",
            colorTemperature="warm", focalPoint="hero-number",
            focalIsolation="unique-scale", heroText="Example hook text",
            subText="Supporting details here",
            prototypeFile="Scene1_Example.html", maxInfoItems=2,
        )
        transition = TransitionModel(**{
            "from": "scene-1", "to": "scene-1",
            "narrativeReason": "This is a single-scene example — no real transition",
        })
        return cls(
            projectId="example-project",
            compositionName="ExampleProject",
            totalDuration=90, fps=30,
            canvas=CanvasModel(width=1080, height=1920),
            narrativeArc="shock-build-resolve",
            framework="PAS",
            scenes=[scene],
            transitions=[],
        )


# ─── Intake State Machine ────────────────────────────────────────────────────

class IntakeState(BaseModel):
    """
    Tracks which of the 7 intake categories have been completed.
    The intake interview cannot conclude until is_complete() returns True.
    """
    completed:          set[IntakeCategory] = Field(default_factory=set)
    data:               dict[str, object]   = Field(default_factory=dict)
    blueprint_provided: bool = False

    def is_complete(self) -> bool:
        return self.completed == set(IntakeCategory)

    def missing(self) -> list[IntakeCategory]:
        return [c for c in IntakeCategory if c not in self.completed]

    def complete_category(self, category: IntakeCategory, extracted: dict) -> None:
        self.completed.add(category)
        self.data[category.value] = extracted

    def progress_pct(self) -> float:
        return round(len(self.completed) / len(IntakeCategory) * 100, 1)


# ─── Brief Model (01-brief.md validation) ────────────────────────────────────

class BrandIdentity(BaseModel):
    colors_use:    list[str] = Field(min_length=1, description="Hex codes to use")
    colors_avoid:  list[str] = Field(default_factory=list, description="Hex codes to avoid")
    dominant_60:   str
    secondary_30:  str
    accent_10:     str
    tone_words:    list[str] = Field(min_length=3, max_length=3)
    brand_is_not:  list[str] = Field(min_length=3, max_length=3)
    logo_path:     str | None = None
    logo_rules:    str = "Never in hook. Bottom corner in CTA only."
    fonts:         list[str] = Field(min_length=1)


class ScenePlanEntry(BaseModel):
    scene_name:       str
    frame_range:      str  # e.g., "0–120"
    duration_seconds: float
    purpose:          str
    color_temperature: ColorTemp
    color_reason:     str


class BriefModel(BaseModel):
    """
    Validates specs/01-brief.md structure.
    ZERO blank fields allowed.
    """
    topic:                 str = Field(min_length=1)
    core_message:          str = Field(min_length=1)
    core_emotion:          str = Field(min_length=1)
    emotion_arc:           str = Field(min_length=1)
    energy_level:          EnergyLevel
    platform:              str = Field(min_length=1)
    dimensions:            str = Field(pattern=r"^\d+×\d+$")
    fps:                   int = Field(default=30, frozen=True)
    duration_seconds:      float = Field(gt=0)
    duration_frames:       int   = Field(gt=0)
    brand:                 BrandIdentity
    scene_plan:            list[ScenePlanEntry] = Field(min_length=1)
    hook_strategy:         str = Field(min_length=1)
    cta:                   str = Field(min_length=1)
    framework:             Framework
    framework_justification: str = Field(min_length=10)
    primary_visual_concept: str = Field(min_length=1)
    focal_point_strategy:  str = Field(min_length=1)
    composition_name:      str = Field(pattern=r"^[A-Z][a-zA-Z0-9]+$")
    hard_constraints_include: list[str] = Field(default_factory=list)
    hard_constraints_avoid:   list[str] = Field(default_factory=list)
    compliance:            str | None = None
