# ✍️ Script & Copy Knowledge Base (v2.0 — World-Class)
## *The Director's Copywriting Reference — Validator-Backed*

> Every word count limit in this file has a corresponding `@field_validator`
> in `models.py`. Violations raise `ValidationError` before the artifact
> can be written to disk. This is not a suggestion — it's a compile gate.

---

## Word Count Limits (Enforced by Pydantic)

| Element | Max Words | Max Lines | Validator |
|---------|-----------|-----------|-----------|
| Hero headline | 7 | 1 | `SceneModel.hero_text_limit()` |
| Sub-headline | 12 | 2 | `SceneModel.sub_text_limit()` |
| Body overlay | 5 | 1 | Manual check in `ArtifactValidator` |
| Label/data | 4 | 1 | Manual check in `ArtifactValidator` |

### Reading Speed Rule
- Human reading speed: **120–160 wpm**
- At 3 seconds of screen time: **max 8 words on screen**
- Always round DOWN, not up

---

## Hook Science

### The First 3 Seconds Rule
The hook determines stay-or-scroll. It MUST:
1. **Lead with a number or pain point** — NEVER a logo (enforced by `hook_not_logo()` validator)
2. **Create an information gap** — make the viewer need to know more
3. **Be visually distinct** — the hook scene should feel different from the rest

### Hook Types (Ranked for Finance Content)

| Rank | Type | Example | When |
|------|------|---------|------|
| 1 | **Shock Number** | "$4,652 leaked" | Surprising statistic |
| 2 | **Pain Question** | "Where did your money go?" | Common frustration |
| 3 | **Counter-Intuitive** | "Saving money is costing you" | Challenging assumptions |
| 4 | **Time Pressure** | "You have 48 hours" | Real urgency |

### Hook Anti-Patterns (Hard Rejected by Validator)
- ❌ Logo first (`hook_not_logo()` raises `ValidationError`)
- ❌ Generic greeting ("Hey there!")
- ❌ Feature announcement ("Introducing our new...")
- ❌ Vague promise ("This will change your life")

---

## Framework Selection (Backed by `Framework` Enum)

### PAS — Problem → Agitate → Solve
**Trigger**: Pain/fear (debt, overspending, hidden costs)

```
Scene 1-2: PROBLEM → State the pain with a specific number
Scene 3-4: AGITATE → Make it worse — compounding cost, time lost
Scene 5-6: SOLVE   → Present solution as relief + CTA
```

### BAB — Before → After → Bridge
**Trigger**: Aspiration (savings, growth, better life)

```
Scene 1-2: BEFORE → Current painful state
Scene 3-4: AFTER  → Desired future state
Scene 5-6: BRIDGE → How to get there + CTA
```

### AIDA — Attention → Interest → Desire → Action
**Trigger**: Education (how it works, feature explainer)

```
Scene 1:   ATTENTION → Hook with surprising fact
Scene 2-3: INTEREST  → Build understanding
Scene 4-5: DESIRE    → Show benefits
Scene 6:   ACTION    → Clear CTA
```

---

## Finance-Specific Trigger Words

### High-Impact (Use)
| Category | Words |
|----------|-------|
| Pain | leaked, drained, hidden, silent, forgotten, bleeding |
| Scale | every month, per year, compounds, adds up, over time |
| Action | track, cancel, reclaim, take control, start |
| Proof | actual, real, verified, your, specific |

### Low-Impact (Avoid)
| Category | Words |
|----------|-------|
| Vague | some, many, a lot, various, multiple |
| Weak | might, could, maybe, possibly, perhaps |
| Corporate | leverage, synergy, optimize, solution, platform |
| Overused | revolutionary, game-changing, innovative, disruptive |

> **Validator note**: `ArtifactValidator.validate_script_deterministic()` scans
> for vague patterns like "hundreds of" and flags them as HIGH severity.

---

## The Silent-First Rule

**Every video must work on mute.** Validation test:
- [ ] What the problem is → conveyed via text?
- [ ] How big the problem is → specific number displayed visually?
- [ ] What the solution is → shown via text?
- [ ] What to do next (CTA) → readable on screen?

If any answer is "no" → script needs more visual text.

---

## CTA Ladder

| Level | CTA | When |
|-------|-----|------|
| 1 (Lowest) | "Follow for more" | Awareness |
| 2 | "Link in bio" | Social media |
| 3 | "Try it free" | Product demos |
| 4 | "Sign up today" | Direct conversion |
| 5 (Highest) | "Start your trial" | High-intent |

**Default for Data Explainers**: Level 2–3 (low friction)

---

## Script Template (Per Scene)

```markdown
## Scene [N]: [Name]
**Frames:** [start]–[end] ([duration]s)

### On-Screen Text
- **Hero:** "[exact text]"           ← ≤ 7 words (validator-enforced)
- **Sub:** "[exact text]"            ← ≤ 12 words (validator-enforced)
- **Labels:** "[label 1]", "[label 2]" ← ≤ 4 words each

### Numbers to Display
- [exact number with formatting, e.g., "$4,652"]

### Voiceover (if applicable)
> "[narration text]"

### Frame Timing
| Element | Appears | Disappears |
|---------|---------|------------|
| Hero text | frame [n] | frame [n] |
| Sub text | frame [n] | frame [n] |
```
