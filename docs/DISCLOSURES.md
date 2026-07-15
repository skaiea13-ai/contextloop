# Build and AI-assistance disclosure

## Submission-period work

ContextLoop source code, visual design, documentation, tests, and sample outputs were created during the DataHub Agent Hackathon submission period beginning July 6, 2026.

## Standard tools and pre-existing components

The project uses standard open-source frameworks and tools under their respective licenses:

- DataHub OSS and DataHub Agent Context Kit
- FastAPI, Pydantic, and Uvicorn
- React, TypeScript, Vite, Lucide, Vitest, and Testing Library
- uv and Node package tooling
- Codex CLI

The official DataHub `showcase-ecommerce` data pack is used as sample metadata. It was not created by this project.

The hackathon resources identify the supplied sample packs as safe for Apache 2.0 submissions. Product and platform names such as Looker, Power BI, and Snowflake appear only as plain-text metadata from that sponsor-provided pack; ContextLoop adds no third-party logos or brand artwork.

## AI assistance

OpenAI Codex assisted with research, design concept generation, implementation, testing, and documentation. Product model execution uses Codex CLI through ChatGPT OAuth. No OpenAI API key or metered OpenAI API backend is used.

`CONTEXTLOOP_FAKE_CODEX=1` is a disclosed deterministic judge and regression mode. It makes no model call, is labeled in the UI, and is not used for the submitted live-OAuth demo evidence.

The design concept in `design/contextloop-concept.png` was generated during this project and is included as an implementation reference, not as a screenshot of the running product.
