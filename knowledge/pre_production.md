# 📋 Pre-Production Knowledge Base (v2.0 — World-Class)
## *The Director's Core Reference — Machine-Grade Precision*

> This is not a cheat sheet. This is the deterministic ruleset that feeds
> the Pydantic contracts in `models.py`. Every rule here has a corresponding
> validator that will raise `ValidationError` if violated.

---

## The 7-Category Intake State Machine

The intake is tracked via `IntakeState` in `models.py`. Each category is an
enum value. The intake cannot conclude until `state.is_complete()` returns `True`.

### Category 1: `message_purpose`
**Feeds**: Script  
**Extract**: The ONE thing, the problem, the video type  
**If missing**: "If the viewer remembers only ONE thing, what should it be?"

### Category 2: `audience_platform`
**Feeds**: All agents  
**Extract**: Target viewer, platform, aspect ratio, duration  
**If missing**: **ALWAYS ASK** — platform determines canvas, duration, pacing, layout

| Platform | Canvas | Duration | Pacing | Layout |
|----------|--------|----------|--------|--------|
| TikTok/Reels | 1080×1920 | 15–30s | Fast | Vertical hierarchy |
| YouTube | 1920×1080 | 15–30s | Moderate | Horizontal flow |
| Twitter | 1920×1080 | 6–15s | Fast | Strong hook |
| LinkedIn | 1920×1080 | 15–30s | Professional | Data-forward |
| Square | 1080×1080 | 6–15s | Centered | Compressed |

### Category 3: `brand_identity`
**Feeds**: Designer  
**Extract**: Colors USE/AVOID (hex), 60-30-10 split, logo rules, fonts, 3 tone words, 3 "NOT" words  
**If missing**: **ALWAYS ASK. NEVER GUESS.**

### Category 4: `emotion_tone`
**Feeds**: Designer + Motion Architect  
**Extract**: Core emotion (ONE word), emotion arc (start→end), energy level  
**Inference table** (when not stated):

| Topic | Inferred Emotion | Arc |
|-------|-----------------|-----|
| Debt / overspending | Anxiety | worry → relief |
| Savings / growth | Aspiration | curiosity → confidence |
| Feature explainer | Education | confusion → clarity |
| Hidden costs | Alarm | comfort → shock → action |

### Category 5: `visual_direction`
**Feeds**: Designer  
**Extract**: Style approach, references, existing assets  
**Rejection**: "card grid" / "dashboard" → redirect to typographic/editorial

### Category 6: `copy_text`
**Feeds**: Script  
**Extract**: Exact text/numbers, hook strategy, CTA, compliance  
**Rule**: Specific numbers only ("$847" not "hundreds")

### Category 7: `hard_constraints`
**Feeds**: All agents  
**Extract**: Must-include, must-avoid, deadline, approval chain

---

## Scene Planning Rules (Enforced by Pydantic)

| Rule | Validator | Error Behavior |
|------|-----------|----------------|
| No scene > 150 frames | `SceneModel.validate_frame_math()` | `ValidationError` — auto-split required |
| ≤ 4 info items per scene | `SceneModel.maxInfoItems` max=4 | `ValidationError` — cut items or split scene |
| `durationFrames = endFrame - startFrame` | `SceneModel.validate_frame_math()` | `ValidationError` — math must be exact |
| `durationSeconds = durationFrames / 30` | `SceneModel.validate_frame_math()` | `ValidationError` — derives from frames |
| First scene starts at frame 0 | `SceneMapModel.validate_first_scene_starts_at_zero()` | `ValidationError` |
| Contiguous scenes (no gaps) | `SceneMapModel.validate_scene_continuity()` | `ValidationError` — `endFrame[N] == startFrame[N+1]` |
| `totalDuration = sum(durationFrames)` | `SceneMapModel.validate_total_duration()` | `ValidationError` |
| All scene IDs unique | `SceneMapModel.validate_unique_scene_ids()` | `ValidationError` |
| All adjacent pairs have transitions | `SceneMapModel.validate_all_transitions_present()` | `ValidationError` |
| Hook focal point ≠ logo | `SceneModel.hook_not_logo()` | `ValidationError` |
| Hero text ≤ 7 words | `SceneModel.hero_text_limit()` | `ValidationError` |
| Sub text ≤ 12 words | `SceneModel.sub_text_limit()` | `ValidationError` |

---

## Emotion → Design Mapping Table

| Emotion | Color Temperature | Motion Physics | Typography | Shape Language |
|---------|-------------------|----------------|------------|----------------|
| Trust | Cool blues, warm whites | Slow springs, gentle settle | Serif or clean sans, medium weight | Circles, rounded corners |
| Urgency | Warm reds, saturated | Snappy springs, fast cuts | Bold sans, tight tracking | Triangles, diagonals |
| Calm | Cool neutrals, desaturated | Slow, floaty, long ease | Light weight, wide tracking | Organic curves |
| Power | High contrast, dark | Impact springs, sharp stops | Ultra bold, condensed | Squares, strong verticals |
| Joy | Bright, saturated, warm | Bouncy springs, playful | Rounded sans, varied weight | Circles, organic |
| Anxiety | Dark, desaturated, red accents | Jittery, unsettled | Tight tracking, condensed | Jagged, irregular |
| Confidence | Warm neutrals, gold accents | Measured, deliberate | Strong weight contrast | Clean geometry |

> **Scope note**: The Director maps emotion to design implications in the brief.
> The Designer and Motion Architect APPLY them. The Director never specifies
> spring constants, easing functions, or component choices.

---

## Framework Selection Logic (Enforced by `Framework` enum)

| Emotional Driver | Framework | Scene Structure |
|-----------------|-----------|-----------------|
| Pain/fear (debt, hidden costs) | **PAS** | Scene 1-2: Problem, 3-4: Agitate, 5-6: Solve |
| Aspiration (savings, growth) | **BAB** | Scene 1-2: Before, 3-4: After, 5-6: Bridge |
| Education (explainer, features) | **AIDA** | Scene 1: Attention, 2-3: Interest, 4-5: Desire, 6: Action |

---

## Duration → Max Text Cards

| Duration | Max Cards |
|----------|-----------|
| 6s | 2 |
| 15s | 5–6 |
| 20s | 6–8 |
| 30s | 8–10 |
| 40s | 10–12 |
