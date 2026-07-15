# Release verification evidence

Verification date: July 15, 2026<br>
Intended platform: desktop browser on macOS or Linux with a Docker-compatible runtime

## Automated checks

- Python 3.11 dependency resolution completed from `uv.lock` using copy mode for external-drive compatibility.
- Ruff completed with no findings.
- Pytest completed with 25 passing tests, covering the OAuth environment boundary, deterministic grounding, DataHub context projection, and exact server-side write-back verification.
- Vitest completed with three passing interface flows: analyze then approve, write-back failure then retry, and the visible deterministic-fixture label. The suite also passed three additional repeat runs.
- TypeScript compilation and the Vite production build completed successfully.
- Shell scripts pass Bash syntax validation, and `scripts/dev.sh` passes ShellCheck. The launcher waited for `/api/health`, started Vite on the strict 5173 port, returned a healthy ChatGPT OAuth/DataHub response, and cleaned up both processes on interruption. Its occupied-8000 path also failed immediately instead of starting the frontend against an unintended backend.
- `examples/impact-analysis.json` passes strict JSON parsing.
- `./scripts/verify.sh` re-confirmed the ChatGPT OAuth preflight and DataHub health after the July 15 hardening changes.
- On July 12, a fresh local clone completed judge-mode bootstrap, locked dependency installation, the full verification suite, and a clean working-tree check while each script was invoked from outside the clone. That clean-clone exercise was not repeated on July 15.

DataHub emits its documented experimental-SDK warning for `datahub.sdk` and Agent Context Kit `save_document`; it does not fail any check.

## Live ChatGPT OAuth path

- `codex login status`: ChatGPT authentication confirmed.
- Backend health: DataHub connected, ChatGPT OAuth connected, `api_key_required` false.
- DataHub OSS images: v1.6.0, healthy.
- Agent Context Kit read: asset search verification, exact `discount_amount` schema match, ten assets selected into the bounded downstream impact set, sixteen safe source-governance signals, and three prior related ContextLoop documents.
- Grounded analysis: run `CL-8736`, model `gpt-5.6-sol`, `auth_mode` `chatgpt_oauth`, severity `P1`.
- The model returned only bounded severity/risk signals; all asset names, owner assignments, counts, evidence, and entity-bearing prose were generated from the retrieved DataHub context.
- Timings: 226 ms context read, 725 ms lineage and memory projection, 11,922 ms OAuth reasoning.
- Human gate: the Analysis document did not exist until the separate approval action.
- Write-back: `urn:li:document:shared-b90b866f-cf9c-404c-ad33-03f88d9c2248` was re-read through the DataHub SDK as a published `Analysis` with the exact title/content markers, eleven related assets, and three related prior documents.
- Exact sanitized output is preserved in `examples/impact-analysis.json` and `examples/incident-memory.md`.
- `./scripts/verify_live.sh` independently completed the same release gate on run `CL-D74B`: zero matching document before approval, then published status, dynamic content, and exact relationship re-query verification after approval.

## Free judge path

On July 15, the backend was launched with `CONTEXTLOOP_FAKE_CODEX=1`. The health response reported `deterministic_fixture`, no model call, and a live DataHub connection. The browser exercised analysis, the approval gate, approved write-back, and the resulting success state. The earlier mobile run `CL-EB77` returned ten assets in the bounded impact set, five deterministic evidence bullets, and five actions.

## Browser verification

- In-app Browser QA on July 15 covered the full real-OAuth trigger → bounded impact projection → approval → write-back success flow at 1600×1000 and 390×844 (run `CL-0E52`).
- The source-centered projection and its overflow indicator rendered as intended at both sizes.
- Before approval, a DataHub document search for `CL-0E52` returned zero matches. After the separate approval click, the UI exposed the saved-document link and the SDK re-read a published `Analysis` with eleven related assets and three prior documents.
- The mobile viewport reported 390 px inner width and 375 px document width, with no page-level horizontal overflow.
- The real-model deterministic headline and five grounded action rows wrap without clipping.
- The approval gate remains reachable after five long action rows.
- The five-stage ledger is horizontally scrollable on mobile without expanding the page width.
- No browser console warning or error was present after the real OAuth flow.
- All runtime date and time labels are forced to English.

QA screenshots are intentionally not stored in the repository because they are test artifacts, not required submission assets. The public demo video must show the same verified runtime state.

## Final local demo candidate

- A second real-OAuth browser pass on July 15 produced run `CL-2EA4`, with ten downstream assets, twelve retrieved owners, eight BI assets, five grounded actions, and two prior incident memories returned for that run.
- The explicit approval action created `urn:li:document:shared-b131747d-e411-4e50-957f-2c8d7ebafa02`; the browser opened that exact document as a published `Analysis` and displayed its impact, actions, related assets, and prior documents.
- Browser review found and fixed a release bug in the success-link route. DataHub 1.6.0 requires the full document URN at `/document/urn:li:document:...`; the API now preserves the full URN, and both the write-back test and `scripts/verify_live.sh` enforce it.
- After that fix, `./scripts/verify_live.sh` passed again on run `CL-D339`, including zero pre-approval matches, ten affected assets, five grounded actions, exact SDK re-read, and `datahub_url_verified: true`.
- The local final candidate is 155.000 seconds, 1600×1000 at 30 fps, with H.264 video, stereo AAC narration, and an embedded English subtitle stream.
- Full decoding, SHA-256 verification, eleven representative-frame inspections, subtitle round-trip extraction, and black-frame detection passed. Mean audio level is -17.9 dB with a -1.0 dB peak; all seven narration sections finish inside their assigned timeline windows.
- The video contains only page-content captures from the actual OAuth run and local DataHub document. It contains no terminal, browser profile, local filesystem path, email, credential, copyrighted music, or fixture-mode label.
- The reviewed local artifact is intentionally excluded from Git. Public upload remains subject to explicit user approval.

## Publication status

- Public project URL: pending publication and explicit user approval.
- Public repository URL: pending publication and explicit user approval.
- Public demonstration video: reviewed local final candidate complete; public upload and URL pending explicit user approval.
- Public commit-author identity: the isolated one-commit release uses a generic GitHub noreply identity; publication remains pending explicit user approval.
