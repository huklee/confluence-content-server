# Parser compatibility status

The components originally recorded here as unsupported are implemented in the
editable parser clone at `/Users/huklee/work/confluence-content-parser`. They
remain unsupported by the published `confluence-content-parser` 0.2.1 package
until these local changes are contributed and released upstream.

## Current local support

| Component | Local status | Implementation |
|---|---|---|
| Legacy `tabs` / `tab` macros | Supported through an opt-in adapter; enabled by this web server | `TabsMacro`, `TabMacro`, `register_legacy_tabs()` |
| `thead`, `tbody`, `tfoot` | Supported by the core parser | `TableSection`, `TableSectionType` |
| PlantUML plaintext macro | Source preservation supported through an opt-in adapter; enabled by this web server | `DiagramMacro`, `register_plaintext_diagrams()` |
| Nested expand/code/info in layouts | Supported by the core parser | Existing typed nodes |
| Other unknown app macros/elements | Preserved when `unknown_content="preserve"` is selected | `GenericMacro`, `GenericElement` |

The web server enables lossless preservation and both optional adapters. It
does not execute PlantUML, Mermaid, JavaScript, includes, or other embedded DSL.
Diagram content is displayed as escaped source text.

## Remaining boundaries

- Vendor-specific Cloud Tabs formats that store opaque JSON are preserved as
  generic content but are not interpreted as typed tabs.
- Only explicitly registered plaintext diagram names are typed. The server
  registers `plantuml`; unknown diagram macros remain generic.
- Resolving attachments, users, pages, Jira results, or remote resources is
  outside the parser's responsibility.
- The parser produces an AST, not browser-safe HTML. Renderers must continue to
  escape untrusted content contextually.

## Research notes

- Atlassian describes storage format as **XHTML-based XML**, but explicitly
  notes that it is not XHTML. Its documented table examples place both header
  and data rows inside `tbody`; `thead` support is a compatibility feature for
  imported or app-generated markup.
- Appfire documents legacy nested-bodied tabs as well as newer Cloud Tabs
  representations that may appear as JSON in the legacy editor. Typed support
  therefore remains an opt-in adapter rather than a universal core assumption.
- The PlantUML app vendor confirms that on-prem page storage uses a `plantuml`
  macro with its source in `ac:plain-text-body`. Parsing and preserving this
  source is separate from rendering it.

See [`PRD_CONFLUENCE_CONTENT_PARSER_EXTENSIONS.md`](PRD_CONFLUENCE_CONTENT_PARSER_EXTENSIONS.md)
and the completed implementation checklist at
`/Users/huklee/work/confluence-content-parser/TODO_PRD.md`.

## Sources

- [Atlassian: Confluence Storage Format](https://confluence.atlassian.com/conf89/confluence-storage-format-1387595118.html)
- [Atlassian: Storage Format for Macros](https://confluence.atlassian.com/spaces/CONF51/pages/336169257/Confluence+Storage+Format+for+Macros)
- [Appfire: Switch to the new Tabs macro](https://appfire.atlassian.net/wiki/spaces/CTFCSM/pages/1562542237/Switch+to+the+new+Tabs+macro)
- [PlantUML app vendor: Copy diagram data from storage format](https://stratus-addons.atlassian.net/wiki/spaces/PDFC/pages/1678966785/How+to+manually+copy+diagram+data+from+page+storage+format)
- [`confluence-content-parser` source](https://github.com/Unificon/confluence-content-parser)
