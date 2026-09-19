# PRD: Lossless and extensible Confluence Storage Format parsing

**Status:** Draft  
**Target project:** `confluence-content-parser`  
**Baseline:** 0.2.1 / upstream commit `72432ea`  
**Proposed release:** 0.3.x for additive APIs; 1.0 for any default-policy change

**Local implementation status:** Completed as 0.3.0 on 2026-09-19; see
`/Users/huklee/work/confluence-content-parser/TODO_PRD.md` for timestamped
progress and quality gates.

## Summary

`confluence-content-parser` should preserve content it does not understand,
support common table section wrappers, and expose a public registration API for
app-specific macros. The parser should add optional adapters for legacy tabbed
content and plaintext diagram macros, but it must not execute third-party code,
fetch resources, or render diagrams.

The primary product requirement is **no silent content loss**. Unknown macros
and elements currently add string diagnostics and disappear from the AST. This
is especially damaging for bodied macros because all nested text disappears as
well. A generic lossless representation is more valuable than attempting to
hard-code every macro in the Confluence ecosystem.

## Research findings

| Area | Finding | Product implication |
|---|---|---|
| Storage format | Atlassian calls the format XHTML-based XML, but explicitly says it is not XHTML. | Do not assume every HTML element is canonical, but preserve safe structural wrappers. |
| Tables | Atlassian's documented tables use `table > tbody > tr` and put `th` cells in `tbody`. Parser 0.2.1 supports those nodes, row/column spans, and nested supported macros, but not `thead`. | Add `thead`/`tfoot` compatibility without claiming Atlassian emits them by default. |
| Unknown content | Parser dispatch is held in fixed private `_element_parsers` and `_macro_parsers` dictionaries. Unknown nodes become diagnostics and are omitted. | Add generic nodes plus public extension registration. |
| Tabs | Tabs are app-provided, and vendor formats differ. Appfire documents legacy nested-bodied macros and a newer Cloud Tabs representation that may appear as JSON in the legacy editor. | Preserve all variants generically; make typed adapters opt-in and vendor/version aware. |
| Diagram macros | A PlantUML vendor documents `ac:name="plantuml"` with DSL in `ac:plain-text-body`. | Preserve title, parameters, and exact plaintext. Rendering belongs outside this library. |
| Macro bodies | Atlassian requires plaintext macro bodies to use CDATA and distinguishes plaintext from rich-text bodies. | Generic macro nodes must retain body kind and whitespace exactly. |
| Error policy | Repository documentation describes non-strict collection as the default, while `ConfluenceParser.__init__` currently defaults `raise_on_finish=True`. | Clarify and test policy semantics before changing defaults. |

## Problem statement

Consumers use the parser for migration, search, RAG ingestion, auditing, and
transformation. In these workflows, dropping an unknown subtree is worse than
returning a partially typed representation. Today:

1. `<thead>` produces `unknown_element:thead`; its header row is omitted in
   tolerant mode and the entire parse raises in strict mode.
2. A `tabs` macro is omitted with `unknown_macro:tabs`, including nested tab
   titles and rich-text bodies.
3. A `plantuml` macro is omitted with `unknown_macro:plantuml`, including the
   plaintext diagram source.
4. Applications cannot register support without subclassing or modifying
   private parser dictionaries.
5. String-only diagnostics have no stable severity, location, namespace, or
   machine-readable context.

## Goals

- Preserve every well-formed input subtree in the AST, even when no typed
  parser exists.
- Parse `thead`, `tbody`, and `tfoot` without losing rows or cell metadata.
- Preserve unknown macro attributes, ordered parameters, rich bodies, plaintext
  bodies, and nested content.
- Provide a documented public API for custom element and macro parsers.
- Offer optional typed adapters for the supplied legacy tabs and PlantUML
  shapes without coupling the core parser to a specific renderer.
- Maintain deterministic text extraction and traversal.
- Provide structured, actionable diagnostics.

## Non-goals

- Rendering HTML, tabs, UML, Mermaid, or other diagrams.
- Executing macro DSL, JavaScript, includes, or remote requests.
- Resolving Confluence users, pages, attachments, or Jira queries.
- Guaranteeing semantic support for every Marketplace app.
- Treating arbitrary XHTML as trusted or browser-safe HTML.
- Converting Cloud ADF or vendor JSON into Storage Format in this phase.

## Users and use cases

- **Migration tooling:** retain unsupported app content for later conversion.
- **Search/RAG pipelines:** index text inside unknown bodied macros.
- **Auditing tools:** identify macro names, parameters, and source locations.
- **Application developers:** register typed support for organization-specific
  or Marketplace macros without forking the parser.
- **Renderers/exporters:** distinguish typed, generic, and unsupported content
  and choose their own safe fallback.

## Functional requirements

### P0 — Lossless generic nodes

#### FR-1: Generic elements

Add an `UnknownElement` (or `GenericElement`) container node with:

```python
class GenericElement(ContainerElement):
    local_name: str
    namespace: str | None
    attributes: dict[str, str]
    children: list[Node]
```

- Unknown well-formed elements must preserve parsed children and text/tail
  order rather than returning `None`.
- `walk()`, `find_all()`, and `to_text()` must include descendants.
- Diagnostics must identify the generic fallback without describing the data as
  lost.

#### FR-2: Generic macros

Add a `GenericMacro` node capable of representing both `ac:macro` and
`ac:structured-macro`:

```python
class MacroBodyKind(str, Enum):
    NONE = "none"
    RICH_TEXT = "rich-text"
    PLAIN_TEXT = "plain-text"

class MacroParameter(BaseModel):
    name: str
    value: str | None = None
    children: list[Node] = []

class GenericMacro(ContainerElement):
    name: str
    storage_element: str
    schema_version: str | None
    macro_id: str | None
    parameters: list[MacroParameter]
    body_kind: MacroBodyKind
    plain_text_body: str | None
    children: list[Node]
    attributes: dict[str, str]
```

- Parameter order and duplicate parameter names must be preserved; therefore a
  list is required even if a convenience dictionary view is also exposed.
- Rich-text bodies must recursively parse into child nodes.
- Plaintext bodies must retain leading/trailing whitespace and newlines.
- CDATA boundaries do not need to be retained, but their text must be exact.
- `to_text()` must include a useful label and the preserved body. It must never
  execute or interpret the body.

#### FR-3: Unknown-content policy

Introduce an explicit policy independent of XML syntax errors:

```python
ConfluenceParser(
    unknown_content="preserve",  # "preserve" | "error" | "drop"
    raise_on_finish=False,
)
```

- `preserve`: produce generic nodes plus warning diagnostics.
- `error`: preserve the current strict failure behavior.
- `drop`: legacy opt-in behavior, with data-loss diagnostics.
- For 0.3.x, retain backward-compatible defaults and emit a deprecation notice
  if a future default will change. For 1.0, make `preserve` the default.
- XML that is not well formed remains an error and must not produce a
  misleading partial AST.

### P0 — Table section compatibility

#### FR-4: Table wrappers

- Recognize `thead`, `tbody`, and `tfoot`.
- Preserve all `tr`, `th`, `td`, `rowspan`, `colspan`, styles, and nested nodes.
- Recommended model: `TableSection(ContainerElement)` with a
  `TableSectionType` enum (`head`, `body`, `foot`).
- If changing the existing `tbody -> Fragment` shape is judged too disruptive,
  `TableSection` may subclass `Fragment` for transitional compatibility.
- `Table.to_text()` must keep logical row order across all sections.
- A table containing a supported nested status macro or user link must parse
  without diagnostics.

### P1 — Public extension API

#### FR-5: Parser registration

Expose supported public hooks rather than requiring mutation of private maps:

```python
parser = ConfluenceParser(
    macro_parsers={"plantuml": parse_plantuml},
    element_parsers={"custom-element": parse_custom_element},
)

# Optional imperative form before parse():
parser.register_macro("tabs", parse_tabs)
parser.register_element("thead", parse_table_section)
```

- Callback types and context objects must be public and fully typed.
- Registration must reject accidental replacement of built-ins unless
  `replace=True` is explicit.
- Parser instances must not share mutable registries.
- Registration during an active parse is unsupported and must fail clearly.
- Documentation must include one rich-body and one plaintext macro example.

#### FR-6: Structured diagnostics

Add a typed diagnostic model:

```python
class Diagnostic(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    path: str | None
    local_name: str | None
    namespace: str | None
```

- Retain a compatibility view of current strings for at least one minor
  release.
- Distinguish `preserved_unknown_macro` from `dropped_unknown_macro`.
- Include a stable element path or equivalent source context.

### P1 — Plaintext diagram preservation

#### FR-7: Diagram source node/adapter

Provide either a built-in `DiagramMacro` or an example adapter built on the
public registry:

```python
class DiagramMacro(Node):
    engine: str
    macro_name: str
    title: str | None
    source: str
    parameters: list[MacroParameter]
```

- The initial verified alias is `plantuml`; `plantumlcloud` may be supported
  when backed by a vendor fixture.
- Mermaid and other names must be opt-in aliases, not assumed equivalent.
- Source must round-trip as text with whitespace preserved.
- No subprocess, network request, include expansion, SVG generation, or image
  rendering may occur in this package.
- `to_text()` should expose the title and source so indexing does not lose it.

### P2 — Vendor-aware tabs adapters

#### FR-8: Legacy nested tabs

Add an optional adapter for the supplied nested rich-body representation:

```python
class TabsMacro(ContainerElement):
    orientation: str | None
    tabs: list[TabMacro]

class TabMacro(ContainerElement):
    title: str
    children: list[Node]
```

- Nested formatting and block nodes must remain traversable.
- Tab order and titles must be preserved.
- Missing titles must generate a warning, not discard the body.
- Nested tabs must be supported recursively or rejected with a precise
  diagnostic—never silently flattened.
- Keep this adapter outside the core default registry until fixtures identify
  the vendor, hosting model, and macro version it represents.
- JSON-backed Cloud Tabs are out of scope until their schema and stability are
  documented; they must still survive as `GenericMacro` content/parameters.

## API and compatibility requirements

- Existing node classes and `find_all()` behavior remain available.
- New node types are exported from `confluence_content_parser.__init__`.
- Existing `raise_on_finish` behavior must be documented accurately. The
  source default and README example currently disagree and need a regression
  test.
- Existing string diagnostics remain readable during the transition.
- Parsing the same document repeatedly must produce equivalent models and
  diagnostics.
- Parser calls must be safe on separate parser instances. Thread safety of a
  shared instance must either be implemented or explicitly documented as
  unsupported because diagnostics are mutable instance state.

## Security and resource limits

- Generic preservation must never mean evaluation.
- Do not resolve external XML entities or permit filesystem/network access.
- Diagram includes, URLs, sprites, and remote imports remain opaque text.
- Add configurable maximum XML bytes, nesting depth, node count, parameter
  count, and plaintext-body bytes, with deterministic limit diagnostics.
- Attribute and body data remain untrusted; downstream renderers are
  responsible for contextual escaping.
- Tests must cover entity expansion, deeply nested macros, oversized plaintext
  bodies, and script-like strings inside CDATA.

## Acceptance criteria

1. The exact example 12 produces either typed `TabsMacro`/`TabMacro` nodes when
   its adapter is enabled or a `GenericMacro` tree containing both titles and
   both tab bodies. No text is lost.
2. The exact example 13 parses without diagnostics; its first table section
   contains the header row, `colspan=2` and `rowspan=2` survive, and nested
   statuses/users remain typed.
3. The exact example 14 continues to parse without diagnostics and retains the
   two layout cells, expand title, YAML source, and info body.
4. The exact example 15 produces a `DiagramMacro` when enabled, otherwise a
   `GenericMacro`; the complete `@startuml` through `@enduml` source survives.
5. Unknown rich-body and plaintext macros have traversal and text-extraction
   tests proving no subtree loss.
6. Strict/error mode raises a structured exception containing diagnostic codes
   and paths.
7. Existing 0.2.1 supported-element fixtures remain green.
8. Added parsing overhead is no more than 10% on the project's representative
   benchmark corpus when no custom adapters are enabled.
9. Public documentation includes migration notes and extension examples.

## Test plan

- Add fixtures for examples 12–15 exactly as received.
- Unit-test every new node's validation, `get_children()`, `walk()`, and
  `to_text()` behavior.
- Parameterize unknown policy tests across element and macro cases.
- Test mixed table sections and direct `tr` children.
- Test duplicate/default (`ac:name=""`) and resource-valued parameters.
- Test nested known macros inside generic macros and unknown macros inside known
  rich bodies.
- Test CDATA containing XML-looking text, Unicode, quotes, and indentation.
- Test independent registries across parser instances and collision handling.
- Add property/fuzz tests asserting well-formed input never loses text solely
  because a tag or macro name is unknown.

## Delivery plan

### Milestone 1: Prevent loss (0.3.0)

- Generic element and macro nodes
- Explicit unknown-content policy
- `thead`/`tfoot` parsing
- Structured diagnostics with legacy compatibility
- Exact fixtures for examples 12–15

### Milestone 2: Make extension public (0.3.x)

- Typed registration API
- Extension author documentation
- PlantUML preservation adapter example
- Resource-limit configuration

### Milestone 3: Vendor adapters (optional package or extras)

- Verified legacy tabs adapter
- Verified diagram aliases
- Vendor/version fixture matrix
- No rendering dependencies in the core package

## Success measures

- Zero text loss for unknown well-formed macro bodies in the fixture corpus.
- 100% retention of parameters, body type, and attributes in generic nodes.
- No unsupported component requires a fork to preserve or inspect its content.
- No network, filesystem, or code execution introduced by new adapters.
- Existing supported-format tests remain passing.

## Open questions

1. Should structured diagnostics replace `metadata["diagnostics"]` or live beside
   it through 1.0?
2. Is lossless preservation important enough to change the default in 0.x, or
   should it wait for 1.0?
3. Should vendor adapters ship in core, an `extensions` module, or a separate
   package?
4. Does the project require byte-for-byte XML round-tripping, or only semantic
   AST/text preservation? Exact round-tripping requires retaining namespaces,
   attribute order, comments, and CDATA boundaries.
5. Which real exported fixtures can vendors legally contribute for regression
   tests?

## Sources

- [Atlassian: Confluence Storage Format](https://confluence.atlassian.com/conf89/confluence-storage-format-1387595118.html)
- [Atlassian: Confluence Storage Format for Macros](https://confluence.atlassian.com/spaces/CONF51/pages/336169257/Confluence+Storage+Format+for+Macros)
- [Atlassian developer note on macro storage versions](https://developer.atlassian.com/server/confluence/preparing-for-confluence-5-3/)
- [Appfire: Switch to the new Tabs macro](https://appfire.atlassian.net/wiki/spaces/CTFCSM/pages/1562542237/Switch+to+the+new+Tabs+macro)
- [Navitabs Marketplace listing](https://marketplace.atlassian.com/apps/28632/navitabs-navigation-macros-for-confluence)
- [PlantUML app vendor: storage-format diagram recovery](https://stratus-addons.atlassian.net/wiki/spaces/PDFC/pages/1678966785/How+to+manually+copy+diagram+data+from+page+storage+format)
- [`confluence-content-parser` repository](https://github.com/Unificon/confluence-content-parser)
- [Pinned parser implementation](https://github.com/Unificon/confluence-content-parser/blob/72432ea4d42988803f91ba55ea6f70b16bcd9490/src/confluence_content_parser/parser.py)
- [Pinned node models](https://github.com/Unificon/confluence-content-parser/blob/72432ea4d42988803f91ba55ea6f70b16bcd9490/src/confluence_content_parser/nodes.py)
