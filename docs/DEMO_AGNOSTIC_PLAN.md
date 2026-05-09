# Demo-Agnostic Plan

A vertical-slice rework plan to move RobotOps Sentinel from a single-purpose demo player to a demo-agnostic safety monitoring product.

---

## 1. Context: the app drifted to a demo-specific implementation

The product contracts (`backend/src/sitewalk/contracts.py`) are demo-agnostic: any zone, any incident, any provider. Everything around the contracts is not.

What is shipping today:

- **Three GET endpoints, all read-only.** `/health`, `/api/product-contract`, `/api/demo-replay`. CORS allows `GET` only, from `localhost:5173` only. There are no write paths anywhere in the system.
- **One hardcoded zone.** `backend/src/sitewalk/demo_data.py` defines a single `CriticalZone` fixture used everywhere.
- **Five hardcoded frames.** `backend/src/sitewalk/perception/replay.py` returns a fixed clear → blocked → sustained → still-blocked → cleared sequence at module import.
- **One hardcoded WAV.** `assets/audio/local-alert.wav` is the only alert audio. The transcript "Robotics notice: clear the obstruction at Robot Workcell A-2." is hardcoded.
- **One pre-computed lifecycle.** `backend/src/sitewalk/api/demo_replay_service.py` runs the full safety lifecycle once at module import and serves the resulting `DemoReplay` statically.
- **Six provider boundaries, none wired.** `incident_reporting/openai_foundry.py`, `verification/gemini_robotics_er.py`, `voice/elevenlabs.py`, `voice/mistral_voxtral.py`, `review_export/encord.py`, `perception/runpod_yolo.py` each define a `Callable` typed as the provider client and a factory function. No SDK appears in `pyproject.toml`. `AppContainer` (`api/state.py:6`) holds only `Settings`. None of the factories are constructed at startup, none are reachable from a route.
- **Provider env vars only flip a UI badge.** `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `MISTRAL_API_KEY`, `ENCORD_API_KEY`, `ENCORD_PROJECT_ID` are checked for presence and used to set a `CONFIGURED` / `UNCONFIGURED` flag. They are never passed to a client.
- **No persistence, no auth, no background workers, no streaming, no router on the frontend.**
- **The frontend module is named `demo-player/`.** It can only render the canned `/api/demo-replay` response. There is no incident list, no live view, no approve button, no review submission, no zone editor.

How `docs/TASKS.md` describes it: all 15 features F-01 through F-15 marked Done, including the six provider adapters (F-08–F-13). "Done" in practice means "boundary contract defined and unit-tested with an in-memory async lambda" — not "real provider integration".

How `docs/DEMO_REHEARSAL.md` describes it: every "fallback" path is the only path. The "demo runs without credentials" goal mutated into "the demo is the entire product."

The diagnosis: F-02 through F-06 were real vertical slices. F-08 through F-13 were horizontal slices in disguise (one boundary per provider, none crossing into a route or the UI), but were tracked as if they were verticals. Six "done" features added zero working integrations.

---

## 2. Goal: demo-agnostic

The product is demo-agnostic when **a different demo can run with no code or fixture changes**:

- A new site, camera, and zone can be created from the UI.
- New evidence can be ingested (uploaded or streamed).
- An incident opens, gets enriched by an LLM, gets a supervisor-approved alert with synthesized voice, gets verified by a separate model, closes, produces a downloadable audit packet, and exports a review sample.
- Provider statuses reflect actual reachability, not just env presence.
- No `demo_data.py` zone, no hardcoded replay frames, no hardcoded audio, no hardcoded transcript.

Every slice below ends with a user-observable result that contributes to that end state.

---

## 3. Cross-cutting rules

These apply to every slice. They are not separate slices.

1. **A slice is done only when a person can perform an action and observe the result.** Boundary defined + unit test with async-lambda fake does not count.
2. **Every new route updates the OpenAPI export and regenerates the frontend types** (`bun run contracts:generate` from `frontend/`). The CI check from W0 enforces this.
3. **Every new persistent entity ships with an Alembic migration**, even if `create_all` would work locally.
4. **Provider adapters use the official SDK** (see §4) and are constructed at startup from `Settings`. No `Callable` placeholders.
5. **Provider failures fall back to the local adapter** with a status visible in `/api/product-contract`.
6. **Storage uses the single blob storage boundary** (introduced in F4) — no ad-hoc paths for frames, audio, or audit bundles.
7. **Writes flow through repositories, not direct ORM calls in routes.**
8. **Don't reinvent what already exists.** See §4.

---

## 4. Library choices

Pinned so each slice doesn't re-derive them. Codex flagged "don't build custom what a library already covers" — these are the choices.

**Backend**

| Need | Choice | Notes |
|---|---|---|
| Persistence | `sqlmodel` + `alembic` | Reuses Pydantic models from `contracts.py`; SQLite (WAL) for now, Postgres later if needed. |
| Auth (supervisor identity) | `itsdangerous` signed cookies | Already a Starlette dep. No JWT, no `fastapi-users`. Upgrade to OIDC via `authlib` only if real auth is later required. |
| Blob storage | `pathlib` + FastAPI `StaticFiles` | One service class wrapping a configurable root dir. No S3, no `fsspec` until deployment forces it. |
| Image handling | `Pillow` | For resize/format conversion in the upload path. |
| Video frame extraction | `imageio-ffmpeg` | Lighter than `opencv-python`. Skip OpenCV entirely. |
| HTTP client (where SDK absent) | `httpx.AsyncClient` | Already a dev dep. |
| Idempotency | DB unique constraint + repo upsert | ~10 lines, no library. |
| SSE (deferred) | `sse-starlette` | When/if real-time updates land. |
| Provider tests | `respx` for httpx mocking; `pytest-recording` for live-vs-replay against SDKs | Modern `vcrpy` successor. |

**Provider SDKs (all installed; one call each, used directly inside the adapter)**

| Provider | Package | Adapter call |
|---|---|---|
| OpenAI Foundry | `openai` | `client.responses.parse(..., text_format=IncidentReport)` |
| Gemini Robotics-ER | `google-genai` | `client.models.generate_content(...)` with two image parts |
| ElevenLabs | `elevenlabs` | `client.text_to_speech.convert(...)` |
| Mistral Voxtral | `mistralai` | (deferred — see §6 cuts) |
| Encord | `encord` | `client.get_project(...).create_label_row(...)` |
| RunPod YOLO | `runpod` | `endpoint.run_sync(...)` against the configured serverless endpoint |

Use the SDK directly inside the adapter. Don't write a wrapper around a wrapper.

**Frontend**

| Need | Choice | Notes |
|---|---|---|
| Routing | `react-router` v7 | Introduced when first multi-page slice (F1) lands. |
| Data fetching | `@tanstack/react-query` | Replaces the manual `Promise.all` + `AbortController` in `App.tsx`. Removes the SSE-vs-refetch decision until much later. |
| Polygon editor | `react-konva` | Canvas-based; well-maintained. Don't hand-roll SVG dragging. |
| Forms | `react-hook-form` + `zod` | Schemas can mirror the generated OpenAPI types. |
| Audio playback | Native `<audio>` element | No library. |

---

## 5. The slices, in execution order

23 slices total: 1 wiring seed (W0), 22 verticals organized in 12 phases. Each is independently shippable.

### W0 — Wiring seed (the only horizontal pass)

**Goal:** Make verticals possible without each one reinventing plumbing.

**Owns:**
- Extend `AppContainer` (`backend/src/sitewalk/api/state.py`) to hold adapter slots: perception, reporter, voice, verifier, exporter, storage.
- Add FastAPI `Depends` providers for each adapter slot.
- Reconcile config namespaces: `Settings` uses the `SITEWALK_` prefix today; provider env vars (`OPENAI_API_KEY` etc.) are read directly from `os.environ` in `providers/integration_status.py`. Move all credentials onto `Settings` with no prefix change required at the env-var name level.
- Add `.env.example` listing all 8 credential vars.
- Loosen CORS in `api/main.py` to allow `POST`, `PATCH`, `DELETE` and to read allowed origins from `Settings`.
- Add `POST /api/_ping` as a wiring template that resolves an adapter via `Depends`.
- Add `scripts/check_openapi_drift.py` — compares the runtime FastAPI OpenAPI export to `docs/contracts/openapi.json`, exits non-zero on drift, prints the regen command. Hook into `uv run` task.
- Frontend `bun run contracts:generate` is already wired; add a `bun run contracts:check` that fails on drift.

**Done when:** `POST /api/_ping` returns the resolved adapter's status; `uv run check-openapi-drift` and `bun run contracts:check` both pass; `.env.example` is checked in.

---

### Phase 1 — Foundation (persistence + domain shape)

Codex's structural pushback: site/camera/zone-policy must land before any ingest route. This phase does that.

#### F1 — Site entity + persistence foundation

**Goal:** First persistent entity. Bootstraps SQLModel + Alembic.

**Owns:**
- `sqlmodel` and `alembic` added to `pyproject.toml`.
- `Site` model with `id`, `name`, `created_at`.
- First Alembic migration.
- `SiteRepository` with `create`, `get`, `list`.
- `POST /api/sites`, `GET /api/sites`, `GET /api/sites/{id}`.
- Frontend: `react-router` introduced; site list page; site selector in header that persists `current_site_id` in localStorage.

**Done when:** Create a site, refresh the page, the site is still there and selected.

#### F2 — Camera entity + frame-source config

**Goal:** Cameras are first-class, scoped to a site.

**Owns:**
- `Camera` model: `id`, `site_id`, `name`, `frame_source` (discriminated union: `manual_upload` | `local_file` | `rtsp_url`), `frame_width`, `frame_height`.
- Migration.
- `CameraRepository`, `POST/GET /api/sites/{site_id}/cameras`.
- Frontend: camera registration form; camera list under the selected site.

**Done when:** Register a camera under the selected site; it appears in the camera list and survives a reload.

#### F3 — Zone entity + policy + polygon editor

**Goal:** Replace the hardcoded `demo_data.py` zone with persisted, configurable zones.

**Owns:**
- `Zone` model: `id`, `camera_id`, `name`, `polygon` (normalized coordinates), `policy` (dwell seconds, confidence floor, severity mapping, blocking-class rules), `alert_template` (string with placeholders).
- Migration.
- `ZoneRepository`, `POST/GET/PATCH /api/cameras/{camera_id}/zones`.
- A "sample frame" upload endpoint scoped to the camera so the editor has something to draw on.
- Frontend: polygon editor using `react-konva`; policy form (dwell, confidence, severity, alert template).
- Lifecycle (`safety/lifecycle.py`) rewritten to read thresholds from the zone's policy, not module constants.
- Delete `demo_data.py` (or convert to a one-time seed CLI).

**Done when:** Upload a sample frame to a camera, draw a polygon, set a 3s dwell + custom alert template, save, reload, and the zone with its policy is intact.

#### F4 — Blob storage boundary

**Goal:** One storage service for frames, audio, and audit bundles.

**Owns:**
- `BlobStorage` service wrapping a configurable root dir; methods: `put(category, key, bytes, mime)`, `get_url(category, key)`, `delete(category, key)`.
- Wired into `AppContainer`.
- Mount under `/blobs` via FastAPI `StaticFiles`.
- Replace the sample-frame storage from F3 to use this service.

**Done when:** Sample frames uploaded in F3 are served via `/blobs/sample-frames/{key}` and visible in the editor.

---

### Phase 2 — Real perception ingest

#### P1 — Frame upload + local stub perception

**Goal:** Run the perception pipeline against any uploaded frame using a local stub detector. Proves the route shape before introducing RunPod risk.

**Owns:**
- `LocalStubDetector` adapter implementing the perception port: returns deterministic detections from a static configuration (so a new test image can be classified clear/blocked by setting a flag).
- `Observation` model + `ObservationRepository`.
- Frame bytes persisted via the F4 storage boundary; `EvidenceFrame.image_ref` resolves to a real `/blobs/...` URL.
- `POST /api/cameras/{camera_id}/observations` (multipart frame + optional `force_label` for the stub).
- Frontend: per-camera "Upload frame" button; result view rendering the polygon overlap and computed observation state.

**Done when:** Upload a frame against a camera; system returns and displays an observation with state tied to the camera's zone policy.

#### P2 — Idempotency gate (observation → incident)

**Goal:** Repeated observations within the same dwell window for the same camera collapse into one logical event. Closes the gap Codex flagged.

**Owns:**
- `dwell_window_id` derived from `(camera_id, floor(timestamp / dwell_seconds))`.
- DB unique constraint on `(camera_id, dwell_window_id)` for the in-progress incident.
- Repository upsert: subsequent observations within the window update the existing incident instead of creating a new one.
- Idempotency-key header support on `POST /api/cameras/{camera_id}/observations` for client-side retries.

**Done when:** Uploading the same blocked frame three times in succession produces one incident, not three.

#### P3 — Real RunPod YOLO client

**Goal:** Replace the local stub with the real perception provider when configured.

**Owns:**
- `runpod` SDK installed.
- `RunPodYoloDetector` adapter using `endpoint.run_sync(...)` against `Settings.runpod_endpoint_id`.
- Adapter registered via `Depends` so a per-request override is possible.
- Provider selection in startup: prefer RunPod if `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` are set; otherwise local stub. Status visible in `/api/product-contract`.
- `respx`-based test plus a recorded `pytest-recording` cassette.

**Done when:** With env set, an uploaded frame produces detections from real RunPod YOLO; with env unset, the local stub still works.

---

### Phase 3 — Incident lifecycle persistence

#### L1 — Incidents persisted; replay path retired

**Goal:** Incidents become durable first-class entities; the import-time pre-computed replay is removed.

**Owns:**
- `Incident`, `EvidenceFrame`, `IncidentEvent` models (the `IncidentEvent` table records every state transition).
- Migration.
- `IncidentRepository` with `open_or_advance`, `list`, `get`.
- `assess_observation` runs per-request inside the observation route and writes through the repo.
- `GET /api/sites/{site_id}/incidents` with state/zone/since filters; `GET /api/incidents/{id}` with full evidence trail.
- Delete `api/demo_replay_service.py` and `perception/replay.py`. Remove `/api/demo-replay` route. Remove `REFERENCE_PRODUCT_CONTRACT` derivation from `PRIMARY_DEMO_ZONE`.
- Frontend: incident list page (per site) + incident detail page; old single-screen replay deleted.

**Done when:** Repeated frame uploads against a camera open and progress incidents that survive reload, are listed under the site, and can be drilled into.

#### L2 — Manual after-evidence submission

**Goal:** A clearance attempt can be submitted manually, without waiting for the (later) continuous loop.

**Owns:**
- Optional `intent: "clearance_attempt"` parameter on `POST /api/cameras/{camera_id}/observations`.
- Lifecycle handles the transition into `clearing` when the observation comes from a clearance attempt and the zone reads as clear.
- Frontend: "Submit clearance evidence" button on open incident detail.

**Done when:** From an open incident, upload a clear frame as a clearance attempt; incident transitions to `clearing`.

#### L3 — Rejection / false-positive flow

**Goal:** Supervisor can dismiss an open incident; rejection is auditable.

**Owns:**
- `POST /api/incidents/{id}/reject` with `reason` body. Persists an `IncidentEvent` of type `rejected` with reason.
- Lifecycle terminal state `rejected` (sibling of `closed`).
- Frontend: "Dismiss as false positive" button with a reason form.

**Done when:** I dismiss an open incident; it shows as rejected with my reason in the audit trail.

---

### Phase 4 — Identity (so approvals are auditable)

#### I1 — Supervisor identity via signed cookies

**Goal:** Every write carries an identifiable actor; approvals later record `approver_id`.

**Owns:**
- `User` model: `id`, `name`, `email`, `created_at`. (No password — this is hackathon-grade attribution, not real auth.)
- Migration.
- `POST /api/auth/login` (accepts name + email, returns a signed cookie via `itsdangerous`).
- `GET /api/auth/me`, `POST /api/auth/logout`.
- `Depends(current_user)` requirement on all write routes.
- All write routes from L1–L3 now record the user on their `IncidentEvent`.
- Frontend: minimal login screen, auth context, redirect on 401, "logged in as" indicator.

**Done when:** I log in as "Alex"; my rejection of an incident shows "rejected by Alex" in the audit trail.

---

### Phase 5 — LLM-enriched reports

#### R1 — OpenAI Foundry incident report

**Goal:** Open incidents carry an LLM-generated structured report.

**Owns:**
- `openai` SDK installed.
- `OpenAIIncidentReporter` adapter using `client.responses.parse(..., text_format=IncidentReport)`.
- Wired via `Depends`; called when an incident transitions into `incident_open`. Persisted on the incident.
- Local deterministic reporter retained as fallback when `OPENAI_API_KEY` unset.
- Status (`local` vs `openai`) visible in `/api/product-contract` and on the incident detail.
- Frontend: incident detail renders hazard, severity, recommended action, suggested alert transcript (which feeds V1).

**Done when:** With `OPENAI_API_KEY` set, opening an incident produces an OpenAI-generated report whose alert text candidate differs from the local deterministic one.

---

### Phase 6 — Approval + voice

Split per Codex: approval state + voice provider + dynamic transcript are separate risks.

#### V1 — Alert approval + persisted alert event

**Goal:** Supervisor approves an incident with an editable transcript. Audio still uses the existing local fallback WAV.

**Owns:**
- `AlertEvent` model + repo.
- `POST /api/incidents/{id}/alert/approve` with body `{ transcript }`. Requires `current_user`. Creates an `AlertEvent` with `approver_id`, `transcript`, `provider="local"`, `audio_ref` pointing to the local fallback WAV (still acceptable here — V2 fixes it).
- Lifecycle transition `incident_open` → `alert_broadcast`.
- Frontend: approval form on open incidents, pre-filled with the report's `alert_text_candidate` from R1, editable.

**Done when:** I approve an incident with my edited transcript; the alert event records me + transcript + state transition.

#### V2 — Dynamic transcript-driven local audio

**Goal:** A non-exit zone can sound a different message without code changes. Removes the hardcoded "Robot Workcell A-2" line as the floor.

**Owns:**
- Replace the single hardcoded WAV reference with either (a) a TTS-via-stdlib path using `pyttsx3` or `gtts` for the local fallback, or (b) a per-zone `alert_template` rendered to a pre-recorded clip lookup. Either is acceptable — pick the simpler one once examined.
- Generated audio persisted via the F4 storage boundary; `audio_ref` points to `/blobs/audio/{event_id}`.

**Done when:** A zone with a custom alert template (set in F3) plays back audio matching that template, not the hardcoded line.

#### V3 — ElevenLabs voice synthesis

**Goal:** When configured, alert audio comes from ElevenLabs.

**Owns:**
- `elevenlabs` SDK installed.
- `ElevenLabsVoiceAdapter` using `client.text_to_speech.convert(...)`. Audio bytes persisted via F4 storage boundary; served via `StaticFiles`.
- Wired via `Depends`; provider selection in startup: ElevenLabs if `ELEVENLABS_API_KEY` set, otherwise V2 local fallback.
- `AlertEvent.provider` reflects what was actually used.
- Frontend: HTML5 `<audio>` plays the audio_ref URL on the alert event view.

**Done when:** With `ELEVENLABS_API_KEY` set, approving an incident produces real ElevenLabs audio that plays in the browser; without it, V2 local audio still plays.

---

### Phase 7 — Verification + closure

#### C1 — Gemini Robotics-ER clearance verification

**Goal:** Independent model verification gates incident closure.

**Owns:**
- `google-genai` SDK installed.
- `GeminiClearanceVerifier` adapter using `client.models.generate_content(...)` with two image parts (before and after frames).
- Triggered automatically when an incident transitions to `clearing` (from L2 manual or M2 continuous).
- `ClearanceVerification` persisted on the incident.
- Lifecycle gate: incident only transitions to `closed` on `clear` verdict; on `still_blocked`, returns to `incident_open`; on `uncertain`, stays `clearing` and surfaces a manual override option.
- Local deterministic verifier remains as fallback.
- Frontend: verification result panel (verdict, confidence, rationale, after-frame preview) on incident detail. Manual override on `uncertain`.

**Done when:** With `GEMINI_API_KEY` set, a clearing incident displays a Gemini verdict and only closes on `clear`.

---

### Phase 8 — Audit + export

#### A1 — Audit packet generation + download

**Goal:** Closed incidents produce a downloadable evidence bundle.

**Owns:**
- `AuditPacket` repo.
- On incident `closed` (or `rejected`), generate the packet: incident metadata, all `IncidentEvent`s, before/after `EvidenceFrame` URLs, alert transcript + audio URL, verification record, approver info.
- `GET /api/incidents/{id}/audit` returns the packet JSON.
- Optional `?format=zip` returns a zip bundle (JSON + frames + audio) staged through F4.
- Frontend: "Download audit packet" button on closed/rejected incidents.

**Done when:** I close an incident; clicking download gives me a JSON bundle (or zip) with all the evidence and identifiable approver/verifier info.

#### A2 — Encord review export

**Goal:** Closed incidents can be pushed to Encord as labeled review samples.

**Owns:**
- `encord` SDK installed.
- `EncordReviewExporter` adapter using `client.get_project(project_id).create_label_row(...)` (or the equivalent SDK call for the Encord API surface in use).
- `POST /api/incidents/{id}/export`. Creates a `ReviewSample` record, stores the returned project URL on the incident.
- Local "review queue" remains as fallback when env unset.
- Frontend: "Export to Encord" button on closed incidents; status badge (pending / exported / failed); link out to the project URL.

**Done when:** With Encord creds, clicking export uploads the sample and the project URL appears on the incident.

---

### Phase 9 — Provider observability

#### O1 — Real provider smoke-test status

**Goal:** Replace env-presence-only badges with actual reachability.

**Owns:**
- Provider port extended with an optional `health_check` async method.
- Each wired adapter implements `health_check` with a cheap call (e.g. OpenAI: `client.models.list()`, ElevenLabs: voices list, Gemini: model list, Encord: project metadata, RunPod: endpoint health).
- `/api/product-contract` (or a new `/api/providers/status`) returns per-provider status: `unconfigured` / `configured` / `reachable` / `last_call_failed` with the last error message and check timestamp.
- Cached for 30s to avoid hammering on every UI render.
- Frontend: provider status table reflects the new states with a manual "recheck" button.

**Done when:** Killing an SDK key flips the status to `last_call_failed` within the cache TTL; restoring it flips back to `reachable` after a recheck.

---

### Phase 10 — Continuous perception

Deferred until manual flow proven. Codex flagged S8 as one of the highest-risk slices — keep it after the manual lifecycle works end-to-end.

#### M1 — Camera frame-source abstraction (file path only)

**Goal:** Cameras configured with a `local_file` source can stream frames at a configured FPS through the same observation route.

**Owns:**
- `FrameSource` abstraction with one implementation: `LocalFileFrameSource` using `imageio-ffmpeg` to extract frames at `Settings.frames_per_second`.
- `POST /api/cameras/{id}/start` and `POST /api/cameras/{id}/stop` (manual control; M2 will automate).
- The streamed frames go through the same observation pipeline (frame stored, perception called, lifecycle advanced, idempotency gate from P2 in effect).
- Frontend: per-camera start/stop control; latest frame preview that polls every 2s (no SSE yet).

**Done when:** Configure a camera with a video file, click start, and the system opens an incident automatically when the file shows a sustained block.

#### M2 — Background workers per active camera

**Goal:** Cameras run autonomously without UI intervention; the full loop runs end-to-end.

**Owns:**
- Background asyncio task per active camera registered in `AppContainer` lifespan.
- Restart-on-failure with exponential backoff.
- Worker advances the lifecycle, triggers verification (C1) on clearing transitions, and closes incidents on verified clear.
- Frontend: "active worker" indicator next to each camera.

**Done when:** Start a camera; without further UI input, it opens an incident, gets a report (R1), waits for an approval (V1), broadcasts (V3), detects clearing, verifies (C1), and closes (A1) — all visible in the incident timeline.

---

### Phase 11 — Scenario import (kills the last hardcoded demo)

#### D1 — Scenario import endpoint

**Goal:** Replace the last vestiges of demo-specific code with a data-driven bootstrap.

**Owns:**
- `POST /api/scenarios/import` accepts a multipart upload: `scenario.yaml` (sites + cameras + zones + policies + alert templates) plus a frames archive (optional sample frames per camera).
- Imports the scenario into the DB; reports created entities.
- A `scenarios/robot-workcell.yaml` fixture replaces the deleted `demo_data.py` content.
- Frontend: "Import scenario" admin action that takes a yaml + zip.

**Done when:** Anyone can `curl -F scenario=@scenario.yaml -F frames=@frames.zip /api/scenarios/import` and end up with a fresh, demo-ready site without touching code.

---

### Phase 12 — Documentation truth

#### T1 — Update PRD / SPEC / TASKS / DEMO_REHEARSAL

**Goal:** Docs match reality after the rework.

**Owns:**
- `docs/TASKS.md`: split F-08 through F-13 into "boundary defined" (already done) vs "wired" (now done per phase 5/6/7/8). Mark each new slice (W0–T1) with status.
- `docs/PRD.md` and `docs/SPEC.md`: reflect multi-site, multi-camera, multi-zone product. Remove single-purpose "blocked robot workcell" framing as the only use case.
- `docs/DEMO_REHEARSAL.md`: rewrite each step to call out which providers are live vs. local fallback at demo time, based on env state.
- New `docs/RUNBOOK.md`: how to start the stack, how to import a scenario, how to add provider creds, how to run the smoke tests.

**Done when:** A reader who has never seen the project can read the docs and accurately predict what works and what is local-fallback.

---

## 6. What was cut from the earlier plan

These were in the original 18-slice list and are removed from MVP scope. Add later if needed.

- **Mistral Voxtral as alternative voice provider.** Duplicate capability with ElevenLabs once V3 lands. One real voice provider plus the V2 local fallback satisfies the demo-agnostic property.
- **Server-Sent Events for live updates.** M2 polling at 2s is acceptable until S11-grade real-time is needed. `sse-starlette` choice already pinned for when it returns.
- **Slack / external notifications.** Polish, not core to the lifecycle.
- **Docker / docker-compose / deployment posture.** Outside the PRD's "not full deployment" constraint. Env-driven config from W0 already covers basic portability.
- **Prometheus `/metrics` endpoint.** O1 covers what's needed for the demo-agnostic property; metrics are post-MVP.
- **Full OIDC auth.** I1 signed cookies cover supervisor attribution. Upgrade to OIDC via `authlib` only when real auth is required.
- **OpenCV.** `imageio-ffmpeg` covers M1's only frame-extraction need.
- **`vcrpy`.** Replaced by `pytest-recording` for live-vs-replay testing of SDK-based adapters.

---

## 7. Quick map

```
W0  Wiring seed
F1  Site + persistence foundation
F2  Camera + frame-source config
F3  Zone + policy + polygon editor (deletes demo_data.py)
F4  Blob storage boundary
P1  Frame upload + local stub perception
P2  Idempotency gate
P3  Real RunPod YOLO
L1  Incident persistence (deletes /api/demo-replay)
L2  Manual after-evidence
L3  Rejection / false-positive flow
I1  Supervisor identity (signed cookies)
R1  OpenAI Foundry report
V1  Alert approval + persisted event
V2  Dynamic transcript-driven local audio
V3  ElevenLabs voice
C1  Gemini clearance verification
A1  Audit packet + download
A2  Encord review export
O1  Real provider smoke-test status
M1  Continuous perception (file source)
M2  Background workers per camera
D1  Scenario import (kills last hardcoded demo)
T1  Documentation refresh
```

Take them one at a time. Each one is a complete vertical that ends with something you can demo to a person.
