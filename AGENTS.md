# AGENTS.md

## Project State

Before planning or implementing, read:

- `docs/PRD.md`
- `docs/SPEC.md`
- `docs/PLAN.md`
- `docs/TASKS.md`

Treat `docs/TASKS.md` as the persistent execution state. Update it whenever a feature starts, completes, or becomes blocked.

## Project Rules

- Build vertical slices while preserving deep module boundaries.
- Keep provider SDKs behind backend ports/adapters.
- Do not let frontend code call perception, verification, or review/export providers directly.
