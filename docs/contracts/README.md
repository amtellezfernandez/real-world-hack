# Shared Product Contracts

The backend is the machine-readable contract source for F-01. It exposes
Pydantic/FastAPI schemas through OpenAPI, exported to `docs/contracts/openapi.json`.

The frontend consumes generated TypeScript types in
`frontend/src/modules/api-client/openapi.d.ts` and must not hand-write duplicate
incident or observation interfaces.

Provider SDKs belong behind backend ports only:

- `perception`
- `incident_reporting`
- `voice`
- `verification`
- `review_export`

The frontend may display provider status returned by the backend, but it must not
import provider SDKs directly.
