# Video Factory — Agent Persistent Memory

## Project Context
This is a multi-agent video production pipeline.
Pipeline order: `/director` → `/designer` → `/motion-architect` → `/builder` → `/inspector`
Contract file: `specs/03-scene-map.json` is THE source of truth for all downstream agents.

## Director Rules (Always Active)
- Never start without completing all 7 intake categories
- `specs/` directory holds locked artifacts — never overwrite without user approval
- All frame math must be exact: `durationFrames = endFrame - startFrame`
- No scene > 150 frames (5 seconds at 30fps). Split automatically.
- 30fps is fixed. Never change.
- Hook **never** leads with logo — lead with number or pain point
- Never guess brand colors — always ask
- Never specify motion physics (Motion Architect's scope) or components (Builder's scope)

## Pydantic Contract Enforcement
- `src/director/models.py` contains the source of truth for all data types
- `SceneMapModel` validates the pipeline contract before write
- `ArtifactValidator` runs evaluator-optimizer loop before handoff
- Invalid artifacts raise `ValidationError` — handoff is blocked until resolved

## Current Project State
<!-- Director writes this block after each session -->
projectId: (none)
phase: (none)
intake_complete: false
artifacts_locked: false
