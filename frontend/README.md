# URDF Zone Frontend

Vite React TypeScript shell for the robot autoload and audit view.

The stage demo runbook lives in `../docs/DEMO_REHEARSAL.md`.

## Commands

```bash
bun install
bun run dev
bun test
bun run lint
bun run build
```

## Contracts

Backend OpenAPI is generated into `../docs/contracts/openapi.json`, then TypeScript
types are generated into `src/modules/api-client/openapi.d.ts`.

```bash
bun run contracts:lint
bun run contracts:generate
```
