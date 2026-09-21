# Other Confluence storage-format features

Audit date: **2026-09-19**

This is the backlog of Confluence storage-format cases not yet represented by the
15 focused samples. It compares Atlassian's documented format with the local
`confluence-content-parser` 0.3 implementation and the local HTML renderer.

Status terms:

- **Typed**: the parser exposes a dedicated model.
- **Preserved**: `unknown_content="preserve"` retains the subtree as a generic
  node, but consumers must decide how to display it.
- **Context required**: faithful rendering needs Confluence data or an external
  service and cannot be derived from storage XML alone.

## Uncovered core elements

| Feature | Current behavior | Work needed | Priority |
| --- | --- | --- | --- |
| Legacy text tags (`b`, `i`, `tt`, `s`, `small`, `big`, `pre`) | Preserved generically; their semantics are not typed | Normalize aliases and add a typed preformatted block | P1 |
| Rich `style` / `class` fidelity | A safe subset of styles is parsed; renderer intentionally does not reproduce arbitrary CSS | Define an allowlist shared by parser consumers | P2 |
| Image presentation attributes | Width, height, alignment, alt, title, and resource are typed; border, thumbnail, class, spacing, and some legacy attributes are not | Preserve all documented metadata and add a resolver contract for attachments | P1 |
| Table metadata (`caption`, `colgroup`, `col`) | Row sections and spans are typed; column definitions are skipped and captions are generic | Add caption and column models without losing source order | P1 |
| Template declarations and variables (`at:declarations`, `at:string`, `at:textarea`, `at:list`, `at:option`, `at:var`) | Preserved generically | Add typed template models and distinguish authoring placeholders from rendered values | P1 |
| Instructional text (`ac:placeholder`, including mention placeholders) | Text is typed, but placeholder type is discarded | Retain the documented type and render it as authoring guidance | P1 |
| Inline comments and markers | Inline-comment markers are intentionally skipped | Preserve comment identifiers and ranges when annotation workflows matter | P2 |
| Less common resource identifiers | Common page, blog, attachment, URL, shortcut, user, space, and content identifiers are typed | Add fixtures for every identifier and malformed/missing attributes | P1 |

## Uncovered built-in macro families

Unknown macros are now losslessly represented by `GenericMacro`, so these do not
vanish. They still lack dedicated semantics or a useful offline presentation.

| Macro family / examples | Offline strategy | Priority |
| --- | --- | --- |
| Legacy layout: `section`, `column` | Convert to a typed responsive column model | P1 |
| Preformatted text: `noformat` | Render as escaped `<pre>` while preserving parameters | P1 |
| Content queries: `children`, `contentbylabel`, `recently-updated`, `contributors`, `contributors-summary` | Render a parameter summary; resolve results only through an injected Confluence client | P1 |
| Media collections: `gallery` | Preserve options and resolve attachment metadata through an injected resolver | P1 |
| Charts and diagrams beyond PlantUML: `chart`, Mermaid/vendor diagram macros | Keep source/options typed; execute only explicitly registered local renderers | P2 |
| External/application content: gadgets, Office viewers, multimedia, Jira results | Render a safe placeholder by default; network-backed resolution must be opt-in | P2 |
| Navigation and metadata macros: labels, spaces, page properties/report, related labels | Add typed parameters, then use an optional site context | P2 |
| Vendor macros | Continue generic preservation and public adapter registration; never hard-code every marketplace app | Ongoing |

### draw.io / diagrams.net

draw.io documents `.drawio` as its native uncompressed XML format. In
Confluence Data Center, saved diagrams are normally page attachments, while the
Embed draw.io macro may reference a master diagram on another page. Storage XML
therefore does not always contain the diagram payload.

The local renderer supports a self-contained extension for testing and offline
preview: a `drawio` structured macro may put uncompressed `<mxfile>` XML in an
`ac:plain-text-body`. Common vertices, labels, colors, and connectors render as
safe local SVG. Compressed diagram pages and attachment-only macros remain
visible as descriptive fallbacks until an attachment resolver or the official
draw.io export engine is configured.

## Rendering and resolution gaps

The storage document frequently identifies a resource without containing enough
data to reproduce Confluence's final view. The renderer therefore needs explicit,
optional resolver interfaces for:

1. attachment URLs and image bytes;
2. page URLs, titles, permissions, and excerpts;
3. user display names and avatars;
4. Jira query execution and issue fields;
5. content-query results such as children and labels;
6. macro engines such as PlantUML or Mermaid.

Resolvers must be disabled by default, bounded by time and output size, and must
not send page content to a public service implicitly. Unresolved content should
remain visible as a descriptive placeholder, never disappear.

## Cloud/editor formats

Confluence Cloud may embed ADF extension payloads and fallback content. The
parser has focused ADF handling for panels and decisions, but arbitrary ADF
nodes, extension attributes, marks, media, and fallback precedence remain an
open compatibility area. Add captured fixtures before expanding this surface;
do not infer a stable schema from one page export.

## Recommended next fixtures

Add focused samples after the comprehensive sample for:

1. legacy text and `pre` / `noformat`;
2. every image source and presentation attribute;
3. caption, column definitions, footer, and nested tables;
4. template declarations, variables, and mention placeholders;
5. legacy section/column layout;
6. content-query and gallery placeholders;
7. all resource identifier variants;
8. representative ADF extension/fallback payloads;
9. malformed namespaces, missing attributes, deep nesting, and size limits;
10. resolver success, timeout, permission failure, and oversized output.

## Sources

- [Atlassian: Confluence Storage Format](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html)
- [Atlassian: Confluence Storage Format for Macros](https://confluence.atlassian.com/spaces/CONF53/pages/411108832/Confluence+Storage+Format+for+Macros)
- [PlantUML: SVG output](https://plantuml.com/svg)
- [PlantUML releases](https://github.com/plantuml/plantuml/releases)
- [draw.io: Save a diagram in various formats](https://www.drawio.com/docs/manual/editor/save-file-formats/)
- [draw.io: Embed a diagram on Confluence Data Center/Server](https://www.drawio.com/docs/integrations/atlassian/confluence/confluence-server/embed-diagram-confluence-server/)
- [draw.io: Diagram attachment retention in Confluence Data Center](https://www.drawio.com/docs/integrations/atlassian/confluence/confluence-server/diagram-retention-confluence/)
