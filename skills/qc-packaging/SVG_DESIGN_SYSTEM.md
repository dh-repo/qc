# SVG Design System

Every SVG diagram produced by the repo-packaging skill must follow this design system exactly. This is the delivery standard.

## Canvas

- **Background:** Full-bleed dark rectangle as the first element: `<rect width="W" height="H" fill="#1e1e2e" rx="12"/>`
- **Width:** 900-920px constant. Height varies with content.
- **viewBox:** `0 0 900 H` where H fits the content. No fixed width/height attributes on the `<svg>` element.
- Self-contained: renders identically on light and dark GitHub themes because the background is opaque.

## Colors (Tailwind-derived, dark-fill + lighter-stroke pattern)

| Role | Fill | Stroke | Use for |
|------|------|--------|---------|
| Background | `#1e1e2e` | -- | SVG canvas |
| Panel/card | `#0f172a` | -- | Inner containers |
| Annotation | `#1a1a2e` | `#334155` | Note boxes, bottom bars |
| Source/origin | `#2563eb` | `#3b82f6` | Input nodes, blob storage |
| Processing | `#4338ca` | `#6366f1` | Indexers, skills, transforms |
| Function/heuristic | `#0d9488` | `#14b8a6` | Azure Functions, heuristic logic |
| Success/correct | `#15803d` | `#22c55e` | Output nodes, correct path |
| Endpoint/consumer | `#9a3412` | `#ea580c` | API consumers, bots |
| Neutral | `#374151` | `#6b7280` | Search service, "none" strategy |
| Error/wrong | `#b91c1c` | `#ef4444` | Error path, unsupported |
| Warning/heuristic | `#b45309` | `#f59e0b` | Merge operations, warnings |
| Decision | `#312e81` | `#6366f1` | Diamond decision nodes |

**Text colors:**

| Role | Color |
|------|-------|
| Primary text | `#e2e8f0` |
| Secondary/muted | `#94a3b8` |
| Dim/tertiary | `#64748b` |
| Labels on colored boxes | `#fff` |
| Sublabels on colored boxes | `rgba(255,255,255,0.85)` |
| Green semantic | `#22c55e` |
| Red semantic | `#ef4444` |
| Amber semantic | `#f59e0b` |

## Typography

Set on root `<svg>` element:
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 H"
     font-family="Segoe UI, -apple-system, sans-serif" font-size="13">
```

| Element | Size | Weight | Notes |
|---------|------|--------|-------|
| Title | 16px | 700 | Top of every diagram |
| Subtitle | 11.5px | normal | Below title, `#94a3b8` |
| Box label | 13-14px | 600 | `#fff` on colored boxes |
| Sublabel | 11.5px | normal | `rgba(255,255,255,0.85)` |
| Note/annotation | 11px | italic | `#94a3b8` |
| Badge text | 10-12px | normal | Status badges |
| Monospace | 9.5-10px | normal | `Cascadia Code, Fira Code, SF Mono, monospace` |

## Shapes

- **Boxes:** Rounded rectangles with `rx="8" ry="8"`, `stroke-width="1.5"`
- **Diamonds:** For decision nodes, rotated 45deg squares
- **Connectors:** `stroke: #9ca3af; stroke-width: 1.5; fill: none`

## Arrowheads

Define in `<defs>` block:
```xml
<defs>
  <marker id="arr" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
    <polygon points="0 0, 8 3, 0 6" fill="#9ca3af"/>
  </marker>
  <marker id="arrG" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
    <polygon points="0 0, 8 3, 0 6" fill="#22c55e"/>
  </marker>
  <marker id="arrR" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
    <polygon points="0 0, 8 3, 0 6" fill="#ef4444"/>
  </marker>
</defs>
```

Applied via `marker-end="url(#arr)"` on `<line>` and `<path>` elements. Use colored variants (`#arrG`, `#arrR`) for semantic paths.

## Style Block

Every SVG uses a `<defs><style>` block with reusable CSS classes (not inline style attributes):

```css
.box { rx: 8; ry: 8; stroke-width: 1.5; }
.label { fill: #fff; font-weight: 600; text-anchor: middle; }
.sublabel { fill: rgba(255,255,255,0.85); font-size: 11.5px; text-anchor: middle; }
.connector { stroke: #9ca3af; stroke-width: 1.5; fill: none; }
.note { fill: #94a3b8; font-size: 11px; font-style: italic; }
.mono { font-family: "Cascadia Code", "Fira Code", "SF Mono", monospace; }
.dim { fill: #64748b; }
.good { fill: #22c55e; }
.bad { fill: #ef4444; }
.warn { fill: #f59e0b; }
```

## Diagram Archetypes

Use the archetype that best fits the concept:

| Archetype | When to use | Layout |
|-----------|-------------|--------|
| Top-to-bottom flow | System architecture, pipelines | Vertical boxes connected by arrows, forks/merges |
| Left/right comparison | Problem illustration, before/after | Center dashed divider, red-left/green-right, "WRONG" vs "CORRECT" labels |
| Decision flowchart | Strategy selection, routing logic | Diamond decision nodes with YES/NO branches |
| Code + annotation | Output format anatomy, schema docs | Left column is styled code, right column is connected annotation boxes |
| Dashboard/map | Test coverage, status overview | Card grid with badge arrays, summary bar, callout boxes |

## Embedding

In the README, always use markdown image syntax with a descriptive alt text sentence:
```markdown
![How data flows from source PDFs through the extraction engine to search index](docs/architecture.svg)
```
