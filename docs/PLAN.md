# RobotOps Sentinel — PLAN

> **Structural intent, not implementation.** This plan uses vertical delivery slices while preserving deep module boundaries. Each slice should produce a more demoable product state. Contracts live in `docs/SPEC.md`.

## Preamble

- **Source SPEC:** `docs/SPEC.md` (last updated: 2026-05-08)
- **Standard gates apply automatically:** tests, typing, lint, and no-test-no-commit discipline are enforced by the active style/TDD skills.
- **Feature-specific gates** below name the behavior that proves each slice works.
- **Architecture:** separate `frontend/` and `backend/`. Backend owns safety lifecycle, provider ports, and audit generation. Frontend owns projected operator experience.
- **Planning principle:** vertical slices first, provider upgrades later. The app should complete the closed-loop demo with simple adapters before external providers become required.
- **Deep module rule:** vertical slices may touch frontend, backend, and assets together, but provider SDKs must stay behind backend ports and must not leak into UI/domain code.

## Features

| ID | Feature | Depends on | Touches | Verification gate | Worktree |
|----|---------|------------|---------|-------------------|----------|
| F-01 | Project skeleton and shared product contracts | — | `frontend/**`, `backend/**`, `assets/**`, root tooling files | Backend and frontend start successfully, share documented incident/observation concepts, and expose no provider SDKs in UI code | no |
| F-02 | Vertical slice: clear/blocked replay appears in operations view | F-01 | `frontend/src/modules/demo-player/**`, `frontend/src/modules/safety-ui/**`, `backend/src/sitewalk/perception/**`, `assets/demo/**` | A replay source drives clear and blocked visual states in the projected UI with a visible robot-workcell zone | no |
| F-03 | Vertical slice: sustained blockage opens an incident | F-02 | `backend/src/sitewalk/safety/**`, `backend/src/sitewalk/api/**`, `backend/tests/safety/**`, `frontend/src/modules/api-client/**`, `frontend/src/modules/safety-ui/**` | A transient obstruction stays warning/dwell; a sustained obstruction opens an incident visible in the UI rail | no |
| F-04 | Vertical slice: supervisor approval broadcasts local alert | F-03 | `backend/src/sitewalk/voice/**`, `backend/src/sitewalk/api/**`, `assets/audio/**`, `frontend/src/modules/safety-ui/**` | Approving an incident records an alert transcript and plays or references a local/prebuilt audio alert | no |
| F-05 | Vertical slice: after evidence verifies closure | F-04 | `backend/src/sitewalk/safety/**`, `backend/src/sitewalk/verification/**`, `backend/src/sitewalk/api/**`, `frontend/src/modules/safety-ui/**`, `assets/demo/**` | The incident remains open after alert and closes only when after evidence shows the zone clear | no |
| F-06 | Vertical slice: audit packet and local review sample | F-05 | `backend/src/sitewalk/safety/**`, `backend/src/sitewalk/review_export/**`, `backend/tests/**`, `frontend/src/modules/safety-ui/**` | Closed incident displays before/after evidence, timestamps, reviewer decision, transcript, verification verdict, and a review/eval sample | no |
| F-07 | Demo timing and fallback controls | F-06 | `backend/src/sitewalk/safety/**`, `frontend/src/modules/demo-player/**`, `frontend/src/modules/safety-ui/**`, `docs/**` | Demo mode can shorten dwell/clear timers without changing the visible state machine or requiring external providers | no |
| F-08 | Gemini Robotics-ER clearance verifier adapter | F-05 | `backend/src/sitewalk/verification/**`, `backend/tests/verification/**` | Gemini adapter can return blocked/clear/uncertain verdicts through the same verification port used by the simple verifier | yes |
| F-09 | OpenAI/Foundry structured incident-report adapter | F-03 | `backend/src/sitewalk/verification/**`, `backend/tests/verification/**` | OpenAI/Foundry adapter can enrich an opened incident with structured hazard, severity, evidence, and recommended action fields | yes |
| F-10 | Mistral Voxtral voice adapter | F-04 | `backend/src/sitewalk/voice/**`, `backend/tests/voice/**` | Mistral adapter conforms to the same voice output contract as the local/prebuilt audio provider | yes |
| F-11 | RunPod YOLO perception adapter boundary | F-02 | `backend/src/sitewalk/perception/**`, `backend/tests/perception/**`, `docs/**` | YOLO-style detections can enter through the perception port without changing safety policy, API orchestration, or UI components | yes |
| F-12 | Encord export scaffold and local fallback status | F-06 | `backend/src/sitewalk/review_export/**`, `backend/tests/review_export/**`, `frontend/src/modules/safety-ui/**` | Missing Encord credentials leave the local review queue intact and visibly mark export unavailable; real credentials can be added behind the same port | yes |
| F-13 | ElevenLabs voice scaffold and provider status | F-04 | `backend/src/sitewalk/voice/**`, `backend/tests/voice/**`, `frontend/src/modules/safety-ui/**` | Missing ElevenLabs credentials do not break alerting; provider status truthfully shows local/Mistral/ElevenLabs availability | yes |
| F-14 | Cross-provider integration selection | F-08, F-09, F-10, F-12, F-13 | `backend/src/sitewalk/**`, `frontend/src/modules/safety-ui/**`, `docs/**` | Demo can state which providers are active and which are scaffolded/unavailable without fake sponsor claims | no |
| F-15 | Full closed-loop demo rehearsal package | F-07, F-14 | `docs/**`, `assets/demo/**`, `frontend/**`, `backend/**` | End-to-end demo completes the two-minute robot-workcell story and has a documented fallback path | no |

## Coverage Map

- SPEC UI rows `UI-01` to `UI-06` map to F-02 through F-07 and F-15.
- SPEC perception/rules rows `PR-01` to `PR-06` map to F-02, F-03, F-05, F-07, and F-11.
- SPEC AI rows `AI-01` to `AI-04` map to F-03, F-05, F-08, F-09, and F-14.
- SPEC alerting rows `AL-01` to `AL-03` map to F-04, F-10, F-13, and F-14.
- SPEC evidence/export rows `EV-01` to `EV-04` map to F-06 and F-12.
- SPEC cross-layer rows `X-01` to `X-03` map to F-07, F-14, and F-15.

## Notes

- F-02 through F-06 are the minimum winning demo path. After F-06, the product should already show detect, approve, alert, verify, prove using local/simple adapters.
- F-08 through F-13 are provider upgrade slices. They should not block the core closed-loop demo.
- F-11 intentionally stops at the RunPod/YOLO adapter boundary until the endpoint contract is known.
- Provider-specific credentials and SDK behavior belong only in backend adapter modules.
- The frontend should never branch on provider SDKs. It should display provider status and product state returned by backend contracts.
- Keep replay/demo mode as a data-source adapter. Do not fork the app into a separate hardcoded demo path.
- Demo timing should be configurable by policy so realistic and stage timings use the same state transitions.
- F-11 uses a provider-neutral YOLO boundary of `label`, `confidence`, and normalized bounding box coordinates; the concrete RunPod request/response contract remains open until deployment is known.

## Open Questions

- [x] Which primary demo asset should be created first? F-15 uses controlled generated frames for the reliable primary path.
- [x] What exact demo-mode dwell and clearance durations should be configured initially? Stage mode uses 3s playback dwell, 2s playback clearance, and 900ms frame pacing; real-time mode uses 30s/15s playback pacing while the safety policy remains unchanged.
- [ ] What RunPod YOLO deployment contract will be used once the GPU endpoint is ready?
- [ ] At the event, does Encord provide project/API access or only product credits/manual UI access?
- [ ] At the event, does ElevenLabs provide API access early enough to replace Mistral/local voice?
