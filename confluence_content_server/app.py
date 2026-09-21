import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from base64 import b64encode
from collections import deque
from html import escape, unescape
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn
from confluence_content_parser import (
    ConfluenceParser,
    register_legacy_tabs,
    register_plaintext_diagrams,
)
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from .samples import SAMPLES

app = FastAPI(title="Confluence Content Parser")
INDEX_HTML = Path(__file__).with_name("editor.html").read_text(encoding="utf-8")
AC_NAMESPACE = "http://www.atlassian.com/schema/confluence/4/ac/"
RI_NAMESPACE = "http://www.atlassian.com/schema/confluence/4/ri/"
MAX_DIAGRAM_SOURCE_BYTES = 100_000
MAX_DRAWIO_SOURCE_BYTES = 1_000_000
MAX_DRAWIO_CELLS = 200
PLANTUML_TIMEOUT_SECONDS = 10
UNSAFE_PLANTUML_DIRECTIVE = re.compile(r"(?im)^\s*!(?:include|import)")
SEQUENCE_MESSAGE = re.compile(
    r'^\s*(?P<left>"[^"]+"|[^:<>]+?)\s*(?P<arrow><--?|--?>)\s*'
    r'(?P<right>"[^"]+"|[^:]+?)\s*:\s*(?P<label>.+?)\s*$'
)


class RenderContext:
    """Extra macro data that parser 0.2.1 does not retain in its AST."""

    def __init__(self, xml_content: str, root_node: object | None = None) -> None:
        self.panels: deque[dict[str, str]] = deque()
        self.code_blocks: deque[dict[str, str]] = deque()
        self.jira_macros: deque[dict[str, str]] = deque()
        self.toc_macros: deque[dict[str, str]] = deque()
        self.tab_group_index = 0
        self.diagram_index = 0
        self.drawio_index = 0
        self.heading_ids: dict[int, str] = {}
        self.headings: list[tuple[object, int, str, str]] = []

        if root_node is not None:
            used_ids: dict[str, int] = {}
            walk = getattr(root_node, "walk", None)
            for node in walk() if callable(walk) else []:
                if type(node).__name__ != "HeadingElement":
                    continue
                level_value = _value(node, "type")
                level = int(level_value[1]) if re.fullmatch(r"h[1-6]", level_value) else 2
                to_text = getattr(node, "to_text", None)
                title = str(to_text()).strip() if callable(to_text) else ""
                base_id = re.sub(r"[^\w-]+", "-", title.lower(), flags=re.UNICODE).strip("-") or "section"
                occurrence = used_ids.get(base_id, 0) + 1
                used_ids[base_id] = occurrence
                heading_id = base_id if occurrence == 1 else f"{base_id}-{occurrence}"
                self.heading_ids[id(node)] = heading_id
                self.headings.append((node, level, title, heading_id))

        try:
            wrapped = (
                f'<root xmlns:ac="{AC_NAMESPACE}" xmlns:ri="{RI_NAMESPACE}">'
                f"{xml_content}</root>"
            )
            root = ET.fromstring(wrapped)
        except ET.ParseError:
            return

        name_attribute = f"{{{AC_NAMESPACE}}}name"
        for macro in root.iter(f"{{{AC_NAMESPACE}}}structured-macro"):
            name = macro.attrib.get(name_attribute, "")
            parameters = {
                child.attrib.get(name_attribute, ""): "".join(child.itertext()).strip()
                for child in macro
                if child.tag == f"{{{AC_NAMESPACE}}}parameter"
            }
            if name in {"panel", "tip", "note", "warning", "info"}:
                self.panels.append(parameters)
            elif name == "code":
                self.code_blocks.append(parameters)
            elif name == "jira":
                self.jira_macros.append(parameters)
            elif name == "toc":
                self.toc_macros.append(parameters)


@app.get("/", response_class=HTMLResponse)
def editor() -> HTMLResponse:
    """Serve the local XML editor and live preview."""
    return HTMLResponse(content=INDEX_HTML)


@app.get("/samples", response_class=JSONResponse)
def samples() -> list[dict[str, str]]:
    """Return the XML examples used by the editor and regression tests."""
    return SAMPLES


def create_parser() -> ConfluenceParser:
    """Create an isolated parser configured with the local extension adapters."""
    parser = ConfluenceParser(unknown_content="preserve")
    register_legacy_tabs(parser)
    register_plaintext_diagrams(parser)
    return parser


def _value(node: object, attribute: str) -> str:
    """Return a node attribute, unwrapping enum values when necessary."""
    value = getattr(node, attribute, "")
    return str(getattr(value, "value", value) or "")


def _children(node: object) -> list[object]:
    get_children = getattr(node, "get_children", None)
    return list(get_children()) if callable(get_children) else []


def _render_children(node: object, context: RenderContext) -> str:
    """Render children with readable spacing (the parser normalizes whitespace)."""
    rendered: list[str] = []
    previous_child: object | None = None
    for child in _children(node):
        child_html = _render_node(child, context)
        if not child_html:
            continue
        if rendered and not (
            type(child).__name__ == "Text"
            and str(getattr(child, "text", "")).startswith(tuple(".,;:!?)]}"))
        ):
            previous_is_block = bool(getattr(previous_child, "is_block_level", False))
            current_is_block = bool(getattr(child, "is_block_level", False))
            if not previous_is_block and not current_is_block:
                rendered.append(" ")
        rendered.append(child_html)
        previous_child = child
    return "".join(rendered)


def _toc_level(value: object, fallback: int) -> int:
    """Normalize a TOC heading-level option to Confluence's supported range."""
    try:
        return min(6, max(1, int(str(value))))
    except (TypeError, ValueError):
        return fallback


def _render_toc(node: object, context: RenderContext) -> str:
    """Resolve a TOC macro against all headings in the parsed document."""
    raw_parameters = context.toc_macros.popleft() if context.toc_macros else {}
    min_level = _toc_level(
        getattr(node, "min_level", None) or raw_parameters.get("minLevel"), 1
    )
    max_level = _toc_level(
        getattr(node, "max_level", None) or raw_parameters.get("maxLevel"), 6
    )
    if min_level > max_level:
        min_level, max_level = max_level, min_level

    headings = [
        (level, title, heading_id)
        for _, level, title, heading_id in context.headings
        if min_level <= level <= max_level and title
    ]
    label = '<span class="toc-title">📋 Table of contents</span>'
    if not headings:
        return f'<nav class="toc-macro" aria-label="Table of contents">{label}</nav>'

    toc_type = str(getattr(node, "toc_type", "") or raw_parameters.get("type", "list"))
    if toc_type.lower() == "flat":
        links = "<span aria-hidden=\"true\"> · </span>".join(
            f'<a href="#{escape(heading_id, quote=True)}">{escape(title)}</a>'
            for _, title, heading_id in headings
        )
        return (
            '<nav class="toc-macro toc-flat" aria-label="Table of contents">'
            f"{label}<div>{links}</div></nav>"
        )

    roots: list[dict[str, object]] = []
    stack: list[tuple[int, dict[str, object]]] = []
    for level, title, heading_id in headings:
        entry: dict[str, object] = {
            "title": title,
            "heading_id": heading_id,
            "children": [],
        }
        while stack and level <= stack[-1][0]:
            stack.pop()
        siblings = stack[-1][1]["children"] if stack else roots
        assert isinstance(siblings, list)
        siblings.append(entry)
        stack.append((level, entry))

    def render_entries(entries: list[dict[str, object]]) -> str:
        items = []
        for entry in entries:
            children = entry["children"]
            nested = render_entries(children) if isinstance(children, list) and children else ""
            items.append(
                f'<li><a href="#{escape(str(entry["heading_id"]), quote=True)}">'
                f'{escape(str(entry["title"]))}</a>{nested}</li>'
            )
        return f'<ul>{"".join(items)}</ul>'

    return (
        '<nav class="toc-macro" aria-label="Table of contents">'
        f"{label}{render_entries(roots)}</nav>"
    )


def _safe_url(value: str | None) -> str | None:
    """Allow local fragments and common browser-safe URL schemes only."""
    if not value:
        return None
    parsed = urlsplit(value)
    if (not parsed.scheme and not parsed.netloc) or parsed.scheme in {"http", "https", "mailto"}:
        return value
    return None


def _render_tabs(node: object, context: RenderContext) -> str:
    """Render a no-script radio tabset with selectors above one visible panel."""
    group_id = f"confluence-tabs-{context.tab_group_index}"
    context.tab_group_index += 1
    tabs = [child for child in _children(node) if type(child).__name__ == "TabMacro"]
    if not tabs:
        return _render_children(node, context)

    switches: list[str] = []
    labels: list[str] = []
    panels: list[str] = []
    selectors: list[str] = []
    for index, tab in enumerate(tabs):
        switch_id = f"{group_id}-{index}"
        panel_id = f"{switch_id}-panel"
        title = escape(str(getattr(tab, "title", "") or f"Tab {index + 1}"))
        checked = " checked" if index == 0 else ""
        switches.append(
            f'<input class="tab-switch" type="radio" name="{group_id}" '
            f'id="{switch_id}"{checked}>'
        )
        labels.append(f'<label for="{switch_id}">{title}</label>')
        panels.append(
            f'<section class="tab-panel" id="{panel_id}">{_render_children(tab, context)}</section>'
        )
        selectors.extend(
            (
                f'#{switch_id}:checked ~ .tab-labels label[for="{switch_id}"]'
                "{color:#0052cc;border-color:#0052cc;background:#deebff}",
                f"#{switch_id}:checked ~ .tab-panels #{panel_id}{{display:block}}",
            )
        )

    orientation = escape(str(getattr(node, "orientation", "") or "horizontal"), quote=True)
    return (
        f'<div class="tabs-container tabs-{orientation}" id="{group_id}">'
        f'<style>{"".join(selectors)}</style>{"".join(switches)}'
        f'<div class="tab-labels" role="tablist">{"".join(labels)}</div>'
        f'<div class="tab-panels">{"".join(panels)}</div></div>'
    )


def _plantuml_cli_svg(source: str) -> bytes | None:
    """Use an explicitly configured local PlantUML jar, never a remote service."""
    jar_value = os.environ.get("PLANTUML_JAR")
    java = shutil.which(os.environ.get("JAVA_BIN", "java"))
    if not jar_value or not java:
        return None
    jar = Path(jar_value).expanduser().resolve()
    if not jar.is_file():
        return None
    try:
        completed = subprocess.run(
            [java, "-Djava.awt.headless=true", "-jar", str(jar), "-pipe", "-tsvg"],
            input=source.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=PLANTUML_TIMEOUT_SECONDS,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout if b"<svg" in completed.stdout else None


def _sequence_svg(source: str, diagram_id: str) -> str | None:
    """Render the common PlantUML sequence subset when the Java engine is absent."""
    participants: list[str] = []
    messages: list[tuple[str, str, str]] = []
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("'", "@", "title ", "skinparam ")):
            continue
        declaration = re.match(
            r'^(?:participant|actor|boundary|control|entity|database|collections|queue)\s+'
            r'(?P<name>"[^"]+"|\S+)',
            line,
            re.IGNORECASE,
        )
        if declaration:
            name = declaration.group("name").strip('"')
            if name not in participants:
                participants.append(name)
            continue
        message = SEQUENCE_MESSAGE.match(line)
        if not message:
            return None
        left = message.group("left").strip().strip('"')
        right = message.group("right").strip().strip('"')
        if message.group("arrow").startswith("<"):
            left, right = right, left
        for participant in (left, right):
            if participant not in participants:
                participants.append(participant)
        messages.append((left, right, message.group("label")))

    if len(participants) < 2 or not messages:
        return None

    spacing = 180
    margin = 70
    width = max(420, margin * 2 + spacing * (len(participants) - 1))
    height = 155 + 58 * len(messages)
    positions = {name: margin + index * spacing for index, name in enumerate(participants)}
    marker_id = f"{diagram_id}-arrow"
    parts = [
        f'<svg class="plantuml-svg" viewBox="0 0 {width} {height}" '
        'role="img" aria-label="PlantUML sequence diagram" xmlns="http://www.w3.org/2000/svg">',
        f'<defs><marker id="{marker_id}" markerWidth="8" markerHeight="8" refX="7" refY="4" '
        'orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#172b4d"/></marker></defs>',
    ]
    for name, x in positions.items():
        safe_name = escape(name)
        parts.extend(
            (
                f'<rect x="{x - 60}" y="12" width="120" height="34" rx="4" fill="#deebff" stroke="#0052cc"/>',
                f'<text x="{x}" y="34" text-anchor="middle" font-size="13">{safe_name}</text>',
                f'<line x1="{x}" y1="46" x2="{x}" y2="{height - 48}" stroke="#a5adba" stroke-dasharray="5 5"/>',
                f'<rect x="{x - 60}" y="{height - 46}" width="120" height="34" rx="4" fill="#deebff" stroke="#0052cc"/>',
                f'<text x="{x}" y="{height - 24}" text-anchor="middle" font-size="13">{safe_name}</text>',
            )
        )
    for index, (sender, receiver, label) in enumerate(messages):
        y = 82 + index * 58
        start = positions[sender]
        end = positions[receiver]
        text_x = (start + end) / 2
        parts.extend(
            (
                f'<text x="{text_x}" y="{y - 8}" text-anchor="middle" font-size="12">{escape(label)}</text>',
                f'<line x1="{start}" y1="{y}" x2="{end}" y2="{y}" stroke="#172b4d" '
                f'marker-end="url(#{marker_id})"/>',
            )
        )
    parts.append("</svg>")
    return "".join(parts)


def _render_plantuml(node: object, context: RenderContext) -> str:
    title = escape(str(getattr(node, "title", "") or "PlantUML diagram"))
    source_value = str(getattr(node, "source", ""))
    source = source_value.encode("utf-8")[:MAX_DIAGRAM_SOURCE_BYTES].decode("utf-8", "ignore")
    diagram_id = f"plantuml-{context.diagram_index}"
    context.diagram_index += 1

    if len(source_value.encode("utf-8")) > MAX_DIAGRAM_SOURCE_BYTES:
        reason = "Diagram source exceeds the 100 KB local rendering limit."
    elif UNSAFE_PLANTUML_DIRECTIVE.search(source):
        reason = "External and local PlantUML include/import directives are disabled."
    else:
        cli_svg = _plantuml_cli_svg(source)
        if cli_svg:
            encoded = b64encode(cli_svg).decode("ascii")
            diagram = f'<img class="plantuml-svg" src="data:image/svg+xml;base64,{encoded}" alt="{title}">'
            return f'<figure class="plantuml-diagram">{diagram}<figcaption>{title}</figcaption></figure>'
        sequence_svg = _sequence_svg(source, diagram_id)
        if sequence_svg:
            return f'<figure class="plantuml-diagram">{sequence_svg}<figcaption>{title}</figcaption></figure>'
        reason = "Install PlantUML locally and set PLANTUML_JAR to render this diagram type."

    return (
        f'<figure class="plantuml-diagram diagram-fallback"><figcaption>{title}</figcaption>'
        f'<p class="diagram-warning">{escape(reason)}</p><pre><code data-language="plantuml">'
        f'{escape(source)}</code></pre></figure>'
    )


def _macro_parameters(node: object) -> dict[str, str]:
    return {
        str(getattr(parameter, "name", "")): str(getattr(parameter, "value", "") or "")
        for parameter in getattr(node, "parameters", [])
    }


def _drawio_style(value: str) -> dict[str, str]:
    return {
        key: setting
        for item in value.split(";")
        if "=" in item
        for key, setting in [item.split("=", 1)]
    }


def _safe_drawio_color(value: str | None, fallback: str) -> str:
    if value and re.fullmatch(r"#[0-9a-fA-F]{3,8}", value):
        return value
    return fallback


def _drawio_label(value: str) -> str:
    with_breaks = re.sub(r"(?i)<br\s*/?>", " ", unescape(value))
    return re.sub(r"<[^>]+>", "", with_breaks).strip()


def _drawio_svg(source: str, diagram_id: str) -> tuple[str | None, str | None]:
    """Render a bounded subset of uncompressed mxGraph XML as safe SVG."""
    try:
        root = ET.fromstring(source)
    except ET.ParseError:
        return None, "The embedded draw.io XML is invalid."

    model = root if root.tag == "mxGraphModel" else root.find(".//mxGraphModel")
    if model is None:
        if root.tag == "mxfile" and root.find("diagram") is not None:
            return None, "This draw.io page is compressed; configure an export engine to render it."
        return None, "No mxGraphModel was found in the embedded draw.io XML."

    cells = model.findall(".//mxCell")
    if len(cells) > MAX_DRAWIO_CELLS:
        return None, f"The diagram exceeds the {MAX_DRAWIO_CELLS}-cell local rendering limit."

    vertices: dict[str, dict[str, float | str]] = {}
    edges: list[ET.Element] = []
    for cell in cells:
        if cell.attrib.get("edge") == "1":
            edges.append(cell)
            continue
        if cell.attrib.get("vertex") != "1":
            continue
        geometry = cell.find("mxGeometry")
        if geometry is None:
            continue
        try:
            x = float(geometry.attrib.get("x", "0"))
            y = float(geometry.attrib.get("y", "0"))
            width = max(20.0, float(geometry.attrib.get("width", "120")))
            height = max(20.0, float(geometry.attrib.get("height", "60")))
        except ValueError:
            continue
        vertices[cell.attrib.get("id", "")] = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "label": _drawio_label(cell.attrib.get("value", "")),
            "style": cell.attrib.get("style", ""),
        }

    if not vertices:
        return None, "The diagram has no locally renderable vertex cells."

    margin = 30.0
    max_x = max(float(vertex["x"]) + float(vertex["width"]) for vertex in vertices.values())
    max_y = max(float(vertex["y"]) + float(vertex["height"]) for vertex in vertices.values())
    view_width = max(320.0, max_x + margin)
    view_height = max(180.0, max_y + margin)
    marker_id = f"{diagram_id}-arrow"
    parts = [
        f'<svg class="drawio-svg" viewBox="0 0 {view_width:g} {view_height:g}" '
        'role="img" aria-label="draw.io diagram" xmlns="http://www.w3.org/2000/svg">',
        f'<defs><marker id="{marker_id}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" '
        'orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="#42526e"/></marker></defs>',
    ]

    for edge in edges:
        source_vertex = vertices.get(edge.attrib.get("source", ""))
        target_vertex = vertices.get(edge.attrib.get("target", ""))
        if not source_vertex or not target_vertex:
            continue
        x1 = float(source_vertex["x"]) + float(source_vertex["width"]) / 2
        y1 = float(source_vertex["y"]) + float(source_vertex["height"]) / 2
        x2 = float(target_vertex["x"]) + float(target_vertex["width"]) / 2
        y2 = float(target_vertex["y"]) + float(target_vertex["height"]) / 2
        label = escape(_drawio_label(edge.attrib.get("value", "")))
        parts.append(
            f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" '
            f'stroke="#42526e" stroke-width="2" marker-end="url(#{marker_id})"/>'
        )
        if label:
            parts.append(
                f'<text x="{(x1 + x2) / 2:g}" y="{(y1 + y2) / 2 - 7:g}" '
                f'text-anchor="middle" font-size="11" fill="#42526e">{label}</text>'
            )

    for vertex in vertices.values():
        x = float(vertex["x"])
        y = float(vertex["y"])
        width = float(vertex["width"])
        height = float(vertex["height"])
        style = _drawio_style(str(vertex["style"]))
        fill = _safe_drawio_color(style.get("fillColor"), "#f4f5f7")
        stroke = _safe_drawio_color(style.get("strokeColor"), "#42526e")
        font = _safe_drawio_color(style.get("fontColor"), "#172b4d")
        label = escape(str(vertex["label"]))
        if "ellipse" in style:
            parts.append(
                f'<ellipse cx="{x + width / 2:g}" cy="{y + height / 2:g}" rx="{width / 2:g}" '
                f'ry="{height / 2:g}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
            )
        else:
            radius = 8 if style.get("rounded") == "1" else 0
            parts.append(
                f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{radius}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
            )
        parts.append(
            f'<text x="{x + width / 2:g}" y="{y + height / 2 + 4:g}" text-anchor="middle" '
            f'font-size="13" font-weight="600" fill="{font}">{label}</text>'
        )
    parts.append("</svg>")
    return "".join(parts), None


def _render_drawio(node: object, context: RenderContext) -> str:
    parameters = _macro_parameters(node)
    title = escape(parameters.get("diagramName", "draw.io diagram"))
    source = str(getattr(node, "plain_text_body", "") or "")
    diagram_id = f"drawio-{context.drawio_index}"
    context.drawio_index += 1

    if not source:
        reason = "The macro references a Confluence attachment; an attachment resolver is required."
    elif len(source.encode("utf-8")) > MAX_DRAWIO_SOURCE_BYTES:
        reason = "The embedded draw.io XML exceeds the 1 MB local rendering limit."
    else:
        svg, reason = _drawio_svg(source, diagram_id)
        if svg:
            return f'<figure class="drawio-diagram">{svg}<figcaption>{title}</figcaption></figure>'

    return (
        f'<figure class="drawio-diagram diagram-fallback"><figcaption>{title}</figcaption>'
        f'<p class="diagram-warning">{escape(reason or "Unable to render this draw.io diagram.")}</p></figure>'
    )


def _render_node(node: object, context: RenderContext) -> str:
    """Render supported parser AST nodes to safe, semantic HTML."""
    name = type(node).__name__
    if name == "TabsMacro":
        return _render_tabs(node, context)
    content = _render_children(node, context)

    if name == "Text":
        return escape(str(getattr(node, "text", "")))
    if name in {"Fragment", "GenericElement", "LayoutElement", "ExcerptMacro", "TableSection"}:
        return content
    if name == "LayoutCell":
        return f'<div class="layout-cell">{content}</div>'
    if name == "LayoutSection":
        return f'<div class="layout">{content}</div>'
    if name == "HeadingElement":
        tag = _value(node, "type")
        tag = tag if tag in {f"h{level}" for level in range(1, 7)} else "h2"
        heading_id = context.heading_ids.get(id(node))
        id_attribute = f' id="{escape(heading_id, quote=True)}"' if heading_id else ""
        return f"<{tag}{id_attribute}>{content}</{tag}>"
    if name == "TextEffectElement":
        tag = _value(node, "type")
        tag = tag if tag in {"strong", "em", "u", "del", "code", "sub", "sup", "blockquote", "span"} else "span"
        return f"<{tag}>{content}</{tag}>"
    if name == "TextBreakElement":
        tag = _value(node, "type")
        if tag in {"br", "hr"}:
            return f"<{tag}>"
        if any(bool(getattr(child, "is_block_level", False)) for child in _children(node)):
            return content
        return f"<p>{content}</p>"
    if name == "ListElement":
        list_type = _value(node, "type")
        tag = "ol" if list_type == "ol" else "ul"
        start = getattr(node, "start", None)
        start_attribute = f' start="{int(start)}"' if tag == "ol" and start is not None else ""
        css_class = ' class="task-list"' if list_type == "task-list" else ""
        return f"<{tag}{css_class}{start_attribute}>{content}</{tag}>"
    if name == "ListItem":
        status = _value(node, "status")
        checkbox = ""
        if status:
            checked = " checked" if status == "complete" else ""
            checkbox = f'<input type="checkbox" disabled{checked}>'
        return f"<li>{checkbox}{content}</li>"
    if name == "LinkElement":
        href = _safe_url(getattr(node, "href", None))
        children = _children(node)
        resource = next((child for child in children if type(child).__name__ == "ResourceIdentifier"), None)
        label_content = "".join(
            _render_node(child, context)
            for child in children
            if type(child).__name__ != "ResourceIdentifier"
        )
        label = label_content or content or escape(str(getattr(node, "href", "") or "Link"))
        if resource is not None:
            resource_type = _value(resource, "type")
            if resource_type == "user":
                user_key = str(
                    getattr(resource, "account_id", "")
                    or getattr(resource, "userkey", "")
                    or "unknown"
                )
                return (
                    f'<span class="user-mention" data-user-key="{escape(user_key, quote=True)}" '
                    f'title="Confluence user">@{escape(user_key)}</span>'
                )
            title = str(getattr(resource, "content_title", "") or label)
            space = str(getattr(resource, "space_key", "") or "")
            return (
                f'<span class="internal-link" title="Confluence page: {escape(title, quote=True)}" '
                f'data-space-key="{escape(space, quote=True)}">{label}</span>'
            )
        return f'<a href="{escape(href, quote=True)}" target="_blank" rel="noreferrer">{label}</a>' if href else label
    if name == "Image":
        source = _safe_url(getattr(node, "src", None) or getattr(node, "url_value", None))
        alt = escape(str(getattr(node, "alt", "") or getattr(node, "filename", "") or "Image"), quote=True)
        width = str(getattr(node, "width", "") or "")
        width_attribute = f' width="{int(width)}"' if width.isdigit() else ""
        placeholder_width = (
            f' data-width="{int(width)}" style="max-width: {int(width)}px"'
            if width.isdigit()
            else ""
        )
        alignment = str(getattr(node, "alignment", "") or "")
        alignment_class = f" image-{alignment}" if alignment in {"left", "center", "right"} else ""
        if source:
            return f'<img class="confluence-image{alignment_class}" src="{escape(source, quote=True)}" alt="{alt}"{width_attribute}>'
        filename = escape(str(getattr(node, "filename", "") or "Image"), quote=True)
        return (
            f'<span class="image-placeholder{alignment_class}" data-filename="{filename}"'
            f'{placeholder_width}>🖼️ Attachment: {filename}</span>'
        )
    if name == "Table":
        return f"<div class=\"table-wrap\"><table>{content}</table></div>"
    if name == "TableRow":
        return f"<tr>{content}</tr>"
    if name == "TableCell":
        tag = "th" if bool(getattr(node, "is_header", False)) else "td"
        attributes = ""
        for attribute in ("rowspan", "colspan"):
            value = getattr(node, attribute, None)
            if value:
                attributes += f' {attribute}="{int(value)}"'
        return f"<{tag}{attributes}>{content}</{tag}>"
    if name == "PanelMacro":
        parameters = context.panels.popleft() if context.panels else {}
        panel_type = _value(node, "type") or "panel"
        icons = {"info": "ℹ️", "note": "📝", "success": "✅", "warning": "⚠️", "error": "❌", "panel": "📋"}
        title = escape(parameters.get("title", ""))
        heading = f'<div class="panel-title">{title}</div>' if title else ""
        return f'<aside class="panel panel-{escape(panel_type, quote=True)}"><span>{icons.get(panel_type, "📋")}</span><div>{heading}{content}</div></aside>'
    if name == "CodeMacro":
        parameters = context.code_blocks.popleft() if context.code_blocks else {}
        language = escape(str(getattr(node, "language", "") or "text"), quote=True)
        code = escape(str(getattr(node, "code", "")))
        title = escape(parameters.get("title", ""))
        line_numbers = parameters.get("linenumbers", "").lower() == "true"
        title_html = f'<div class="code-title">{title}</div>' if title else ""
        line_attribute = ' data-line-numbers="true"' if line_numbers else ""
        return f'<div class="code-block">{title_html}<pre><code data-language="{language}"{line_attribute}>{code}</code></pre></div>'
    if name == "DiagramMacro":
        return _render_plantuml(node, context)
    if name == "TabMacro":
        title = escape(str(getattr(node, "title", "") or "Untitled tab"))
        return f'<section class="tab-panel"><h3>{title}</h3>{content}</section>'
    if name == "GenericMacro":
        macro_name = escape(str(getattr(node, "name", "unknown")), quote=True)
        if macro_name == "drawio":
            return _render_drawio(node, context)
        plain_text = getattr(node, "plain_text_body", None)
        if plain_text is not None:
            return f'<div class="generic-macro" data-macro="{macro_name}"><pre><code>{escape(str(plain_text))}</code></pre></div>'
        return f'<aside class="generic-macro" data-macro="{macro_name}"><strong>{macro_name}</strong>{content}</aside>'
    if name in {"ExpandMacro", "DetailsMacro"}:
        title = escape(str(getattr(node, "title", "") or "Details"))
        return f"<details><summary>{title}</summary>{content}</details>"
    if name == "StatusMacro":
        title = escape(str(getattr(node, "title", "") or "Status"))
        colour = escape(str(getattr(node, "colour", "") or "neutral"), quote=True)
        return f'<span class="status-lozenge status-{colour}">{title}</span>'
    if name == "TocMacro":
        return _render_toc(node, context)
    if name == "JiraMacro":
        parameters = context.jira_macros.popleft() if context.jira_macros else {}
        server = escape(str(getattr(node, "server", "") or parameters.get("server", "Jira")))
        query = escape(parameters.get("jqlQuery", ""))
        maximum = escape(parameters.get("maximumIssues", ""), quote=True)
        query_html = f'<code class="jira-query">{query}</code>' if query else ""
        maximum_attribute = f' data-maximum-issues="{maximum}"' if maximum else ""
        return (
            f'<span class="jira-macro"{maximum_attribute}>'
            f'<strong>🎫 Jira issues</strong><span class="jira-server">{server}</span>{query_html}'
            f"</span>"
        )

    # Nodes without a visual equivalent still provide a useful text form.
    to_text = getattr(node, "to_text", None)
    return escape(str(to_text())) if callable(to_text) else content


@app.post("/render", response_class=HTMLResponse)
def render(xml_content: str = Body(..., media_type="text/plain")) -> HTMLResponse:
    """Parse Confluence Storage Format and return its extracted text as HTML."""
    try:
        document = create_parser().parse(xml_content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Confluence content: {exc}") from exc

    errors = [
        diagnostic
        for diagnostic in document.metadata.get("structured_diagnostics", [])
        if diagnostic.get("severity") == "error"
    ]
    if errors:
        raise HTTPException(status_code=400, detail={"diagnostics": errors})

    context = RenderContext(xml_content, document.root)
    rendered = _render_node(document.root, context) if document.root else ""
    return HTMLResponse(content=rendered)


def main() -> None:
    """Run the local server using environment-based host and port settings."""
    uvicorn.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )


if __name__ == "__main__":
    main()
