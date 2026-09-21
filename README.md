# Confluence Content Server

This project exposes `confluence-content-parser` through a small local FastAPI
server. It includes a side-by-side XML editor, a sample catalog, and a safe
HTML preview for common Confluence elements and macros.

## Requirements

- Python 3.12+
- Git
- [`uv`](https://docs.astral.sh/uv/)
- The customized [`huklee/confluence-content-parser`](https://github.com/huklee/confluence-content-parser)
  checkout in a sibling directory

If Python 3.12 is not already installed, `uv python install 3.12` can install a
managed interpreter.

## Quick start

Copy and run these commands from a directory where you want the two projects:

```bash
mkdir confluence-preview
cd confluence-preview
git clone https://github.com/huklee/confluence-content-parser.git
git clone https://github.com/huklee/confluence-content-server.git
cd confluence-content-server
uv sync --locked
uv run python -m unittest discover -s tests -v
./run_server.sh
```

The sibling layout is required because the server intentionally consumes the
customized parser as an editable dependency:

```text
confluence-preview/
├── confluence-content-parser/
└── confluence-content-server/
```

When the launcher prints that Uvicorn is running, open
<http://127.0.0.1:8000>. Stop the server with `Ctrl+C`.

To verify the API from a second terminal:

```bash
curl --fail http://127.0.0.1:8000/samples

curl --fail -X POST http://127.0.0.1:8000/render \
  -H "Content-Type: text/plain" \
  --data-binary '<h1>Setup works</h1><p>Hello from Confluence.</p>'
```

The second command should return HTML containing
`<h1 id="setup-works">Setup works</h1>`.

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

## Updating or developing the parser

The project is configured to use the editable parser clone at
`../confluence-content-parser` through `[tool.uv.sources]`. Changes in that
clone are picked up by `uv run` without publishing a package. Pull both
repositories and resynchronize after parser dependency changes:

```bash
git -C ../confluence-content-parser pull --ff-only
git pull --ff-only
uv sync --locked
```

The customized parser
implements version 0.3.0 features including lossless unknown nodes, semantic
table sections, extension registration, legacy tabs, plaintext diagrams, and
retained table-of-contents options.

If `uv sync --locked` reports that `../confluence-content-parser` is missing,
the repositories were not cloned as siblings. Move or clone the parser next to
the server using the directory layout shown above.

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
