"""
The Director — ACI-Engineered Tools

These tools follow Anthropic's Agent-Computer Interface (ACI) principles:
- Each tool does ONE thing with CLEAR boundaries
- Error messages are actionable (tell the agent what to fix)
- Tool descriptions match how Claude actually uses tools
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .models import SceneMapModel, IntakeState, IntakeCategory
from .validator import ArtifactValidator, ValidationIssue


SPECS_DIR = Path("specs")


# ─── Intake Tools ─────────────────────────────────────────────────────────────

def check_intake_status(state: IntakeState) -> dict[str, Any]:
    """
    Returns current intake completion status.
    Use this to determine which categories still need to be covered.
    """
    return {
        "complete": state.is_complete(),
        "progress": f"{state.progress_pct()}%",
        "completed_categories": [c.value for c in state.completed],
        "missing_categories": [c.value for c in state.missing()],
        "blueprint_provided": state.blueprint_provided,
    }


def complete_intake_category(
    state: IntakeState,
    category: str,
    extracted_data: dict,
) -> dict[str, Any]:
    """
    Marks an intake category as complete with extracted data.
    Returns updated status.

    Args:
        category: One of: message_purpose, audience_platform, brand_identity,
                  emotion_tone, visual_direction, copy_text, hard_constraints
        extracted_data: The structured data extracted for this category
    """
    try:
        cat = IntakeCategory(category)
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid category: '{category}'. "
                     f"Valid: {[c.value for c in IntakeCategory]}",
        }

    state.complete_category(cat, extracted_data)
    return {
        "success": True,
        "category": category,
        "progress": f"{state.progress_pct()}%",
        "remaining": [c.value for c in state.missing()],
    }


# ─── Artifact Tools ──────────────────────────────────────────────────────────

def write_artifact(filename: str, content: str) -> dict[str, Any]:
    """
    Writes an artifact to the specs/ directory.
    Valid filenames: 01-brief.md, 02-script.md, 03-scene-map.json

    For scene-map.json, content must be valid JSON that passes
    SceneMapModel validation. The tool will reject invalid schemas.
    """
    valid_files = {"01-brief.md", "02-script.md", "03-scene-map.json"}
    if filename not in valid_files:
        return {
            "success": False,
            "error": f"Invalid artifact filename: '{filename}'. "
                     f"Valid: {valid_files}",
        }

    SPECS_DIR.mkdir(exist_ok=True)
    filepath = SPECS_DIR / filename

    # Special handling for scene-map: validate BEFORE writing
    if filename == "03-scene-map.json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON: {e}. Fix the JSON and retry.",
            }

        try:
            validated = SceneMapModel(**data)
        except Exception as e:
            return {
                "success": False,
                "error": f"Schema validation failed:\n{e}\n\n"
                         f"Fix the issues above and retry. "
                         f"Do NOT write invalid scene maps.",
            }

        # Write the validated (and potentially normalized) version
        content = validated.model_dump_json(indent=2, by_alias=True)

    filepath.write_text(content, encoding="utf-8")
    return {
        "success": True,
        "path": str(filepath),
        "size_bytes": filepath.stat().st_size,
    }


# ─── Validation Tools ────────────────────────────────────────────────────────

def run_validation() -> dict[str, Any]:
    """
    Runs ALL deterministic validation passes on generated artifacts.
    Returns structured issues with severity, source, and fix hints.

    Call this BEFORE generating the handoff block.
    If any CRITICAL issues exist, handoff is blocked.
    """
    validator = ArtifactValidator()
    issues = validator.run_all_deterministic()

    return {
        "passed": len(issues) == 0,
        "total_issues": len(issues),
        "critical_count": sum(1 for i in issues if i.severity == "CRITICAL"),
        "handoff_blocked": validator.has_critical_issues(issues),
        "issues": [i.to_dict() for i in issues],
        "report": validator.format_report(issues),
    }


# ─── Handoff Tools ───────────────────────────────────────────────────────────

def generate_handoff_block(project_id: str | None = None) -> dict[str, Any]:
    """
    Generates the handoff block for /designer.
    Will REFUSE to generate if validation has critical issues.
    Always run run_validation() first.
    """
    # Pre-flight check
    validator = ArtifactValidator()
    issues = validator.run_all_deterministic()

    if validator.has_critical_issues(issues):
        return {
            "success": False,
            "error": "Cannot generate handoff — CRITICAL issues exist.",
            "report": validator.format_report(issues),
        }

    # Extract projectId from scene-map if not provided
    scene_map_path = SPECS_DIR / "03-scene-map.json"
    if scene_map_path.exists() and not project_id:
        data = json.loads(scene_map_path.read_text())
        project_id = data.get("projectId", "unknown")

    pid = project_id or "unknown"

    # Build unresolved risks from non-critical issues
    risks = [i.message for i in issues if i.severity != "CRITICAL"]
    risks_text = ", ".join(risks) if risks else "None"

    handoff = f"""## 📦 Handoff
| Field | Value |
|-------|-------|
| **Project** | `{pid}` |
| **Phase completed** | Director |
| **Artifacts created** | `specs/01-brief.md`, `specs/02-script.md`, `specs/03-scene-map.json` |
| **Validations passed** | ✅ 7-category intake ✅ brief complete ✅ script validated ✅ scene-map schema valid ✅ evaluator pass |
| **Unresolved risks** | {risks_text} |
| **Next agent** | `/designer` |

### Prompt for /designer:
> I'm working on `{pid}`. Director phase is locked.
> Upstream specs are in `specs/`:
> - `01-brief.md` — locked brief: brand identity, emotion arc, scene plan
> - `02-script.md` — approved script: exact on-screen text per scene
> - `03-scene-map.json` — machine-readable contract (read this first)
>
> Run `/designer` to create HTML prototypes and visual spec for each scene."""

    return {
        "success": True,
        "handoff_block": handoff,
        "project_id": pid,
        "non_critical_risks": risks,
    }


# ─── Tool Registry ───────────────────────────────────────────────────────────

DIRECTOR_TOOLS = {
    "check_intake_status": check_intake_status,
    "complete_intake_category": complete_intake_category,
    "write_artifact": write_artifact,
    "run_validation": run_validation,
    "generate_handoff_block": generate_handoff_block,
}
