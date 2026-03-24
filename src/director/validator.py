"""
The Director — ArtifactValidator (Evaluator-Optimizer Loop)

A SEPARATE evaluation pass that validates generated artifacts.
This is NOT the same agent checking its own work — it's a dedicated
validator with deterministic (Pydantic) and LLM-based checks.
"""
from __future__ import annotations
import json
from pathlib import Path
from pydantic import ValidationError

from .models import SceneMapModel


SPECS_DIR = Path("specs")


class ValidationIssue:
    """Structured validation issue with severity and fix suggestion."""

    def __init__(self, severity: str, source: str, message: str, fix_hint: str = ""):
        self.severity = severity   # CRITICAL / HIGH / MEDIUM
        self.source = source       # SCHEMA / SCRIPT / BRIEF / CONTINUITY
        self.message = message
        self.fix_hint = fix_hint

    def __str__(self) -> str:
        prefix = f"[{self.severity}][{self.source}]"
        hint = f" → Fix: {self.fix_hint}" if self.fix_hint else ""
        return f"{prefix} {self.message}{hint}"

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "source": self.source,
            "message": self.message,
            "fix_hint": self.fix_hint,
        }


class ArtifactValidator:
    """
    Two-phase validation:
    1. Deterministic (Pydantic schema) — no LLM needed
    2. Semantic (LLM evaluator call) — narrative coherence, compliance checks

    Returns structured issues that feed directly into the optimizer pass.
    """

    def __init__(self, specs_dir: Path | None = None):
        self.specs_dir = specs_dir or SPECS_DIR

    # ── Phase 1: Deterministic Schema Validation ──────────────────────────

    def validate_scene_map_schema(self) -> list[ValidationIssue]:
        """
        Validates specs/03-scene-map.json against SceneMapModel.
        Returns structured issues with fix hints.
        """
        issues: list[ValidationIssue] = []
        scene_map_path = self.specs_dir / "03-scene-map.json"

        if not scene_map_path.exists():
            issues.append(ValidationIssue(
                severity="CRITICAL",
                source="SCHEMA",
                message="specs/03-scene-map.json does not exist",
                fix_hint="Generate the scene map before running validation",
            ))
            return issues

        try:
            raw = json.loads(scene_map_path.read_text())
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                severity="CRITICAL",
                source="SCHEMA",
                message=f"Invalid JSON in scene-map: {e}",
                fix_hint="Fix JSON syntax errors and re-validate",
            ))
            return issues

        try:
            SceneMapModel(**raw)
        except ValidationError as e:
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                issues.append(ValidationIssue(
                    severity="CRITICAL" if "frame" in loc.lower() else "HIGH",
                    source="SCHEMA",
                    message=f"{loc}: {err['msg']}",
                    fix_hint=f"Fix field '{loc}' in scene-map.json",
                ))

        return issues

    # ── Phase 2: Artifact Existence & Completeness ────────────────────────

    def validate_artifacts_exist(self) -> list[ValidationIssue]:
        """Check that all 3 required artifacts exist."""
        issues: list[ValidationIssue] = []
        required = ["01-brief.md", "02-script.md", "03-scene-map.json"]

        for filename in required:
            path = self.specs_dir / filename
            if not path.exists():
                issues.append(ValidationIssue(
                    severity="CRITICAL",
                    source="ARTIFACT",
                    message=f"Missing artifact: specs/{filename}",
                    fix_hint=f"Generate {filename} before running handoff",
                ))
            elif path.stat().st_size < 50:
                issues.append(ValidationIssue(
                    severity="HIGH",
                    source="ARTIFACT",
                    message=f"Artifact specs/{filename} appears empty or too small ({path.stat().st_size} bytes)",
                    fix_hint=f"Regenerate {filename} with complete content",
                ))

        return issues

    def validate_brief_completeness(self) -> list[ValidationIssue]:
        """Check that the brief has no blank required fields."""
        issues: list[ValidationIssue] = []
        brief_path = self.specs_dir / "01-brief.md"

        if not brief_path.exists():
            return issues  # Already caught by artifacts_exist

        content = brief_path.read_text()
        # Normalize: strip markdown bold/italic, case-insensitive
        content_normalized = content.replace("**", "").replace("##", "").replace("#", "")

        # Check for common blank-field patterns
        required_sections = [
            ("topic:", "topic"),
            ("core message:", "core_message"),
            ("core emotion:", "core_emotion"),
            ("emotion arc:", "emotion_arc"),
            ("colors use:", "brand_colors"),
            ("hook strategy:", "hook_strategy"),
            ("cta:", "cta"),
            ("framework:", "framework"),
            ("composition name:", "composition_name"),
        ]

        content_lower = content_normalized.lower()

        for marker, field_name in required_sections:
            if marker in content_lower:
                # Check if the line after the marker is empty or just whitespace
                idx = content_lower.index(marker)
                line = content_normalized[idx:].split("\n")[0]
                value_part = line.split(":", 1)[1].strip() if ":" in line else ""
                if not value_part or value_part.lower() in ("(none)", "tbd", "todo", "[]"):
                    issues.append(ValidationIssue(
                        severity="HIGH",
                        source="BRIEF",
                        message=f"Blank field in brief: '{marker}'",
                        fix_hint=f"Fill in the {field_name} field — no blanks allowed",
                    ))
            else:
                issues.append(ValidationIssue(
                    severity="HIGH",
                    source="BRIEF",
                    message=f"Missing section in brief: '{marker}'",
                    fix_hint=f"Add the {field_name} section to 01-brief.md",
                ))

        return issues

    # ── Phase 3: Script Validation (Deterministic Checks) ─────────────────

    def validate_script_deterministic(self) -> list[ValidationIssue]:
        """Check script for deterministic violations (vague numbers, missing sections)."""
        issues: list[ValidationIssue] = []
        script_path = self.specs_dir / "02-script.md"

        if not script_path.exists():
            return issues

        content = script_path.read_text()
        content_lower = content.lower()

        # Check for vague numbers
        vague_patterns = [
            "hundreds of", "thousands of", "millions of",
            "a lot of", "many people", "some money",
            "significant amount", "large number",
        ]
        for pattern in vague_patterns:
            if pattern in content_lower:
                issues.append(ValidationIssue(
                    severity="HIGH",
                    source="SCRIPT",
                    message=f"Vague amount detected: '{pattern}'",
                    fix_hint="Replace with specific number (e.g., '$847' not 'hundreds')",
                ))

        # Check hook doesn't start with logo
        if "scene 1" in content_lower or "scene-1" in content_lower:
            first_scene_idx = min(
                content_lower.find("scene 1") if "scene 1" in content_lower else len(content),
                content_lower.find("scene-1") if "scene-1" in content_lower else len(content),
            )
            # Find next scene boundary
            next_scene = content_lower.find("scene 2", first_scene_idx + 1)
            if next_scene == -1:
                next_scene = content_lower.find("scene-2", first_scene_idx + 1)
            if next_scene == -1:
                next_scene = len(content)

            hook_section = content_lower[first_scene_idx:next_scene]
            if "logo" in hook_section and "hero" in hook_section:
                issues.append(ValidationIssue(
                    severity="CRITICAL",
                    source="SCRIPT",
                    message="Hook scene appears to lead with logo",
                    fix_hint="Lead hook with number or pain point, never logo",
                ))

        return issues

    # ── Phase 4: Reading Speed Validation ─────────────────────────────────

    def validate_reading_speed(self) -> list[ValidationIssue]:
        """
        Validates reading speed: max 8 words per 3 seconds of screen time.
        Human reading speed is 120-160 WPM. At 3s, max 8 words on screen.
        Reads scene-map and checks heroText + subText combined per scene.
        """
        issues: list[ValidationIssue] = []
        scene_map_path = self.specs_dir / "03-scene-map.json"

        if not scene_map_path.exists():
            return issues

        try:
            raw = json.loads(scene_map_path.read_text())
        except (json.JSONDecodeError, OSError):
            return issues

        scenes = raw.get("scenes", [])
        for scene in scenes:
            scene_id = scene.get("id", "unknown")
            duration_s = scene.get("durationSeconds", 0)
            hero = scene.get("heroText", "")
            sub = scene.get("subText", "")

            total_words = len(hero.split()) + len(sub.split())
            if duration_s > 0:
                # Words per 3 seconds
                words_per_3s = total_words / (duration_s / 3.0)
                if words_per_3s > 8:
                    issues.append(ValidationIssue(
                        severity="HIGH",
                        source="READING_SPEED",
                        message=(
                            f"[{scene_id}] {total_words} words in {duration_s}s "
                            f"= {words_per_3s:.1f} words/3s (max: 8)"
                        ),
                        fix_hint="Reduce on-screen text or increase scene duration",
                    ))

        return issues

    # ── Phase 5: Duration Distribution ────────────────────────────────────

    def validate_duration_distribution(self) -> list[ValidationIssue]:
        """
        Warns if any single scene takes >60% of total duration.
        Poor pacing = bad viewer retention.
        """
        issues: list[ValidationIssue] = []
        scene_map_path = self.specs_dir / "03-scene-map.json"

        if not scene_map_path.exists():
            return issues

        try:
            raw = json.loads(scene_map_path.read_text())
        except (json.JSONDecodeError, OSError):
            return issues

        total = raw.get("totalDuration", 0)
        if total == 0:
            return issues

        scenes = raw.get("scenes", [])
        for scene in scenes:
            scene_id = scene.get("id", "unknown")
            duration = scene.get("durationFrames", 0)
            pct = (duration / total) * 100
            if pct > 60:
                issues.append(ValidationIssue(
                    severity="MEDIUM",
                    source="PACING",
                    message=(
                        f"[{scene_id}] takes {pct:.0f}% of total duration "
                        f"({duration}/{total} frames)"
                    ),
                    fix_hint="Consider splitting into two scenes for better pacing",
                ))

        return issues

    # ── Master Validation ─────────────────────────────────────────────────

    def run_all_deterministic(self) -> list[ValidationIssue]:
        """Run all deterministic validation passes. Returns combined issues."""
        all_issues: list[ValidationIssue] = []
        all_issues.extend(self.validate_artifacts_exist())
        all_issues.extend(self.validate_brief_completeness())
        all_issues.extend(self.validate_script_deterministic())
        all_issues.extend(self.validate_scene_map_schema())
        all_issues.extend(self.validate_reading_speed())
        all_issues.extend(self.validate_duration_distribution())
        all_issues.extend(self.validate_cross_references())
        return all_issues

    # ── Phase 7: Cross-Reference Validation (Upgrade 2) ───────────────────

    def validate_cross_references(self) -> list[ValidationIssue]:
        """
        Cross-validates scene-map ↔ brief ↔ script artifacts.
        Checks that scene IDs, composition name, and scene plans align.
        """
        issues: list[ValidationIssue] = []
        scene_map_path = self.specs_dir / "03-scene-map.json"
        brief_path = self.specs_dir / "01-brief.md"

        if not scene_map_path.exists():
            return issues

        try:
            raw = json.loads(scene_map_path.read_text())
        except (json.JSONDecodeError, OSError):
            return issues

        scene_ids = [s.get("id", "") for s in raw.get("scenes", [])]
        composition_name = raw.get("compositionName", "")

        # Cross-check: brief composition name matches scene-map
        if brief_path.exists():
            brief_content = brief_path.read_text().lower()
            if composition_name and composition_name.lower() not in brief_content:
                issues.append(ValidationIssue(
                    severity="MEDIUM",
                    source="CROSS_REF",
                    message=f"compositionName '{composition_name}' not found in brief",
                    fix_hint="Ensure brief's Composition Name matches scene-map compositionName",
                ))

        # Cross-check: script references all scene IDs
        script_path = self.specs_dir / "02-script.md"
        if script_path.exists():
            script_content = script_path.read_text().lower()
            for sid in scene_ids:
                if sid.lower() not in script_content and sid.replace("-", " ").lower() not in script_content:
                    issues.append(ValidationIssue(
                        severity="MEDIUM",
                        source="CROSS_REF",
                        message=f"Scene '{sid}' in scene-map but not referenced in script",
                        fix_hint=f"Add {sid} section to 02-script.md",
                    ))

        return issues

    def has_critical_issues(self, issues: list[ValidationIssue]) -> bool:
        return any(i.severity == "CRITICAL" for i in issues)

    def format_report(self, issues: list[ValidationIssue]) -> str:
        """Format issues into a human-readable validation report."""
        if not issues:
            return "✅ All validations passed. Artifacts are clean."

        report_lines = [
            f"## ⚠️ Validation Report — {len(issues)} Issue(s) Found\n",
            f"| Severity | Source | Issue | Fix |",
            f"|----------|--------|-------|-----|",
        ]
        for i in sorted(issues, key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}.get(x.severity, 3)):
            report_lines.append(
                f"| **{i.severity}** | {i.source} | {i.message} | {i.fix_hint} |"
            )

        critical_count = sum(1 for i in issues if i.severity == "CRITICAL")
        if critical_count:
            report_lines.append(f"\n❌ **{critical_count} CRITICAL issue(s) must be fixed before handoff.**")
        else:
            report_lines.append(f"\n⚠️ **{len(issues)} non-critical issue(s). Review recommended before handoff.**")

        return "\n".join(report_lines)

    # ── LLM Evaluator Prompt Builder ──────────────────────────────────────

    def build_llm_evaluator_prompt(self, brief: str, script: str) -> str:
        """
        Builds the prompt for the LLM evaluator pass.
        This is a SEPARATE call — not the Director reviewing its own work.
        """
        return f"""You are a strict script validator. Evaluate this script against the brief constraints.
Return ONLY a JSON array of violation strings. Return [] if no violations found.

BRIEF (truncated):
{brief[:2000]}

SCRIPT (truncated):
{script[:3000]}

CHECK FOR:
1. Hook leads with logo (violation if true)
2. Any hero text exceeding 7 words
3. Any sub text exceeding 12 words
4. Vague amounts instead of specific numbers ("hundreds" instead of "$847")
5. Script does NOT work on mute (text doesn't tell full story alone)
6. CTA is high-friction (requires multiple steps)
7. Compliance violations (unverified claims, superlatives, etc.)
8. Any scene missing frame ranges
9. Reading speed violations (>8 words per 3 seconds of screen time)

Output format: ["violation 1", "violation 2"] or []
Only output the JSON array — no explanation, no markdown."""
