# RobotOps Sentinel — SPEC

> **Version:** 0.1 (generated from PRD)
> **Status:** Draft — requires human review
> **Last updated:** 2026-05-08

## 1. System Overview

RobotOps Sentinel is a hackathon prototype for closed-loop critical-zone robotics monitoring in workshops, factories, and prototype cells. It turns camera evidence from a site-defined robot workcell into an operational incident that can be approved, announced, visually verified, and preserved as review evidence.

The first workflow is robot-workcell obstruction. The system must demonstrate that it is more than object detection: it detects a sustained critical-zone violation, keeps robotics authority human-supervised, issues a specific floor alert, refuses to close until the physical world is visually clear, and produces an audit packet.

## 2. Success Criteria

1. A two-minute demo shows the full loop: clear zone, obstruction, incident open, alert approval, audible alert, obstruction removal, verified closure, audit evidence.
2. The system visibly distinguishes passive detection from verified closure by keeping the incident open until after-frame evidence shows the zone is clear.
3. Safety-critical lifecycle transitions are policy-bound and deterministic; AI-generated outputs explain and verify evidence but do not independently authorize closure.
4. The demo remains functional without paid ElevenLabs or Encord access.
5. Optional sponsor integrations can be swapped in without changing the product story or the user-facing workflow.
6. Product copy avoids compliance/autonomy overclaims and frames the system as monitoring, escalation, verification, and evidence.

## 3. Feature-Verification Matrix

### 3.1 Operations Experience

| ID | Feature | Verification (observable outcome) | Traces to |
|----|---------|----------------------------------|-----------|
| UI-01 | Robotics operations view | A large camera/replay feed shows a marked robot workcell with clear visual state: clear, dwell, incident, awaiting verification, or closed. | §1, §8.1 |
| UI-02 | Zone evidence overlay | When an obstruction is present, the UI shows why the zone is considered blocked using visible zone and evidence indicators. | BR-001, BR-002 |
| UI-03 | Incident rail | An open incident shows severity, zone, evidence frame, policy reason, recommended response, and current state. | §4, §5.2 |
| UI-04 | Alert approval control | A supervisor can approve, reject, or leave pending an alert; approval state is visible and recorded. | BR-004, §8.1 |
| UI-05 | Verification and audit view | After clearance, the UI shows before/after evidence, verification verdict, alert transcript, timestamps, and closure state. | BR-005, BR-008 |
| UI-06 | Review/eval queue | Closed incidents appear as review samples with frames, labels, decisions, and export readiness. | BR-008, §9 |

### 3.2 Perception, Rules, and State

| ID | Feature | Verification (observable outcome) | Traces to |
|----|---------|----------------------------------|-----------|
| PR-01 | Critical-zone definition | The monitored robot-workcell area is defined as a site-specific zone, not inferred as a generic image caption. | §4.1, BR-001 |
| PR-02 | Obstruction observation | The system represents an object occupying the critical zone with enough evidence to open or ignore an incident. | §4.1, BR-002 |
| PR-03 | Dwell threshold | A transient object can be ignored, while a sustained obstruction opens an incident after the configured threshold. | BR-003 |
| PR-04 | Incident state machine | Incidents move only through allowed states and cannot skip approval or verification gates. | §4.3, BR-004, BR-005 |
| PR-05 | Uncertainty handling | Ambiguous or unavailable perception produces an uncertain/review state rather than a false closed state. | BR-009 |
| PR-06 | Demo-mode timing | Shortened demo dwell/clear timers preserve the same visible state transitions as normal timing. | §7.5, R5 |

### 3.3 AI Assistance and Verification

| ID | Feature | Verification (observable outcome) | Traces to |
|----|---------|----------------------------------|-----------|
| AI-01 | Structured incident report | When an incident opens, the AI output is a typed incident summary with hazard, severity, evidence, and recommended action. | §5.3, BR-006 |
| AI-02 | Clearance verification | Given before/after evidence, the verifier returns a blocked/clear verdict with confidence and short rationale. | §5.3, BR-005 |
| AI-03 | Provider-independent AI role | The same product workflow works if one AI provider is unavailable and a configured alternative produces equivalent outputs. | BR-006, §9 |
| AI-04 | No AI safety authority | AI output can enrich incident data or verification evidence, but cannot bypass deterministic lifecycle transitions. | BR-002, BR-005 |

### 3.4 Alerting and Audio

| ID | Feature | Verification (observable outcome) | Traces to |
|----|---------|----------------------------------|-----------|
| AL-01 | Specific floor alert | Approved incidents produce a specific audible or spoken alert naming the zone and required action. | BR-004, §8.1 |
| AL-02 | Alert transcript | The exact alert text is stored with the incident and appears in the audit packet. | BR-008 |
| AL-03 | Provider-swappable audio | The system can use pre-generated audio, Mistral voice output, or event-provided voice tooling without changing the incident lifecycle. | BR-006, R4 |

### 3.5 Evidence, Storage, and Export

| ID | Feature | Verification (observable outcome) | Traces to |
|----|---------|----------------------------------|-----------|
| EV-01 | Evidence retention | Open and closed incidents preserve before frame, after frame when available, timestamps, state transitions, and reviewer decision. | §4.1, BR-008 |
| EV-02 | Audit packet | A closed incident has a complete evidence packet suitable for demo review and post-event export. | BR-008 |
| EV-03 | Review/eval record | Closed incidents can be represented as labeled review samples for a future Encord or internal eval workflow. | §4.1, R6 |
| EV-04 | Integration fallback | If Encord credentials are unavailable, the local review queue still shows the same evidence and labels. | BR-006, §9 |

### 3.6 Cross-Layer Verifications

| ID | Feature | Verification (observable outcome) | Layers involved | Traces to |
|----|---------|----------------------------------|----------------|-----------|
| X-01 | Closed-loop robot-cell demo | A blocked workcell moves from clear to open incident to approved alert to verified closure to audit packet without breaking the user-facing story. | UI, PR, AI, AL, EV | §2, §8.1 |
| X-02 | Human-supervised robotics loop | No audible alert is broadcast without an approval state, and no incident closes without visual clearance evidence. | UI, PR, AL, EV | BR-004, BR-005 |
| X-03 | Sponsor-resilient demo | The core demo remains complete when optional Encord or ElevenLabs integrations are replaced by local equivalents. | UI, AI, AL, EV | BR-006, §9 |

## 4. Domain Model

### 4.1 Core Entities

**Entity: CriticalZone**
- Description: A site-defined physical area whose obstruction or misuse is robotics-relevant.
- Key attributes:
  - `id`: stable identifier.
  - `name`: human-readable location, such as "Robot Workcell A-2".
  - `zone_type`: robot workcell, walkway, forklift lane, robot workcell, or other future critical-zone type.
  - `geometry`: visual area in camera coordinates.
  - `policy`: dwell threshold, severity mapping, and escalation rules.
- Invariants:
  - A safety incident must reference exactly one primary critical zone.
  - A zone must have an explicit policy before it can open incidents.

**Entity: EvidenceFrame**
- Description: A captured image/frame used to support an observation, verification, or audit record.
- Key attributes:
  - `source`: camera, replay clip, uploaded image, or generated test frame.
  - `timestamp`: capture time or replay timestamp.
  - `image_ref`: local or remote reference to the frame.
  - `annotations`: zone, detected objects, labels, verifier notes.
- Invariants:
  - Any closed incident must include at least one before frame and one after frame.

**Entity: Observation**
- Description: Evidence that an object or condition may be violating a critical-zone policy.
- Key attributes:
  - `zone_id`: critical zone under observation.
  - `observed_state`: clear, blocked, uncertain, camera unavailable.
  - `dwell_duration`: duration the state has persisted.
  - `evidence_frame_id`: supporting evidence.
  - `confidence`: perception confidence when available.
- Invariants:
  - An uncertain observation cannot directly close an incident.

**Entity: SafetyIncident**
- Description: The operational record for a critical-zone violation.
- Key attributes:
  - `id`: stable incident identifier.
  - `zone_id`: affected zone.
  - `state`: lifecycle state.
  - `severity`: low, medium, high, critical.
  - `incident_report`: structured explanation and recommended action.
  - `alert_events`: alert attempts and transcripts.
  - `verification`: clearance verdict when available.
  - `audit_packet`: final evidence packet when closed.
- Invariants:
  - An incident cannot close while the zone remains blocked or uncertain.
  - An incident cannot be marked closed without an after-frame verification record.

**Entity: AlertEvent**
- Description: A human-approved alert issued in response to an incident.
- Key attributes:
  - `incident_id`: related incident.
  - `approval_actor`: supervisor or demo operator approving the alert.
  - `alert_text`: exact spoken or audible message.
  - `provider`: local audio, Mistral, ElevenLabs, or other configured provider.
  - `timestamp`: alert time.
- Invariants:
  - Every broadcast alert must have a transcript.

**Entity: ReviewSample**
- Description: Evidence package that can be reviewed internally or exported to an annotation/eval platform.
- Key attributes:
  - `incident_id`: source incident.
  - `before_frame_id`: blocked/violation evidence.
  - `after_frame_id`: clearance evidence.
  - `labels`: hazard and clearance labels.
  - `human_decision`: accepted, corrected, rejected, or pending.
  - `export_status`: local only, export pending, exported.

### 4.2 Relationships

- CriticalZone -> SafetyIncident: one zone can produce many incidents; each incident has one primary zone.
- SafetyIncident -> EvidenceFrame: an incident has one or more before frames and zero or more after frames until verification.
- SafetyIncident -> AlertEvent: an incident may have zero or more alert events; at least one alert event is expected for the primary demo flow.
- SafetyIncident -> ReviewSample: a closed incident can produce one review sample.

### 4.3 State Machine

SafetyIncident can be in these states:

- `clear`: no active violation.
- `dwell`: potential violation observed but threshold not reached.
- `incident_open`: threshold reached and incident created.
- `alert_pending`: incident awaits human approval or rejection.
- `alert_broadcast`: approved alert has been issued.
- `clearing`: system awaits visual evidence that the obstruction has been removed.
- `verified_clear`: verifier and deterministic policy agree the zone is clear.
- `closed`: audit packet is complete.
- `uncertain`: evidence is insufficient for automated progression.

Allowed transitions:

- `clear` -> `dwell` when a potential obstruction is observed.
- `dwell` -> `incident_open` when the dwell threshold is met.
- `dwell` -> `clear` when the obstruction disappears before threshold.
- `incident_open` -> `alert_pending` when incident evidence is ready for supervisor action.
- `alert_pending` -> `alert_broadcast` when a supervisor approves.
- `alert_pending` -> `uncertain` or closed-without-alert only when the supervisor rejects as false positive.
- `alert_broadcast` -> `clearing` after the alert is issued.
- `clearing` -> `verified_clear` when after-frame evidence shows the zone clear.
- `verified_clear` -> `closed` when the audit packet is complete.
- Any state with insufficient evidence can move to `uncertain`.

Forbidden transitions:

- No transition may skip from `incident_open` to `closed`.
- No alert may be broadcast without an approval state in the demo flow.
- No incident may close from AI text alone.

## 5. Interface Contracts

### 5.1 API / Service Contracts

**Submit Observation**
- Purpose: Accepts a current critical-zone observation and returns whether it affects the incident lifecycle.
- Input: zone identifier, evidence reference, observed state, dwell duration, confidence when available.
- Output: current incident state and any incident opened or updated.
- Error cases:
  - Unknown zone -> explicit configuration error.
  - Missing evidence -> observation rejected as incomplete.
  - Camera/feed unavailable -> uncertainty state.

**Generate Incident Report**
- Purpose: Converts an opened incident and evidence summary into structured incident language.
- Input: incident id, zone, observed state, evidence summary, policy context.
- Output: hazard type, severity, concise rationale, recommended action, alert text candidate.
- Constraints: Output must be structured and must not claim autonomous safety authority.

**Approve Alert**
- Purpose: Records supervisor approval or rejection of an alert.
- Input: incident id, decision, reviewer identity or demo operator marker, optional edited alert text.
- Output: updated incident state and alert transcript when approved.
- Error cases:
  - Incident not alertable -> no broadcast.
  - Rejected alert -> incident moves to review/uncertain or false-positive resolution.

**Verify Clearance**
- Purpose: Evaluates before/after evidence and determines whether the critical zone appears clear.
- Input: incident id, before evidence, after evidence, zone context.
- Output: verified clear, still blocked, or uncertain, plus confidence and rationale.
- Constraints: A positive verification can support closure only when deterministic state policy also marks the zone clear.

**Get Audit Packet**
- Purpose: Returns the complete incident evidence package.
- Input: incident id.
- Output: incident states, timestamps, before/after frames, alert transcript, reviewer decision, verification verdict, review/export status.

### 5.2 Component Interfaces

**Component: SafetyOperationsView**
- Purpose: Presents the live/replay safety event as a single stage-ready experience.
- Inputs: camera/replay source, critical zones, current observations, incident state.
- User interactions: start/restart demo, inspect incident, approve alert, view audit packet.
- States: no feed, clear, dwell, incident open, alert pending, clearing, verified, closed, uncertain.

**Component: ZoneOverlay**
- Purpose: Makes critical-zone state visible on top of the video/image feed.
- Inputs: zone geometry, observation state, incident state, evidence markers.
- States: neutral, warning, critical, verifying, clear.

**Component: IncidentRail**
- Purpose: Shows the current incident and supervisor action controls.
- Inputs: incident, incident report, alert decision state.
- User interactions: approve alert, reject alert, view evidence.
- States: loading report, actionable, rejected, awaiting verification, closed.

**Component: VerificationPanel**
- Purpose: Shows before/after evidence and clearance verdict.
- Inputs: before frame, after frame, verifier outputs, deterministic state.
- States: awaiting after evidence, verifying, clear, still blocked, uncertain.

**Component: ReviewQueue**
- Purpose: Shows closed incidents as review/eval samples.
- Inputs: review samples and export status.
- States: empty, local samples, export pending, exported, export unavailable.

### 5.3 Event Schemas

**Event: ObservationUpdated**
- Trigger: New frame or replay tick changes the observed critical-zone state.
- Payload: zone id, observed state, dwell duration, evidence frame, confidence.
- Consumers: rules/state layer, operations view.
- Ordering guarantees: Later observations for the same zone supersede earlier observations by timestamp.

**Event: IncidentOpened**
- Trigger: Dwell threshold and policy conditions create a violation incident.
- Payload: incident id, zone, before evidence, severity, policy reason.
- Consumers: incident rail, incident-report generation, audit store.

**Event: AlertApproved**
- Trigger: Supervisor approves alert broadcast.
- Payload: incident id, reviewer, alert text, provider, timestamp.
- Consumers: audio alert provider, audit store, timeline.

**Event: ClearanceVerified**
- Trigger: After evidence shows the zone has cleared or remains blocked/uncertain.
- Payload: incident id, verdict, confidence, rationale, after evidence.
- Consumers: state machine, audit store, review queue.

## 6. Business Rules

- **BR-001: First workflow is robot-workcell obstruction** — The primary demo must focus on a designated robot-workcell zone and a sustained obstruction inside that zone.
- **BR-002: Deterministic safety lifecycle** — Zone overlap, dwell threshold, state transitions, approval gates, and closure gates are policy-driven and must not depend solely on model prose.
- **BR-003: Dwell threshold prevents noise** — A transient obstruction may be shown as dwell/warning but must not open an incident unless it persists long enough to violate policy.
- **BR-004: Human-approved alert** — In the demo flow, floor alerts require a visible approval action before broadcast.
- **BR-005: Verified closure required** — The incident cannot close until after evidence shows the zone clear and verification records support the closure.
- **BR-006: Optional sponsor integrations** — Unconfirmed sponsor tooling must have local/provider-swappable equivalents so the demo remains complete.
- **BR-007: No overclaiming** — The product must not claim to prevent accidents, ensure compliance, replace inspections, or act as an autonomous safety officer.
- **BR-008: Audit completeness** — Closed incidents must include enough evidence to explain what happened, who approved the alert, what was broadcast, and why the incident closed.
- **BR-009: Uncertainty is explicit** — Poor lighting, missing evidence, camera loss, conflicting verification, or low confidence must surface as uncertain/review, not false certainty.
- **BR-010: Review data flywheel** — Closed incidents should become review/eval samples so real site evidence can improve future model behavior.

## 7. Non-Functional Requirements

### 7.1 Performance

- The visual demo must feel real-time: zone state changes should appear within roughly one second of the relevant replay/live frame.
- Incident opening should be visible within roughly two seconds after the configured dwell threshold.
- Alert playback should begin immediately after approval from the audience's perspective.
- AI-generated enrichment may arrive asynchronously as long as the core incident state remains visible and coherent.

### 7.2 Safety and Liability

- The UI and generated text must use monitoring, escalation, verification, and evidence language.
- The system must make human approval and visual verification visible as product features, not hidden implementation details.
- The system must clearly distinguish "likely unsafe condition" from certified compliance or guaranteed accident prevention.

### 7.3 Security and Secrets

- API keys and provider credentials must not appear in UI, logs, screenshots, committed files, or audit packets.
- Evidence storage for the hackathon may be local, but audit records must not expose provider secrets or raw credential paths.

### 7.4 Accessibility

- Critical incident state must be conveyed through text and shape/state changes, not color alone.
- The approve/reject controls must be keyboard reachable in the demo app.
- Audible alert text must also appear as a visible transcript.

### 7.5 Reliability

- The core demo must work from controlled replay assets even when live camera, Encord, ElevenLabs, or one AI provider is unavailable.
- Demo mode may shorten timers, but it must preserve the same state machine and visible gates.
- Fallback outputs must preserve product truth: local audio is acceptable; fake sponsor integration is not.

## 8. UI/UX Specifications

### 8.1 User Flows

**Flow: Closed-Loop Blocked Exit**
1. The operator starts the demo with an robot-workcell zone in clear state.
2. The system shows the zone as clear and ready.
3. A pallet or box obstructs the zone long enough to cross the dwell threshold.
4. The system opens an incident and shows evidence, severity, policy reason, and recommended action.
5. The supervisor approves the alert.
6. The system broadcasts the approved floor alert and records the transcript.
7. The obstruction is removed.
8. The system verifies the zone is clear and closes the incident only after evidence supports closure.
9. The user sees an audit packet and review/eval sample.
- Happy path outcome: The audience sees a complete physical-world loop in under two minutes.
- Error paths: Ambiguous evidence, unavailable feed, or conflicting verification keeps the incident open or uncertain.

**Flow: False Positive or Transient Obstruction**
1. A brief or ambiguous obstruction appears in the zone.
2. The system shows warning/dwell or uncertainty rather than immediately broadcasting an alert.
3. If the condition clears before threshold or is rejected by the supervisor, it does not become a completed alert.
- Happy path outcome: The system demonstrates alert-fatigue protection.
- Error paths: If the system cannot decide, the evidence is routed to review.

### 8.2 Responsive Behavior

- The projected demo layout prioritizes the video/zone overlay and current incident state.
- The app should remain usable on a laptop screen, with secondary panels collapsing or scrolling before the core video/incident state is obscured.
- The audit/review view may be secondary; it should not compete with the live incident moment.

## 9. Implementation Notes

> Suggestions, not requirements. Sections 1-8 are authoritative.

- A single-page web app is the preferred demo surface because it projects well and keeps the story visible.
- Architecture decision: use separate `frontend/` and `backend/` folders. The frontend owns presentation and operator interaction; the backend owns safety policy, incident lifecycle, provider adapters, verification, alert generation, and audit packet creation.
- Backend modules should be Python-shaped unless implementation constraints change, because perception/model-provider glue and RunPod integration are likely easier to manage there.
- Frontend modules should consume backend contracts rather than provider SDKs directly.
- The perception service may run locally or on a temporary GPU host. The product contract is detector-independent as long as it provides object/zone evidence.
- OpenAI via Foundry can be used for structured incident reporting and recommendation text.
- Gemini Robotics-ER can be used as a before/after clearance-verification cross-check because access has been smoke-tested.
- Mistral Voxtral TTS can be used for pre-event alert audio; event-provided ElevenLabs can replace it if credits are available.
- Encord should remain an export-ready review/eval target until event credentials are confirmed. If unavailable, the local review queue must carry the same evidence shape.
- Pre-recorded or staged footage is preferred for the primary demo path; a live camera path is optional once reliable.
- Pre-generated alert audio is acceptable for reliability, as long as the transcript and provider state are represented honestly.
- Voice output should be provider-agnostic: a stable alert-audio contract can use local/pre-generated audio, Mistral Voxtral during pre-event work, and ElevenLabs if event credits are available.
- Perception should be provider-agnostic: the app should consume a stable observation/evidence contract whether detections come from YOLO on RunPod, local inference, or replay fixtures.
- Lightweight audit hashes for evidence frames and audit JSON are desirable if cheap, but the demo must not depend on cryptographic signing to tell the core story.
- The app should be product-shaped rather than demo-script-shaped: demo/replay mode is a data-source adapter, not a separate hardcoded application path.
- Prefer deep modules with narrow public interfaces. Module boundaries should hide provider/setup complexity behind domain-level contracts rather than spreading integration details through UI components.

## 10. Design Rationale Appendix

**R1: Verified closure is the differentiator**
- Supports: §1, BR-005, EV-02.
- Original choice: Focus on closed-loop detection, approval, alert, verification, and evidence.
- Underlying concern: Detection alone is commodity; verified closure is more memorable and operationally credible.
- Acceptable alternatives: Any implementation that keeps the incident open until visual closure evidence is present.
- Unacceptable alternatives: A detector-only dashboard that opens alerts but does not prove remediation.

**R2: Deterministic safety lifecycle**
- Supports: BR-002, BR-005, AI-04.
- Original choice: Safety transitions are rule/state driven; AI explains and verifies but does not authorize alone.
- Underlying concern: LLM-only safety decisions are unreliable and create liability risk.
- Acceptable alternatives: Different state-machine implementations that preserve approval and verification gates.
- Unacceptable alternatives: Letting model prose directly close incidents or broadcast alerts without policy gates.

**R3: Emergency-exit obstruction as first wedge**
- Supports: BR-001, Non-Goals.
- Original choice: Lead with robot workcells rather than PPE or forklift collision prevention.
- Underlying concern: Blocked exits are visually obvious, legally/operationally credible, and lower-liability than collision prevention.
- Acceptable alternatives: Another static critical-zone obstruction with equally clear before/after proof.
- Unacceptable alternatives: Starting with generic PPE or real-time collision prevention for the main demo.

**R4: Provider-swappable sponsor layer**
- Supports: BR-006, AL-03, EV-04.
- Original choice: Avoid hard dependency on paid/event-only integrations.
- Underlying concern: The demo must work before sponsor credentials are issued.
- Acceptable alternatives: Local equivalents that preserve the same user-visible contract.
- Unacceptable alternatives: Fake sponsor claims or failing the demo because optional credentials are unavailable.

**R5: Stage reliability over fragile live heroics**
- Supports: §7.5, UI-01, X-01.
- Original choice: Controlled replay/staged footage is primary; live camera is optional.
- Underlying concern: Judges reward a coherent live story more than fragile real-time setup.
- Acceptable alternatives: Live input that has been tested in the actual environment and has replay fallback.
- Unacceptable alternatives: A demo path that cannot proceed if lighting, camera, network, or API latency misbehaves.

**R6: Review/eval data flywheel**
- Supports: BR-010, EV-03, UI-06.
- Original choice: Closed incidents become labeled review samples.
- Underlying concern: The project should show how physical-world data improves model behavior over time.
- Acceptable alternatives: Internal review queue or real Encord export with equivalent evidence.
- Unacceptable alternatives: Treating review/export as a decorative logo without useful data.

**R7: Deep modules and provider ports**
- Supports: §9, BR-006, AL-03, EV-04.
- Original choice: Keep voice, perception, verification, and review/export behind narrow contracts.
- Underlying concern: Event access and infrastructure may change quickly; product behavior should remain stable while providers swap.
- Acceptable alternatives: Any module structure that keeps UI/domain code independent from provider SDKs and demo fixtures.
- Unacceptable alternatives: UI components calling provider SDKs directly or hardcoding the demo path as the product path.

**R8: Separate frontend and backend**
- Supports: §9, X-01, X-02.
- Original choice: Use separate frontend and backend folders instead of hiding the backend inside the frontend framework.
- Underlying concern: Safety state, policy, provider orchestration, RunPod perception, and audit generation are backend concerns and should not leak into UI code.
- Acceptable alternatives: A full-stack framework only if the same boundaries remain explicit and provider code stays out of UI components.
- Unacceptable alternatives: A frontend-only prototype where safety policy, provider calls, and demo fixtures are entangled in presentation code.

## 11. Open Questions

- [ ] Will event-provided Encord access include project creation and API/export capability, or should the demo avoid live Encord entirely?
- [ ] Will event-provided ElevenLabs access be available early enough to replace Mistral/local alert audio? Decision until then: keep voice provider-agnostic and use Mistral/local audio pre-event.
- [ ] Which footage will be the primary demo asset: staged in-room video, pre-recorded warehouse clip, or synthetic/replay sequence?
- [ ] What dwell and clearance durations should be used in demo mode versus realistic mode?
- [x] Will YOLO/perception run on RunPod, locally, or as a simulated/replay evidence source for the first stage build? Decision: assume YOLO will be available through RunPod, but keep app work behind a perception adapter until deployment is confirmed.
- [x] Should the audit packet include cryptographic hashes/signatures for demo credibility, or keep "signed" as reviewer/status evidence only? Decision: add lightweight hashes if easy; do not make them core.
- [x] Should the project use a full-stack frontend framework or separate frontend/backend folders? Decision: use separate `frontend/` and `backend/` folders.

## 12. Glossary

- **Critical zone:** A site-defined physical area where obstruction or misuse matters for safety.
- **Dwell threshold:** The time a potential violation must persist before it opens an incident.
- **Verified closure:** The incident state where after evidence supports that the hazard has been resolved.
- **Audit packet:** The before/after evidence, timestamps, alert transcript, reviewer decision, and verification output for a closed incident.
- **Review/eval sample:** A labeled evidence bundle that can be reviewed internally or exported to an annotation/evaluation platform.
