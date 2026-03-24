# /director

Run the Director agent — pre-production intake and artifact generation.

## Usage
```
/director                          # Start fresh intake
/director [blueprint text]         # Provide existing GPT blueprint to skip intake
/director --resume [projectId]     # Resume an incomplete intake session
```

## What This Command Does
1. Checks for upstream blueprint (auto-extracts all 7 categories if found)
2. Runs structured 7-category intake interview (grouped, never a wall of questions)
3. Generates three locked artifacts in `specs/`:
   - `specs/01-brief.md` — Brief Analysis (zero blank fields)
   - `specs/02-script.md` — Script with frame-level timing
   - `specs/03-scene-map.json` — Machine-readable pipeline contract
4. Self-validates all artifacts (Pydantic schema + evaluator-optimizer pass)
5. Outputs Handoff block for `/designer`

## This Command Does NOT
- Design visuals (→ `/designer`)
- Specify motion physics or springs (→ `/motion-architect`)
- Choose components or write `.tsx` code (→ `/builder`)
- Create HTML prototypes (→ `/designer`)

## Pipeline Position
```
[/director] → /designer → /motion-architect → /builder
     ↑ YOU ARE HERE
```

## Gate Criteria
The Director will not hand off until ALL of these pass:
- All 7 intake categories answered
- Brief has zero blank fields
- Script passes word count validation
- Scene-map passes Pydantic schema validation
- Evaluator-optimizer loop reports zero critical issues
