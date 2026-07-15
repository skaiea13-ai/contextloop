# ContextLoop demo script — target duration 2:35

The final recording must show the real application functioning. Keep the browser at 1600×1000, use English narration and UI, and do not include copyrighted music.

## 0:00–0:18 — Problem and product

**Narration:**

“A column change can look safe at the source and still break ten downstream assets. ContextLoop closes that gap: it reads DataHub, surfaces a bounded blast-radius view, assigns grounded actions, and writes the approved decision back as reusable context.”

Show the full ContextLoop screen. Briefly point to DataHub Connected, Codex Auth, and No API key required.

## 0:18–0:38 — Trigger

Show:

- Asset: `analytics.order_details`
- Change: `Drop column`
- Column: `discount_amount`
- Environment: `PROD`

**Narration:**

“This demo uses DataHub's official e-commerce sample. I am proposing to drop `discount_amount` in production.”

Click **Run impact loop**.

## 0:38–1:03 — Context and lineage

Let the five-stage ledger animate.

**Narration:**

“Agent Context Kit first verifies the asset through search, then loads the exact schema field, ownership, governance signals, and prior incident memories. It queries column-level lineage up to three hops, then builds a bounded, source-centered impact projection for the model and interface.”

When complete, show the bounded projection, its overflow count, and the `10 assets` evidence count.

## 1:03–1:35 — Grounded assessment

Pan attention to the right inspector.

**Narration:**

“ContextLoop found Looker, Power BI, and Snowflake dependencies. Codex returns only severity and bounded risk enums; counts, evidence, entity claims, and actions are derived from DataHub. Every recommended owner is constrained to catalog owner names, and asset-level governance is never misrepresented as a column-level claim.”

Briefly highlight the evidence bullets and two action rows.

## 1:35–1:55 — Human gate

Highlight stage five.

**Narration:**

“The agent has completed analysis, but DataHub is unchanged. Write-back is a separate mutation and requires explicit approval.”

Click **Approve & write back to DataHub**.

## 1:55–2:20 — Durable memory

Click the green success link to open the new DataHub document.

**Narration:**

“ContextLoop saves an Analysis document containing the change, impact, evidence, and owned actions. It is related to the source, every asset in this verified impact set, and prior incident documents, creating a navigable memory chain for future humans and agents.”

Show the document title and related assets in DataHub.

## 2:20–2:35 — Close

Return to ContextLoop.

**Narration:**

“ContextLoop turns DataHub's context graph into an operational memory loop—read, trace, reason, act, and write back—using ChatGPT OAuth with no OpenAI API key.”

## Recording acceptance checks

- Duration is under three minutes.
- The real OAuth run is used; `CONTEXTLOOP_FAKE_CODEX` is not set.
- The footer visibly says `Codex Auth`, never `Fixture · no model call`.
- The DataHub success link opens a document created during the recording.
- No terminal token, local user path, email address, or credential is visible.
- Platform names are shown only as metadata from the sponsor-provided `showcase-ecommerce` pack; no third-party logos are added.
- The video is public on YouTube, Vimeo, or Youku only after user approval.
