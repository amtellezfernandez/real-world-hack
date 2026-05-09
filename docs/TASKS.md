# RobotOps Sentinel — TASKS

> **Persistent execution state.** This file is the source of truth for what is done, what is next, and what is blocked. It survives sessions and compaction. PLAN remains the source for dependency and scope.

## Active

_None_

## In Progress

_None_

## Blocked

_None_

## Done

- [x] **F-01** Project skeleton and shared product contracts — *gate:* Backend and frontend start successfully, share documented incident/observation concepts, and expose no provider SDKs in UI code
- [x] **F-02** Vertical slice: clear/blocked replay appears in operations view — *gate:* A replay source drives clear and blocked visual states in the projected UI with a visible robot workcell zone
- [x] **F-03** Vertical slice: sustained blockage opens an incident — *gate:* A transient obstruction stays warning/dwell; a sustained obstruction opens an incident visible in the UI rail
- [x] **F-04** Vertical slice: supervisor approval broadcasts local alert — *gate:* Approving an incident records an alert transcript and plays or references a local/prebuilt audio alert
- [x] **F-05** Vertical slice: after evidence verifies closure — *gate:* The incident remains open after alert and closes only when after evidence shows the zone clear
- [x] **F-06** Vertical slice: audit packet and local review sample — *gate:* Closed incident displays before/after evidence, timestamps, reviewer decision, transcript, verification verdict, and a review/eval sample
- [x] **F-07** Demo timing and fallback controls — *gate:* Demo mode can shorten dwell/clear timers without changing the visible state machine or requiring external providers
- [x] **F-08** Gemini Robotics-ER clearance verifier adapter — *gate:* Gemini adapter can return blocked/clear/uncertain verdicts through the same verification port used by the simple verifier
- [x] **F-09** OpenAI/Foundry structured incident-report adapter — *gate:* OpenAI/Foundry adapter can enrich an opened incident with structured hazard, severity, evidence, and recommended action fields
- [x] **F-10** Mistral Voxtral voice adapter — *gate:* Mistral adapter conforms to the same voice output contract as the local/prebuilt audio provider
- [x] **F-11** RunPod YOLO perception adapter boundary — *gate:* YOLO-style detections can enter through the perception port without changing safety policy, API orchestration, or UI components
- [x] **F-12** Encord export scaffold and local fallback status — *gate:* Missing Encord credentials leave the local review queue intact and visibly mark export unavailable; real credentials can be added behind the same port
- [x] **F-13** ElevenLabs voice scaffold and provider status — *gate:* Missing ElevenLabs credentials do not break alerting; provider status truthfully shows local/Mistral/ElevenLabs availability
- [x] **F-14** Cross-provider integration selection — *gate:* Demo can state which providers are active and which are scaffolded/unavailable without fake sponsor claims
- [x] **F-15** Full closed-loop demo rehearsal package — *gate:* End-to-end demo completes the two-minute robot-workcell story and has a documented fallback path

## Conventions

- **Status values:** `pending` in Active or Blocked, `in_progress` in In Progress, `completed` in Done.
- **Annotations:** Add an indented `> *Note:*` only when something notable is discovered. Cap at 200 chars / 2 lines.
- **TaskTool relationship:** TaskTool is session-only. `TASKS.md` is persistent. Update this file whenever a feature starts, completes, or blocks.
- **One feature, one row:** If a task needs decomposition, update `PLAN.md` first.
- **Active refresh:** When a feature completes, move newly unblocked rows from Blocked to Active.
