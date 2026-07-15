# Third-party software and data notices

ContextLoop source code is licensed under Apache License 2.0. Dependencies remain under their respective licenses; this file does not replace those license texts.

## Runtime dependencies

| Component | License |
|---|---|
| DataHub Agent Context Kit | Apache-2.0 |
| FastAPI | MIT |
| Pydantic | MIT |
| Uvicorn | BSD-3-Clause |
| React and React DOM | MIT |
| Lucide React | ISC |

## Development dependencies

| Component | License |
|---|---|
| HTTPX | BSD-3-Clause |
| Pytest | MIT |
| pytest-asyncio | Apache-2.0 |
| Ruff | MIT |
| Vite and Vitest | MIT |
| TypeScript | Apache-2.0 |
| Testing Library React | MIT |
| jsdom | MIT |

Exact versions and transitive packages are locked in `uv.lock` and `frontend/package-lock.json`.

## Sample metadata

The project uses DataHub's official `showcase-ecommerce` data pack. The hackathon [resources page](https://datahub.devpost.com/resources) identifies the supplied sample datasets as safe for Apache 2.0 submissions. Platform names visible in the demo are metadata values from that pack; no third-party logos or copied product artwork are distributed.
