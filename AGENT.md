# 🎬 The Director — World-Class Production Build (v2.0)

> **Pipeline Position**: First agent called. No upstream dependencies.  
> **Slash Command**: `/director`  
> **Architecture**: State-machine intake → Pydantic-enforced contracts → Evaluator-optimizer loop → SDK-native streaming

---

## 1. ARCHITECTURAL TRUTH

The critical insight from Anthropic's own engineering: the most successful multi-agent systems use **three core principles** — simplicity in design, transparency in planning steps, and deep investment in the agent-computer interface (ACI). A wall of bullet-point rules is NOT an ACI. This Director has a **state machine intake loop**, **Pydantic-enforced contracts**, a **self-evaluation pass**, and **filesystem-native SDK configuration**. Every artifact is type-checked before it can leave the agent.

---

## 2. FILE STRUCTURE

The Claude Agent SDK is **filesystem-native** — skills live in `.claude/skills/`, commands in `.claude/commands/`, and project memory in `CLAUDE.md`.

```
the-director/
├── AGENT.md                           ← This file (architecture doc)
├── CLAUDE.md                          ← Agent persistent memory + project rules
├── .claude/
│   ├── commands/
│   │   └── director.md                ← /director slash command definition
│   └── skills/
│       ├── pre_production.md          ← Scene planning, intake, storyboard rules
│       └── script_copy.md            ← Word limits, hook science, PAS/BAB/AIDA
├── src/
│   ├── director/
│   │   ├── __init__.py
│   │   ├── agent.py                   ← DirectorAgent class (async SDK loop)
│   │   ├── models.py                  ← Pydantic contracts (THE source of truth)
│   │   ├── validator.py               ← ArtifactValidator (evaluator-optimizer)
│   │   ├── tools.py                   ← ACI-engineered tools
│   │   └── prompts.py                 ← System prompt (XML-structured)
│   └── pipeline/
│       ├── __init__.py
│       └── router.py                  ← Slash command router
├── specs/                             ← Director artifact output (auto-created)
├── tests/
│   └── test_director.py
└── knowledge/
    ├── pre_production.md              ← Full intake protocol + emotion table
    └── script_and_copy.md             ← Word limits, hook science, CTA ladder
```

---

## 3. IDENTITY

| Field | Value |
|-------|-------|
| **Professional Persona** | Executive Creative Director + Senior Producer + Narrative Strategist |
| **Operational Bias** | "Front-load every decision into the cheap phase. Every scene planned now is an 8-hour animation rework avoided later." |
| **Tone** | Structured, decisive, editorial. Uses tables and structured templates. Never rambles. |

---

## 4. SCOPE BOUNDARY (Hard Enforced)

| ✅ OWNS | ❌ NEVER TOUCHES |
|---------|------------------|
| 7-category client intake (state-machine tracked) | Visual design (→ `/designer`) |
| Brief Analysis synthesis → `specs/01-brief.md` | Motion physics, springs, easing (→ `/motion-architect`) |
| Framework selection (PAS / BAB / AIDA) with justification | Component selection: ValueCounter, ClipPathReveal (→ `/builder`) |
| Script with frame-level timing → `specs/02-script.md` | `.tsx` code (→ `/builder`) |
| Scene-map JSON contract → `specs/03-scene-map.json` | HTML prototypes (→ `/designer`) |
| Word count + compliance validation | |
| Evaluator-optimizer pass on all artifacts | |
| Handoff block generation after all gates pass | |

---

## 5. CONTRACT ENFORCEMENT

All artifacts are **type-checked at generation time** via Pydantic models in `src/director/models.py`. This replaces manual checklists with compile-time guarantees:

- `SceneModel` — enforces frame math, word counts, Hick's Law (≤4 info items), hook-not-logo
- `TransitionModel` — enforces narrative reason (not technique)
- `SceneMapModel` — enforces total duration, scene continuity, all transitions present
- `IntakeState` — enum-tracked state machine for 7-category completion

**If frame math is wrong → `ValidationError` is raised. No handoff possible.**

---

## 6. EVALUATOR-OPTIMIZER LOOP

After generating all 3 artifacts, a **separate LLM call** (not self-review) evaluates:

1. **Deterministic pass**: Pydantic schema validation on `scene-map.json`
2. **LLM evaluator pass**: Checks script narrative coherence, hook compliance, word limits
3. **If issues found** → `_optimizer_pass()` re-runs generation with specific failure context
4. **Only when clean** → handoff block is generated

---

## 7. THE 10/10 DIFFERENCES

| Dimension | Previous (1/10) | This Build (10/10) |
|-----------|-----------------|---------------------|
| **Contract enforcement** | Checklist in system prompt | Pydantic models — validation fails at generation |
| **Intake process** | Bullet-point instructions | `IntakeState` enum-tracked state machine |
| **Validation** | "Checklist to run" | `_evaluator_pass()` — separate LLM call |
| **Error recovery** | None | `_optimizer_pass()` re-runs with failure context |
| **SDK integration** | Generic prompt | Native `claude_agent_sdk.query()` async streaming |
| **File structure** | None | `.claude/skills/`, `.claude/commands/`, `CLAUDE.md` |
| **Frame math** | Manual checklist | `@model_validator` raises `ValidationError` |
| **System prompt** | Markdown headers | XML-structured ACI |
| **Handoff** | Static template | Generated dynamically from validated `SceneMapModel` |
| **Scene continuity** | Not checked | `validate_scene_continuity()` enforces contiguity |

---

## 8. PIPELINE COLLABORATION

| Agent | When | Contract |
|-------|------|----------|
| `/designer` | After Director handoff | Reads `01-brief.md`, `02-script.md`, `03-scene-map.json` → creates HTML prototypes |
| `/motion-architect` | After Designer | Reads scene-map + design spec → defines motion physics |
| `/builder` | After Motion Architect | Reads all upstream specs → writes `.tsx` code |
| `/inspector` | After Builder | Audits final output against all specs |

---

## 9. ACTIVATION

```bash
/director                          # Start fresh intake
/director [blueprint text]         # Provide GPT blueprint to skip intake
/director --resume [projectId]     # Resume incomplete session
```

---

## 10. SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Blank fields in brief | **0** |
| Scene-map schema errors | **0** |
| Downstream rework from Director errors | **0** |
| Intake categories covered | **7/7** |
| Evaluator pass rate (first attempt) | **>90%** |

---
*Synthesized by the Elite Factory Hub v3.0 — World-Class Architecture*
