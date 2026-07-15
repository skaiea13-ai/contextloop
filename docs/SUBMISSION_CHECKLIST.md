# Devpost submission checklist

Source of truth: [Build with DataHub: The Agent Hackathon](https://datahub.devpost.com/) and its [official rules](https://datahub.devpost.com/rules).

## Eligibility and timing

- [ ] Entrant is registered on Devpost and explicitly accepts the official rules.
- [ ] Submission is completed before August 10, 2026 at 5:00 PM EDT.
- [x] All work claimed for the submission was created during the submission period.
- [x] Any pre-existing framework or generated asset is disclosed.

## Required project behavior

- [x] Working software application using DataHub OSS.
- [x] Agent Context Kit reads search, schema, lineage, ownership, and entity context.
- [x] Explicit approval precedes mutation.
- [x] Agent writes a related incident-memory document back to DataHub.
- [x] OAuth-only model execution; no OpenAI API key or metered OpenAI API billing.
- [x] Free judge path requires no model account and makes no model call.
- [x] Release verification recorded in `docs/RELEASE_EVIDENCE.md`.

## Required submission artifacts

- [x] Public project URL and public repository with clear, complete setup instructions: `https://github.com/skaiea13-ai/contextloop`.
- [x] Submission package contains all source, assets, locked dependencies, and setup instructions.
- [x] Apache 2.0 `LICENSE` at repository root.
- [x] Repository About metadata and the anonymous GitHub API identify the license as Apache-2.0.
- [x] English project description and testing instructions.
- [ ] Public YouTube, Vimeo, or Youku demo video under three minutes.
- [x] Reviewed 155-second local video shows the actual real-OAuth project functioning on its intended desktop browser; only public upload remains.
- [x] Sample outputs present under `examples/`.
- [x] No secret, personal token, local credential, private dataset, or machine-local path in the repository or working diff.
- [x] Public history is isolated to a generic GitHub noreply release identity and contains no personal author history.
- [ ] Project remains freely available to judges through the end of judging.
- [x] Final local video review found no copyrighted music, credentials, private paths, or unrelated third-party material.

## Final consistency audit

- [x] Reviewed local video, README, runtime screenshots, and locked Devpost text make consistent product claims; only the public video and Devpost URLs remain pending.
- [x] Every visible asset and owner in the verified demo comes from DataHub.
- [x] The documented model path says ChatGPT OAuth via Codex CLI, not OpenAI API.
- [x] Judges can understand the value and run the project without private assistance.

## Optional bonus

- [ ] A meaningful contribution has been accepted by an official DataHub open-source repository.
- [x] No upstream contribution or bonus claim appears in the submission package without a public contribution URL.
- [ ] Most Valuable Feedback section is completed with the verified Agent Context Kit Document-hydration report.
