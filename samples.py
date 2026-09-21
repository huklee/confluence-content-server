SAMPLES: list[dict[str, str]] = [
    {
        "id": "info-panel",
        "title": "1. Structured Info Callout Panel",
        "xml": '''<p>
  <ac:structured-macro ac:name="info" ac:schema-version="1">
    <ac:parameter ac:name="title">Important Notice</ac:parameter>
    <ac:rich-text-body>
      <p>This is a highlighted info panel content.</p>
    </ac:rich-text-body>
  </ac:structured-macro>
</p>''',
    },
    {
        "id": "code-block",
        "title": "2. Code Block Macro",
        "xml": '''<p>
  <ac:structured-macro ac:name="code" ac:schema-version="1">
    <ac:parameter ac:name="language">python</ac:parameter>
    <ac:parameter ac:name="title">Example Script</ac:parameter>
    <ac:parameter ac:name="linenumbers">true</ac:parameter>
    <ac:plain-text-body><![CDATA[def hello_world():
    print("Hello from Confluence XML!")
]]></ac:plain-text-body>
  </ac:structured-macro>
</p>''',
    },
    {
        "id": "page-link",
        "title": "3. Internal Confluence Page Link",
        "xml": '''<p>
  <ac:link>
    <ri:page ri:content-title="Target Page Title" ri:space-key="DOCS" />
    <ac:plain-text-link-body><![CDATA[Click here to read more]]></ac:plain-text-link-body>
  </ac:link>
</p>''',
    },
    {
        "id": "status",
        "title": "4. Status Badge",
        "xml": '''<p>
  Status:
  <ac:structured-macro ac:name="status" ac:schema-version="1">
    <ac:parameter ac:name="title">IN PROGRESS</ac:parameter>
    <ac:parameter ac:name="colour">Yellow</ac:parameter>
  </ac:structured-macro>
</p>''',
    },
    {
        "id": "layout",
        "title": "5. Two-Column Equal Layout",
        "xml": '''<ac:layout>
  <ac:layout-section ac:type="two_equal">
    <ac:layout-cell><p>Left column content</p></ac:layout-cell>
    <ac:layout-cell><p>Right column content</p></ac:layout-cell>
  </ac:layout-section>
</ac:layout>''',
    },
    {
        "id": "expand",
        "title": "6. Expand / Collapsible Block",
        "xml": '''<p>
  <ac:structured-macro ac:name="expand" ac:schema-version="1">
    <ac:parameter ac:name="title">Click to view details</ac:parameter>
    <ac:rich-text-body><p>Hidden text that expands on user click.</p></ac:rich-text-body>
  </ac:structured-macro>
</p>''',
    },
    {
        "id": "attachment-image",
        "title": "7. Embedded Attachment Image",
        "xml": '''<p>
  <ac:image ac:align="center" ac:width="500">
    <ri:attachment ri:filename="screenshot.png" />
  </ac:image>
</p>''',
    },
    {
        "id": "toc",
        "title": "8. Table of Contents Macro",
        "xml": '''<p>
  <ac:structured-macro ac:name="toc" ac:schema-version="1">
    <ac:parameter ac:name="printable">true</ac:parameter>
    <ac:parameter ac:name="maxLevel">3</ac:parameter>
    <ac:parameter ac:name="type">list</ac:parameter>
  </ac:structured-macro>
</p>''',
    },
    {
        "id": "user-mention",
        "title": "9. User Mention",
        "xml": '''<p>
  Hey <ac:link><ri:user ri:userkey="8a7f80824b260021014b26002e210000" /></ac:link>, please review this section.
</p>''',
    },
    {
        "id": "jira",
        "title": "10. Jira Issues Macro",
        "xml": '''<p>
  <ac:structured-macro ac:name="jira" ac:schema-version="1">
    <ac:parameter ac:name="server">JIRA Local</ac:parameter>
    <ac:parameter ac:name="jqlQuery">project = PROJ AND status = Open</ac:parameter>
    <ac:parameter ac:name="maximumIssues">10</ac:parameter>
  </ac:structured-macro>
</p>''',
    },
    {
        "id": "tasks",
        "title": "11. Task / Checkbox List",
        "xml": '''<ac:task-list>
  <ac:task><ac:task-id>1</ac:task-id><ac:task-status>complete</ac:task-status><ac:task-body>Draft initial documentation</ac:task-body></ac:task>
  <ac:task><ac:task-id>2</ac:task-id><ac:task-status>incomplete</ac:task-status><ac:task-body>Review with product owner</ac:task-body></ac:task>
</ac:task-list>''',
    },
    {
        "id": "tabs",
        "title": "12. Tabbed Container",
        "xml": '''<p>
  <ac:structured-macro ac:name="tabs" ac:schema-version="1">
    <ac:parameter ac:name="type">horizontal</ac:parameter>
    <ac:rich-text-body>
      <ac:structured-macro ac:name="tab" ac:schema-version="1">
        <ac:parameter ac:name="title">Overview</ac:parameter>
        <ac:rich-text-body><p>This is the content inside <strong>Tab 1</strong>.</p></ac:rich-text-body>
      </ac:structured-macro>
      <ac:structured-macro ac:name="tab" ac:schema-version="1">
        <ac:parameter ac:name="title">Configuration</ac:parameter>
        <ac:rich-text-body><p>This is the content inside <strong>Tab 2</strong>.</p></ac:rich-text-body>
      </ac:structured-macro>
    </ac:rich-text-body>
  </ac:structured-macro>
</p>''',
    },
    {
        "id": "complex-table",
        "title": "13. Complex Project Portfolio Table",
        "xml": '''<table>
  <thead>
    <tr><th colspan="2">Product area and module</th><th>Scope and delivery notes</th><th>Status</th><th>Owner</th><th>Dependencies</th><th>Target</th></tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="2"><strong>Platform</strong><p>Shared services used by every customer-facing product.</p></td>
      <td>Identity and Access</td>
      <td><p>Complete the OAuth 2.1 and OIDC migration.</p><ul><li>Enforce MFA for administrators</li><li>Rotate legacy signing keys</li></ul></td>
      <td><ac:structured-macro ac:name="status"><ac:parameter ac:name="title">ACTIVE</ac:parameter><ac:parameter ac:name="colour">Green</ac:parameter></ac:structured-macro></td>
      <td><ac:link><ri:user ri:userkey="8a7f80824b260021014b26002e210000" /></ac:link></td>
      <td>Secrets service; customer directory</td><td>2026 Q4</td>
    </tr>
    <tr>
      <td>API Gateway</td>
      <td><p>Standardize routing, tenant quotas, and audit events.</p><p><em>Risk:</em> mobile clients still use two deprecated routes.</p></td>
      <td><ac:structured-macro ac:name="status"><ac:parameter ac:name="title">IN PROGRESS</ac:parameter><ac:parameter ac:name="colour">Yellow</ac:parameter></ac:structured-macro></td>
      <td><ac:link><ri:user ri:userkey="8a7f80824b260021014b26002e210001" /></ac:link></td>
      <td>Identity and Access; observability</td><td>2027 Q1</td>
    </tr>
    <tr>
      <td rowspan="2"><strong>Commerce</strong><p>Order capture, money movement, and fulfillment.</p></td>
      <td>Payment Gateway</td>
      <td><p>Add multi-provider failover and idempotent refunds.</p><ul><li>Primary provider certified</li><li>Disaster-recovery exercise pending</li></ul></td>
      <td><ac:structured-macro ac:name="status"><ac:parameter ac:name="title">BLOCKED</ac:parameter><ac:parameter ac:name="colour">Red</ac:parameter></ac:structured-macro></td>
      <td><ac:link><ri:user ri:userkey="8a7f80824b260021014b26002e210002" /></ac:link></td>
      <td>Finance approval; provider sandbox</td><td>2027 Q1</td>
    </tr>
    <tr>
      <td>Order Orchestration</td>
      <td><p>Replace nightly batches with event-driven fulfillment and customer notifications.</p></td>
      <td><ac:structured-macro ac:name="status"><ac:parameter ac:name="title">DESIGN</ac:parameter><ac:parameter ac:name="colour">Blue</ac:parameter></ac:structured-macro></td>
      <td><ac:link><ri:user ri:userkey="8a7f80824b260021014b26002e210003" /></ac:link></td>
      <td>Payment Gateway; event pipeline</td><td>2027 Q2</td>
    </tr>
    <tr>
      <td rowspan="2"><strong>Data and Experience</strong><p>Analytics foundations and operator workflows.</p></td>
      <td>Event Pipeline</td>
      <td><p>Provide schema validation, replay, and regional retention policies for product events.</p></td>
      <td><ac:structured-macro ac:name="status"><ac:parameter ac:name="title">AT RISK</ac:parameter><ac:parameter ac:name="colour">Yellow</ac:parameter></ac:structured-macro></td>
      <td><ac:link><ri:user ri:userkey="8a7f80824b260021014b26002e210004" /></ac:link></td>
      <td>Cloud capacity; privacy review</td><td>2027 Q1</td>
    </tr>
    <tr>
      <td>Operations Console</td>
      <td><p>Unify order search, incident context, and audited support actions in one interface.</p></td>
      <td><ac:structured-macro ac:name="status"><ac:parameter ac:name="title">PLANNED</ac:parameter><ac:parameter ac:name="colour">Grey</ac:parameter></ac:structured-macro></td>
      <td><ac:link><ri:user ri:userkey="8a7f80824b260021014b26002e210005" /></ac:link></td>
      <td>Order Orchestration; design system</td><td>2027 Q3</td>
    </tr>
  </tbody>
  <tfoot><tr><td colspan="7"><strong>Portfolio summary:</strong> six workstreams; one blocked and one at risk. Identity migration is the critical dependency for the gateway rollout.</td></tr></tfoot>
</table>''',
    },
    {
        "id": "nested-layout",
        "title": "14. Nested Expand in Layout",
        "xml": '''<ac:layout>
  <ac:layout-section ac:type="two_equal">
    <ac:layout-cell><p><ac:structured-macro ac:name="expand"><ac:parameter ac:name="title">View Technical Architecture</ac:parameter><ac:rich-text-body><p>Here are the primary architectural details for the left column.</p><ac:structured-macro ac:name="code"><ac:parameter ac:name="language">yaml</ac:parameter><ac:plain-text-body><![CDATA[version: '3.8'
services:
  web:
    image: nginx:latest
]]></ac:plain-text-body></ac:structured-macro></ac:rich-text-body></ac:structured-macro></p></ac:layout-cell>
    <ac:layout-cell><p><ac:structured-macro ac:name="info"><ac:rich-text-body><p>Right column notice block.</p></ac:rich-text-body></ac:structured-macro></p></ac:layout-cell>
  </ac:layout-section>
</ac:layout>''',
    },
    {
        "id": "plantuml",
        "title": "15. PlantUML Diagram Macro",
        "xml": '''<p>
  <ac:structured-macro ac:name="plantuml" ac:schema-version="1">
    <ac:parameter ac:name="title">Sequence Diagram</ac:parameter>
    <ac:plain-text-body><![CDATA[@startuml
User -> Client: Click Button
Client -> Server: POST /api/v1/process
Server --> Client: 200 OK
@enduml
]]></ac:plain-text-body>
  </ac:structured-macro>
</p>''',
    },
    {
        "id": "drawio",
        "title": "16. Embedded draw.io Architecture Diagram",
        "xml": '''<p>
  <ac:structured-macro ac:name="drawio" ac:schema-version="1">
    <ac:parameter ac:name="diagramName">checkout-architecture.drawio</ac:parameter>
    <ac:parameter ac:name="width">760</ac:parameter>
    <ac:parameter ac:name="revision">1</ac:parameter>
    <ac:plain-text-body><![CDATA[<mxfile host="app.diagrams.net">
  <diagram id="checkout" name="Checkout Architecture">
    <mxGraphModel dx="760" dy="420" grid="1" gridSize="10" page="1" pageWidth="827" pageHeight="1169">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <mxCell id="client" value="Web &amp;amp; Mobile Clients" style="rounded=1;fillColor=#deebff;strokeColor=#0052cc;fontColor=#172b4d;" vertex="1" parent="1">
          <mxGeometry x="30" y="100" width="180" height="70" as="geometry" />
        </mxCell>
        <mxCell id="gateway" value="API Gateway" style="rounded=1;fillColor=#e3fcef;strokeColor=#00875a;fontColor=#172b4d;" vertex="1" parent="1">
          <mxGeometry x="290" y="100" width="160" height="70" as="geometry" />
        </mxCell>
        <mxCell id="orders" value="Order Service" style="rounded=1;fillColor=#fff0b3;strokeColor=#ff991f;fontColor=#172b4d;" vertex="1" parent="1">
          <mxGeometry x="530" y="25" width="170" height="70" as="geometry" />
        </mxCell>
        <mxCell id="payments" value="Payment Service" style="rounded=1;fillColor=#ffebe6;strokeColor=#de350b;fontColor=#172b4d;" vertex="1" parent="1">
          <mxGeometry x="530" y="180" width="170" height="70" as="geometry" />
        </mxCell>
        <mxCell id="e1" value="HTTPS / JSON" style="edgeStyle=orthogonalEdgeStyle;endArrow=block;strokeColor=#42526e;" edge="1" source="client" target="gateway" parent="1"><mxGeometry relative="1" as="geometry" /></mxCell>
        <mxCell id="e2" value="create order" style="edgeStyle=orthogonalEdgeStyle;endArrow=block;strokeColor=#42526e;" edge="1" source="gateway" target="orders" parent="1"><mxGeometry relative="1" as="geometry" /></mxCell>
        <mxCell id="e3" value="authorize payment" style="edgeStyle=orthogonalEdgeStyle;endArrow=block;strokeColor=#42526e;" edge="1" source="gateway" target="payments" parent="1"><mxGeometry relative="1" as="geometry" /></mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>]]></ac:plain-text-body>
  </ac:structured-macro>
</p>''',
    },
]


def _comprehensive_xml() -> str:
    """Assemble sample 0 from every focused example so the catalog cannot drift."""
    sections = [
        "<h1>Comprehensive Confluence Storage Format Page</h1>",
        "<p>This page combines every focused example available in the sample catalog.</p>",
    ]
    for sample in SAMPLES:
        sections.extend((f'<h2>{sample["title"]}</h2>', sample["xml"]))
    return "\n".join(sections)


SAMPLES.insert(
    0,
    {
        "id": "comprehensive",
        "title": "0. Comprehensive — All Examples",
        "xml": _comprehensive_xml(),
    },
)
