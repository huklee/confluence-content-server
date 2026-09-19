# Confluence Content Server

This project exposes `confluence-content-parser` through a small local FastAPI
server. It includes a side-by-side XML editor, a sample catalog, and a safe
HTML preview for common Confluence elements and macros.

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- The current `confluence-content-parser` 0.3 development checkout in a sibling
  directory (see below)

This repository intentionally uses an editable sibling checkout because the
parser extensions it exercises have not yet been released by the upstream
project. Arrange both repositories like this:

```text
workspace/
├── confluence-content-parser/
└── confluence-content-server/
```

Then install the locked environment:

```bash
cd confluence-content-server
uv sync
```

## Run

```bash
uv run parse_confluence.py
```

Open `http://127.0.0.1:8000` for the side-by-side XML editor and live preview.
Use the sample selector in the header to load the comprehensive sample 0 or any
of the 16 focused regression examples.

The bundled sequence-diagram fallback renders the PlantUML sample without a
network call. For full PlantUML syntax, install a local Java runtime and point
`PLANTUML_JAR` at an official PlantUML jar before starting the server. Include
and import directives remain disabled because page input must not read local
files or fetch remote content.

Sample 16 embeds uncompressed `.drawio` XML in a `drawio` macro plaintext body
for a self-contained local preview. Confluence normally stores draw.io diagrams
as page attachments; attachment-only and compressed diagrams show a resolver
message until an attachment/export integration is configured.
The server listens only on your local machine. To use another port:

```bash
./run_server.sh --port 8001
```

Run `./run_server.sh --help` for host, reload, and PlantUML options. Environment
variables such as `PORT=8001`, `HOST=0.0.0.0`, and `PLANTUML_JAR=/path/to/plantuml.jar`
are also supported.

## Parse content

```bash
curl -X POST "http://127.0.0.1:8000/render" \
  -H "Content-Type: text/plain" \
  --data-binary '<p><ac:structured-macro ac:name="info"><ac:rich-text-body><p>Hello AI</p></ac:rich-text-body></ac:structured-macro></p>'
```

Expected response:

```html
<aside class="panel panel-info"><span>ℹ️</span><div><p>Hello AI</p></div></aside>
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

The preview supports common headings, text formatting, lists, tables, links,
images, panels, code blocks, statuses, layouts, expandable sections, legacy
tabs, local diagrams, and a navigable table of contents. TOC entries are built
from the entire parsed document, including headings after the macro, and honor
the configured minimum and maximum heading levels. Parse failures and parser
diagnostics with error severity are returned as HTTP 400.

## Local parser development

The project is configured to use the editable parser clone at
`../confluence-content-parser` through `[tool.uv.sources]`. Changes in that
clone are picked up by `uv run` without publishing a package. The local clone
implements version 0.3.0 features including lossless unknown nodes, semantic
table sections, extension registration, legacy tabs, plaintext diagrams, and
retained table-of-contents options.

## Safety boundaries

- Unknown content is preserved for a visible fallback, but never trusted as
  browser-ready HTML.
- Page-provided URLs are restricted to local fragments, HTTP(S), and `mailto`.
- PlantUML include/import directives are rejected.
- No public rendering service receives page content.
- Attachment-backed diagrams, Jira results, users, and pages need explicit
  resolver integrations; unresolved content remains visible as a placeholder.

## Test

Run the renderer tests based on the Atlassian Storage Format examples:

```bash
uv run python -m unittest discover -s tests -v
```

The compatibility research and follow-up work are documented in:

- [`OTHER_FEATURES.md`](OTHER_FEATURES.md) for uncovered format cases and
  recommended fixtures.
- [`UNSUPPORTED_COMPONENTS.md`](UNSUPPORTED_COMPONENTS.md) for parser support
  boundaries and safe fallbacks.
- [`PRD_CONFLUENCE_CONTENT_PARSER_EXTENSIONS.md`](PRD_CONFLUENCE_CONTENT_PARSER_EXTENSIONS.md)
  for the upstream parser requirements implemented by the sibling checkout.
