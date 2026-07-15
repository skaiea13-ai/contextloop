# ContextLoop project rules

## Non-negotiable model access

- All model-backed development, testing, and product execution must use the local Codex CLI authenticated with ChatGPT OAuth (`codex login status` must report `Logged in using ChatGPT`).
- Do not add `OPENAI_API_KEY`, the OpenAI SDK, direct OpenAI HTTP calls, or any API-key fallback.
- The backend must remove `OPENAI_API_KEY` from the child-process environment before invoking `codex exec`.
- Deterministic fixtures are allowed for unit and browser regression tests because they make no model call. At least one release verification must exercise the real OAuth path.

## DataHub hackathon submission gates

- Target: “Agents That Do Real Work” in Build with DataHub: The Agent Hackathon.
- Use DataHub OSS plus `datahub-agent-context` for search, schema inspection, lineage traversal, entity context, and `save_document` write-back.
- Keep the repository Apache-2.0 licensed, public-ready, and free of secrets or personal credentials.
- Submission materials must be in English and include: working project URL or clear runnable repository, public repository URL, concise description, setup/testing instructions, sample outputs, and a public demonstration video under three minutes.
- The video and written claims must match behavior verified in the actual runtime.
- Do not join the hackathon, accept terms, publish a repository, upload a video, or submit to Devpost without the user's explicit approval.

## Completion checks

- Run Python tests and lint, frontend tests and production build, OAuth preflight, DataHub health, a live impact analysis, a confirmed DataHub document write-back, and browser checks at desktop and mobile sizes.
- Verify generated output contains only assets and owners grounded in the retrieved DataHub context.
- Keep the design aligned with `design/contextloop-concept.png` and document intentional deviations.
