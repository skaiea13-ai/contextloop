# Release verification evidence

Latest verification date: August 10, 2026<br>
Intended platform: desktop browser on macOS or Linux with a Docker-compatible runtime

## Automated checks

- Python 3.11 dependency resolution completed from `uv.lock` using copy mode for external-drive compatibility.
- Ruff completed with no findings.
- Pytest completed with 37 passing tests, covering the OAuth environment boundary, deterministic grounding, bounded DataHub context projection, single-job admission, short display-ID collision isolation, per-analysis write-back capabilities, serialized DataHub mutation, concurrent approval, client disconnect recovery, idempotent retry, and exact server-side write-back verification.
- Vitest completed with three passing interface flows: analyze then approve, write-back failure then retry, and the visible deterministic-fixture label. The suite also passed three additional repeat runs.
- TypeScript compilation and the Vite production build completed successfully.
- Shell scripts pass Bash syntax validation, and `scripts/dev.sh` passes ShellCheck. The launcher waited for `/api/health`, started Vite on the strict 5173 port, returned a healthy ChatGPT OAuth/DataHub response, and cleaned up both processes on interruption. Its occupied-8000 path also failed immediately instead of starting the frontend against an unintended backend.
- `examples/impact-analysis.json` passes strict JSON parsing.
- `./scripts/verify.sh` re-confirmed the full static, test, production-build, ChatGPT OAuth, and DataHub gate on July 16 after the public repository URLs were added.
- `./scripts/verify.sh` re-confirmed Ruff, all 37 Pytest tests, all three Vitest flows, the TypeScript build, ChatGPT OAuth, and DataHub health on August 10.
- On July 12, a fresh local clone completed judge-mode bootstrap, locked dependency installation, the full verification suite, and a clean working-tree check while each script was invoked from outside the clone. That clean-clone exercise was not repeated on July 15.

DataHub emits its documented experimental-SDK warning for `datahub.sdk` and Agent Context Kit `save_document`; it does not fail any check.

## Live ChatGPT OAuth path

- `codex login status`: ChatGPT authentication confirmed.
- Backend health: DataHub connected, ChatGPT OAuth connected, `api_key_required` false.
- DataHub OSS images: v1.6.0, healthy.
- Agent Context Kit read: asset search verification, exact `discount_amount` schema match, ten assets selected into the bounded downstream impact set, sixteen safe source-governance signals, and three prior related ContextLoop documents.
- Grounded analysis: run `CL-8736`, model `gpt-5.6-sol`, `auth_mode` `chatgpt_oauth`, severity `P1`.
- The model returned only bounded severity/risk signals; all asset names, counts, evidence, and entity-bearing prose were generated from the retrieved DataHub context. Owner assignments use sanitized stable aliases for retrieved owner records.
- Timings: 226 ms context read, 725 ms lineage and memory projection, 11,922 ms OAuth reasoning.
- Human gate: the Analysis document did not exist until the separate approval action.
- Write-back: `urn:li:document:shared-b90b866f-cf9c-404c-ad33-03f88d9c2248` was re-read through the DataHub SDK as a published `Analysis` with the exact title/content markers, eleven related assets, and three related prior documents.
- Sanitized representative output based on the verified run is preserved in `examples/impact-analysis.json` and `examples/incident-memory.md`; raw governance labels are replaced by the same bounded count now emitted by the hardened renderer.
- `./scripts/verify_live.sh` independently completed the same release gate on run `CL-D74B`: zero matching document before approval, then published status, dynamic content, and exact relationship re-query verification after approval.
- On August 8, `./scripts/verify_live.sh` independently passed again on run `CL-682A`: ChatGPT OAuth, ten affected assets, five grounded actions, approval-gated write-back, verified DataHub URL, and successful SDK re-read.
- On August 10, the hardened `./scripts/verify_live.sh` passed on run `CL-B1E4`: the protected response issued a 256-bit write-back capability, the approval upserted the preassigned `urn:li:document:shared-contextloop-b1e440d523c5492896d3d42dfe551481`, and the SDK re-read the exact published document with ten affected assets and five grounded actions. Regression tests also proved that concurrent approval performs one save and a retry returns the same result and document target.
- After client-disconnect recovery and global DataHub mutation serialization were added, the exact final tree passed the live gate again on run `CL-D5E1`; `urn:li:document:shared-contextloop-d5e130f41407463ba4427dcbd7d52c5f` was re-read as the approved published document with ten affected assets and five grounded actions.

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
- The August 8 desktop pass used real-OAuth run `CL-99FA`. It completed with ten affected assets, twelve owners, eight BI assets, and five grounded actions; the separate approval created and opened the exact published DataHub `Analysis` document for that run. A second real-OAuth pass at an emulated 390×844 viewport reached its approval gate with no page-level horizontal overflow and no console warnings or errors; that mobile pass was intentionally not written back.

QA screenshots are intentionally not stored in the repository because they are test artifacts, not required submission assets. The public demo video must show the same verified runtime state.

## Final local demo candidate

- The August 8 real-OAuth browser pass produced run `CL-99FA`, with ten downstream assets, twelve retrieved owners, eight BI assets, five grounded actions, and zero prior incident memories returned for that run.
- The explicit approval action created `urn:li:document:shared-d68eb433-1451-491a-8fe3-832b42f91482`; the browser opened that exact document as a published `Analysis` and displayed its impact, owned actions, and related assets. The narration accurately states that prior incident memories are linked only when retrieved.
- The local final candidate is 155.000 seconds, 1600×1000 at 30 fps, with H.264 video, stereo AAC narration, and an embedded English subtitle stream.
- Full decoding, SHA-256 verification, twelve representative-frame inspections, exact subtitle round-trip extraction, and black-frame detection passed. Mean audio level is -16.6 dB with a -1.2 dB peak; all seven narration sections finish inside their assigned timeline windows.
- Final SHA-256: `eae90cb12aa691679997c2876fd403a718503f4fcb8fc903bc8cb3301496f627`.
- The video contains only page-content captures from the actual OAuth run and local DataHub document. It contains no terminal, browser profile, local filesystem path, email, credential, copyrighted music, or fixture-mode label.
- The reviewed local artifact remains excluded from Git. It was originally published at `https://youtu.be/VW5ZLLwqPoQ` with manually uploaded English captions and a YouTube AI-use disclosure for the synthetic narration; that upload is now unlisted after the public replacement below.

## Public calm-Aiden replacement

- The replacement is 164.960 seconds, 1920×1080 at 30 fps, with H.264 video and mono 48 kHz AAC narration. Its SHA-256 is `badbcbfcdc1d4b9a6410f632a93372a37dae56c5a5cbabecc37bcc8b86d7fb3c`.
- The continuous application footage shows real-OAuth run `CL-AAD1`: DataHub context retrieval, ChatGPT OAuth reasoning through Codex CLI, explicit approval, write-back, and the exact new DataHub document opened after creation.
- Full decoding passed. Privacy review covered 33 sampled frames and found no credentials, email, private filesystem path, or personal phone number; the MP4 contains no subtitle, attachment, chapter, or unexpected metadata stream.
- The calm Aiden narration was generated locally with Qwen3-TTS and is disclosed in the YouTube description. English captions were manually uploaded from the reviewed SRT.
- The replacement is public at `https://youtu.be/rbLMs7jN6eY`; YouTube reported no copyright-check issue. Devpost embeds this new video ID and no longer embeds the previous upload.

## Publication status

- Public project URL: `https://github.com/skaiea13-ai/contextloop`.
- Public repository URL: `https://github.com/skaiea13-ai/contextloop`.
- Public Devpost submission: `https://devpost.com/software/contextloop`; Devpost displayed `Project submitted!`, embedded the public demo video, and linked the public GitHub repository.
- Anonymous HTTP, raw-license, and GitHub API checks confirmed public access, Apache-2.0 detection, and pre-submission public head `668176d02fe7f0e31419dcae524f2eb55972ced0`.
- Public demonstration video: `https://youtu.be/rbLMs7jN6eY`; YouTube reports a 2:45 duration and no copyright-check issues. The previous upload is unlisted.
- Public commit-author identity: isolated release commits use the generic GitHub noreply identity `ContextLoop Release`.
