# RobotOps Sentinel Demo Rehearsal

## Goal

Run the robot-workcell story in under two minutes:

1. Clear robot workcell.
2. Sustained obstruction opens an incident.
3. Supervisor approves the floor alert.
4. Alert transcript and audio reference are recorded.
5. Still-blocked after evidence keeps the incident open.
6. Clear after evidence closes the incident with audit and review evidence.

## Preflight

Run these before launching the backend and frontend servers:

```bash
cd backend
uv run pytest
uv run ruff check
uv run ty check
```

```bash
cd frontend
bun install
bun test
bun run lint
bun run build
bun run contracts:lint
```

When launching the frontend, leave `VITE_API_BASE_URL` unset or set it to
`http://127.0.0.1:8000`.

- `GET /health` returns `ready`.
- `GET /api/demo-replay` returns six assessed frames.
- `GET /api/product-contract` includes provider integration statuses.
- The UI shows `Stage timing`, `Local replay`, `Local audio`,
  `Local clearance`, and `Local review` as active local paths.
- Optional sponsor rows are shown as configured or unconfigured scaffolds.

## Start Commands

Use two terminals from the repository root.

Backend:

```bash
cd backend
uv run fastapi dev src/sitewalk/api/main.py --host 127.0.0.1 --port 8000 --no-reload
```

Frontend:

```bash
cd frontend
bun run dev
```

Open `http://127.0.0.1:5173`. The frontend expects the backend at
`http://127.0.0.1:8000` unless `VITE_API_BASE_URL` is set.

## Two-Minute Run

| Time | Operator action | What to say |
| --- | --- | --- |
| 0:00 | Load the operations view on `Stage timing`. | "This is a site-defined robot-workcell zone, not a generic safety dashboard." |
| 0:10 | Start or step to `Clear exit`. | "The exit starts clear, with the zone boundary visible on the replay." |
| 0:25 | Step to `Transient blockage`. | "A short obstruction enters dwell, but it does not open an incident yet." |
| 0:40 | Step to `Sustained blockage`. | "After the dwell threshold, the backend opens a high-severity incident with deterministic policy context." |
| 0:55 | Step to `Approved alert`. | "A supervisor-approved alert is broadcast locally, and the exact transcript is retained." |
| 1:10 | Step to `Still blocked`. | "The incident cannot close while after evidence still shows the zone blocked." |
| 1:25 | Step to `Verified clear`. | "Once the after frame is clear, the incident closes with before/after evidence, timestamps, verification verdict, and a review sample." |
| 1:45 | Open the provider status section. | "The demo is honest about providers: local paths are active, and sponsor integrations stay configured or unconfigured until manually exercised." |

## Fallback Path

The primary demo does not require external providers.

| Dependency | Demo fallback |
| --- | --- |
| Live camera or RunPod | Local replay frames remain the perception source. |
| OpenAI/Foundry | Deterministic incident report remains attached to the incident. |
| Gemini Robotics-ER | Deterministic clearance verifier remains the closure gate. |
| Mistral or ElevenLabs | Local prebuilt audio and transcript remain the alert path. |
| Encord | Local review sample remains visible; Encord remains a configured or unconfigured scaffold. |

Do not claim a sponsor integration is live unless the provider status panel shows
it as configured and the adapter has been manually exercised before the demo.

## Expected Evidence

Expected demo replay states:

```text
clear -> dwell -> incident_open -> alert_broadcast -> clearing -> closed
```

Expected closed-incident evidence:

- Before frame: `frame-workcell-sustained-blocked`
- After frame: `frame-workcell-after-clear`
- Alert transcript: `Robotics notice: clear the obstruction at Robot Workcell A-2.`
- Verification verdict: `clear`
- Review status: `local_only`

## Reset

Refresh the browser to return to the first replay frame. The backend replay is
static and does not mutate server state.
