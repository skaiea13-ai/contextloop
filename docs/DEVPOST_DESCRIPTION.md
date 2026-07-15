# Devpost submission copy

## Project name

ContextLoop

## Tagline

Close the schema-change loop with DataHub-grounded impact, action, and memory.

## Challenge

Agents That Do Real Work

## Inspiration

Data teams routinely discover the true blast radius of a schema change only after a dashboard fails. The metadata usually exists—schemas, column lineage, owners, BI dependencies, and documentation—but it is scattered across catalog screens and rarely becomes reusable incident memory. We wanted a single operational loop that could read that context, turn it into owned actions, and write the approved decision back for the next human or agent.

## What it does

ContextLoop accepts a proposed dataset-column change and uses DataHub Agent Context Kit to verify the asset and field, query downstream lineage up to three hops, retrieve a bounded set of affected entities, collect governance signals, and reread prior related ContextLoop documents. A ChatGPT-authenticated Codex runtime classifies severity and bounded risk-factor enums. The server then deterministically renders the entity-bearing assessment, evidence, and owner-bound actions from verified DataHub context. The interface presents a source-centered projection of the returned assets; it does not claim to reconstruct the multi-hop edge topology. Nothing is written automatically: after explicit approval, ContextLoop saves an Analysis document into DataHub and relates it to the source, every asset in the bounded impact set, and prior incident memories.

The verified demo traces `discount_amount` on `analytics.order_details` to 10 Looker, Power BI, and Snowflake assets, then saves a reusable incident-memory document linked to 11 total assets.

## How we built it

- DataHub OSS v1.6.0 and the official `showcase-ecommerce` data pack
- DataHub Agent Context Kit: `search`, `list_schema_fields`, `get_lineage`, `get_entities`, `search_documents`, `grep_documents`, and `save_document`
- FastAPI orchestration with Pydantic contracts
- React, TypeScript, Vite, and SVG lineage rendering
- Codex CLI authenticated through ChatGPT OAuth—no OpenAI API key or metered API backend
- Free-text-free model output, deterministic evidence and entity claims, owner allow-listing, untrusted-context handling, explicit mutation approval, and exact DataHub re-query verification

## Built with

DataHub OSS, DataHub Agent Context Kit, Python, FastAPI, Pydantic, React, TypeScript, Vite, SVG, Codex CLI, and ChatGPT OAuth.

## Challenges we ran into

Real metadata is messier than a mockup. The selected column returned 10 assessed assets across three platforms and a long owner set. Early free-text model output could also introduce unverifiable entity claims. We narrowed the model contract to severity and risk enums, generated every entity-bearing sentence from DataHub context, and fixed the interface against the full live state: long incident titles wrap, the approval gate remains visible, and the canvas reports the 10-asset assessment count without pretending to reconstruct hidden intermediate edges.

The second challenge was separating model reasoning from catalog mutation. We kept `codex exec` read-only and ephemeral, removed API-key fallback entirely, and placed `save_document` behind a distinct approval action.

## Accomplishments we are proud of

- End-to-end live DataHub read, OAuth reasoning, approval, write-back, and document re-query
- A closed memory loop that rereads prior approved incidents and links new memory back to them
- Claims and action owners constrained to retrieved DataHub context
- No OpenAI API key and no metered OpenAI API billing during development or execution
- Free judge mode with live DataHub behavior and a clearly labeled no-model deterministic fixture
- Responsive incident console verified at desktop and mobile viewports
- A public-ready Apache 2.0 repository with locked dependencies, tests, setup instructions, and sample outputs

## What we learned

Context is most valuable when it survives the current execution. Lineage answers “what is connected,” but the closed loop—evidence, decision, owner, action, and durable write-back—is what makes the next response faster and safer.

## What's next

- Trigger analyses from DataHub schema-change events and incidents
- Add governed proposal mode for teams that require metadata-review workflows
- Expand from dropped columns to type changes, nullability changes, and ML feature drift
- Package the workflow as a reusable DataHub Skill
