# ContextLoop design specification

Accepted concept: [`design/contextloop-concept.png`](../design/contextloop-concept.png)

## Product surface

ContextLoop is a single-screen incident command center. It is a working product surface, not a marketing wrapper.

- Top bar: ContextLoop brand, incident breadcrumb, DataHub connection status, and a direct DataHub link.
- Left rail: source asset, change type, column, environment, run action, and recent runs.
- Center: bounded, source-centered column-impact projection with selected impact edges highlighted.
- Right inspector: severity, evidence counts, business impact, grounded actions, and explicit write-back approval.
- Bottom ledger: Read → Trace → Reason → Prepare → Write back, with elapsed time and status.
- Footer: Codex Auth model, DataHub version, and “No API key required.”

## Design tokens

| Token | Value | Use |
|---|---:|---|
| Canvas | `#07111d` | Application background |
| Panel | `#0a1725` | Primary surfaces |
| Elevated | `#0d1d2c` | Inputs and rows |
| Border | `#2a3c4d` | Hairline panel boundaries |
| Text | `#f1f5f8` | Primary copy |
| Muted | `#93a4b4` | Supporting copy |
| Coral | `#ff5b57` | Risk, selected lineage, primary action |
| Mint | `#62d97a` | Connected and complete states |
| Periwinkle | `#5f89ff` | Selected node and active reasoning |

Typography uses Inter-compatible system sans with compact control text, 14–16px body copy, 18px section headers, and 25–28px incident severity text. Corners are 8–12px, borders are 1px, and shadows are avoided.

## Implementation inventory

- All controls and labels are code-native.
- Icons use one outline family with 1.75px strokes.
- The graph uses SVG curves and node surfaces over a subtle dot grid.
- The desktop native QA viewport is 1600×1000.
- Below 980px, the interface stacks in workflow order and the graph remains horizontally scrollable.
- The live DataHub sample uses `analytics.order_details` and the Looker, Power BI, and Snowflake assets returned by the bounded lineage query. This is an intentional data-grounding deviation from the illustrative asset names in the concept.
