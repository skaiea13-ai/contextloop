# Official submission requirements matrix

Sources: [hackathon overview](https://datahub.devpost.com/) and [official rules](https://datahub.devpost.com/rules). Verified on July 16, 2026.

| Official requirement | ContextLoop evidence | Current status |
|---|---|---|
| Working software application using DataHub OSS and at least one approved agent interface | DataHub OSS v1.6.0 plus Agent Context Kit operations in `backend/contextloop/datahub_service.py` | Complete and runtime-verified |
| Project fits a challenge category | `Agents That Do Real Work`; searches and reads DataHub, reuses prior memory, takes grounded action, and writes linked approved memory back | Complete |
| Project must install and run consistently as depicted | Locked dependencies, `scripts/bootstrap.sh`, `scripts/dev.sh`, automated verification, and `docs/RELEASE_EVIDENCE.md` | Complete on intended desktop platform |
| Easy-access Project URL | `https://github.com/skaiea13-ai/contextloop`; free judge mode requires no model account | Complete and anonymously reachable |
| Public code repository containing all source, assets, and full instructions | Public repository includes README, design asset, docs, examples, lockfiles, and the verified clone command | Complete and anonymously cloneable |
| Apache 2.0 license detectable in the repository About area | Root `LICENSE`, GitHub repository metadata, and anonymous API response identify Apache-2.0 | Complete |
| English project description | `docs/DEVPOST_DESCRIPTION.md` | Complete |
| Public demonstration video under three minutes | Reviewed 155-second final cut from the real OAuth run | Local artifact complete; public upload and URL pending |
| Video shows the Project functioning on its intended device | Final cut covers live DataHub read, lineage, OAuth reasoning, approval, write-back, and document view | Recording and review complete; public upload pending |
| Video contains no unlicensed copyrighted music or third-party material | Decode, frame, audio, subtitle, and privacy review found no copyrighted music or unrelated third-party material | Complete |
| Sample outputs are recommended | Verified OAuth output and exact saved DataHub document under `examples/`, including asset and prior-document relations | Complete |
| Project remains free and unrestricted for judging through the judging period | `CONTEXTLOOP_FAKE_CODEX=1` exercises live DataHub behavior with no account and no model call | Runtime complete; depends on keeping the public repository available through August 31, 2026 |
| All submission materials are in English or translated | UI, README, testing instructions, Devpost copy, narration, and embedded subtitle track are English | Complete |
| New work was created during the submission period; pre-existing work is disclosed | `docs/DISCLOSURES.md` records project-period work, standard frameworks, the official sample pack, generated concept, and AI assistance | Complete, subject to entrant attestation |
| Entrant owns the submission and respects third-party licenses and rights | Apache-2.0 project license plus disclosure of open-source dependencies and official sample data | Entrant attestation required |
| Submission entered before August 10, 2026 at 5:00 PM EDT | Deadline is August 11, 2026 at 6:00 AM KST | Devpost registration and final submission pending |

## User-specific model boundary

This is stricter than the hackathon requirement: real model execution accepts only a ChatGPT-authenticated Codex CLI session. It has no OpenAI SDK, direct OpenAI HTTP call, API-key fallback, or metered OpenAI API billing. The model can return only severity and bounded risk-factor enums; entity-bearing output is derived from DataHub. Free judge mode makes no model call and is visibly labeled as a fixture.
