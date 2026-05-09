# Encord + OpenAI Incident Dataset Integration

This repo keeps Encord and OpenAI behind backend endpoints. The frontend and
demo flow should never call either SDK directly.

## Local Credentials

Place the downloaded Encord private key at the repo root:

```text
encord-airw_hack-private-key.ed25519
```

The file is ignored by Git. Copy `backend/.env.example` to `backend/.env` and
fill:

```env
ENCORD_PROJECT_ID=...
ENCORD_DATASET_ID=...
ENCORD_STORAGE_FOLDER=AIRW Hack Incidents
ENCORD_DOMAIN=https://api.encord.com

OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
```

`ENCORD_SSH_KEY_FILE` is optional when the key is kept at the repo root with
the filename above.

If your Encord workspace is US-hosted, use:

```env
ENCORD_DOMAIN=https://api.us.encord.com
```

Live provider calls need the optional SDKs:

```powershell
cd backend
uv add encord openai
```

The app still returns local packets and local outcome reports without those
packages.

## Ontology

The app ontology is:

- `robot_path`: polygon
- `obstruction`: bounding box
- `safe_drop_zone`: polygon
- `human`: bounding box
- `robot`: bounding box

Classifications:

- `zone_state`: `clear`, `blocked`, `uncertain`
- `approval_state`: `pending`, `approved`, `rejected`
- `robot_action`: `none`, `stopped`, `remove_obstruction`,
  `manual_intervention`
- `verification_result`: `cleared`, `still_blocked`, `unsafe`, `uncertain`
- `review_decision`: `accepted`, `corrected`, `rejected`, `pending`
- `incident_id`: text
- `openai_outcome_summary`: text

Print the ontology JSON:

```powershell
cd backend
uv run sitewalk-encord-ontology
```

Create it in Encord:

```powershell
cd backend
uv run sitewalk-create-encord-ontology
```

Install the Encord SDK first if that command reports it is missing.

## Demo Endpoints

All endpoints are safe without credentials.

```http
GET  /api/demo-replay/encord/ontology
POST /api/demo-replay/encord/ontology
GET  /api/demo-replay/encord/export-packet
POST /api/demo-replay/report/openai
POST /api/demo-replay/export/encord
```

`GET /api/demo-replay/encord/export-packet` builds the Encord-ready incident
packet locally.

`POST /api/demo-replay/report/openai` returns an OpenAI structured analysis when
`OPENAI_API_KEY` is configured and falls back to local deterministic analysis
when it is not.

`POST /api/demo-replay/export/encord` uploads before/after images only when:

- Encord credentials are configured,
- `ENCORD_DATASET_ID` is configured,
- `before_image_path` and `after_image_path` are concrete local image files.

Example:

```json
{
  "before_image_path": "D:/AIRW_Hack/real-world-hack/runs/demo_001/before.png",
  "after_image_path": "D:/AIRW_Hack/real-world-hack/runs/demo_001/after.png",
  "include_openai_report": true
}
```

The current replay assets are SVG files, so the endpoint returns the packet when
no PNG/JPEG paths are supplied. The robot sim should pass real captured frame
paths.
