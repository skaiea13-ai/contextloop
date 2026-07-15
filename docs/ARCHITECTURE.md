# Architecture and trust boundaries

## Components

### React command center

The browser gathers a proposed change, shows the DataHub-derived bounded impact projection and grounded assessment, and keeps the catalog mutation behind a distinct approval button.

### FastAPI orchestrator

The backend owns sequencing and validation. It never gives the model a DataHub token or a mutation tool.

### DataHub Agent Context Kit

Read phase:

- `search` identifies catalog assets.
- `list_schema_fields` verifies the requested column.
- `get_lineage` queries downstream column lineage with a three-hop, 20-result bound.
- `get_entities` batches schemas, platforms, descriptions, and owners.
- `search_documents` finds prior ContextLoop Analysis documents related to the source.
- `grep_documents` retrieves bounded excerpts so previous approved decisions inform the next run.

Write phase:

- `save_document` runs only after an explicit `/api/write-back` request.
- The saved document is related to the source and every asset selected into the bounded impact set.
- The saved document links to prior ContextLoop documents, forming a navigable incident-memory chain.
- The server accepts write-back only for a pending analysis it generated; client-supplied impact data and asset URNs are not trusted.

### Lineage projection boundary

The orchestrator assesses at most the first 10 downstream results returned by DataHub. It represents them as a source-centered star for impact review rather than claiming to reconstruct intermediate multi-hop edge topology. The canvas renders up to six of those downstream nodes and reports the remainder as an overflow count.

### Codex OAuth runner

The model process uses the local Codex CLI and ChatGPT OAuth. It is ephemeral, read-only, schema-constrained, and receives only a compact JSON metadata projection. Email-like values and unsafe structured properties are removed. Descriptions and prior-document excerpts are explicitly marked as untrusted data. Its output contract contains only severity and bounded risk-factor enums. The orchestrator rejects unsupported factors and generates all entity-bearing prose, evidence, counts, actions, and owner assignments deterministically from DataHub context.

## Invariants

1. The model process environment never contains `OPENAI_API_KEY`.
2. A non-ChatGPT Codex login fails closed.
3. Asset and owner names come from DataHub.
4. Affected counts, evidence, and entity-bearing action text are computed from DataHub context rather than model free text.
5. Model reasoning cannot directly mutate DataHub.
6. Write-back requires a second, explicit user action.
7. Success is returned only after the saved document is re-queried and its subtype, title, content markers, and exact related-entity sets match the write request.
8. Free judge mode makes no model call and is visibly distinguished from the OAuth release path.
9. Governance signals apply to the source asset and are never promoted to column-level claims without explicit evidence.
10. New incident memory links to prior related memory as well as affected assets.

## Failure handling

- DataHub unavailable: analysis returns a safe integration error and no model call is made.
- OAuth unavailable: analysis returns `503` and tells the operator to run `codex login`.
- Model timeout or invalid JSON: no assessment or mutation is accepted.
- Write-back failure: the completed assessment remains visible and can be retried; no success state is shown.
