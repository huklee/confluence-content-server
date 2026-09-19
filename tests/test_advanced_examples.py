import unittest
from unittest.mock import patch

from parse_confluence import render, samples
from samples import SAMPLES


class WebSamplesTest(unittest.TestCase):
    def sample(self, sample_id: str) -> str:
        return next(sample["xml"] for sample in SAMPLES if sample["id"] == sample_id)

    def render_sample(self, sample_id: str) -> str:
        response = render(self.sample(sample_id))
        self.assertEqual(response.status_code, 200)
        return response.body.decode("utf-8")

    def test_catalog_exposes_comprehensive_and_sixteen_unique_focused_samples(self) -> None:
        response = samples()
        self.assertEqual(len(response), 17)
        self.assertEqual(len({sample["id"] for sample in response}), 17)
        self.assertEqual(response[0]["id"], "comprehensive")

    def test_comprehensive_sample_contains_every_focused_example(self) -> None:
        xml = self.sample("comprehensive")
        for sample in SAMPLES[1:]:
            with self.subTest(sample=sample["id"]):
                self.assertIn(sample["title"], xml)
                self.assertIn(sample["xml"], xml)
        html = self.render_sample("comprehensive")
        self.assertIn("Comprehensive Confluence Storage Format Page", html)
        self.assertIn("Portfolio summary", html)
        self.assertIn('class="plantuml-svg"', html)
        self.assertIn('class="drawio-svg"', html)
        self.assertIn('<a href="#1-structured-info-callout-panel">1. Structured Info Callout Panel</a>', html)
        self.assertIn('<a href="#16-embedded-draw-io-architecture-diagram">16. Embedded draw.io Architecture Diagram</a>', html)

    def test_tabbed_container_uses_local_parser_adapter(self) -> None:
        html = self.render_sample("tabs")
        self.assertIn('class="tabs-container tabs-horizontal"', html)
        self.assertIn('id="confluence-tabs-0-0" checked', html)
        self.assertIn('id="confluence-tabs-0-1"', html)
        self.assertIn('<div class="tab-labels" role="tablist">', html)
        self.assertIn('<label for="confluence-tabs-0-0">Overview</label>', html)
        self.assertIn('<label for="confluence-tabs-0-1">Configuration</label>', html)
        self.assertIn(".tab-panels #confluence-tabs-0-0-panel{display:block}", html)
        self.assertIn(".tab-panels #confluence-tabs-0-1-panel{display:block}", html)
        self.assertIn("<strong>Tab 1</strong>", html)
        self.assertIn("<strong>Tab 2</strong>", html)

    def test_complex_table_supports_thead_spans_statuses_and_mentions(self) -> None:
        html = self.render_sample("complex-table")
        self.assertIn('<th colspan="2">Product area and module</th>', html)
        self.assertEqual(html.count('rowspan="2"'), 3)
        self.assertIn("ACTIVE", html)
        self.assertIn("BLOCKED", html)
        self.assertIn("OAuth 2.1 and OIDC migration", html)
        self.assertIn("multi-provider failover", html)
        self.assertIn("Portfolio summary", html)
        self.assertEqual(html.count('class="user-mention"'), 6)

    def test_nested_expand_macros_inside_layout_cells(self) -> None:
        html = self.render_sample("nested-layout")
        self.assertEqual(html.count('class="layout-cell"'), 2)
        self.assertIn("<summary>View Technical Architecture</summary>", html)
        self.assertIn('data-language="yaml"', html)
        self.assertIn("image: nginx:latest", html)
        self.assertIn('class="panel panel-info"', html)

    def test_plantuml_sequence_is_rendered_locally_as_svg(self) -> None:
        with patch.dict("os.environ", {"PLANTUML_JAR": ""}):
            html = self.render_sample("plantuml")
        self.assertIn('class="plantuml-diagram"', html)
        self.assertIn('class="plantuml-svg"', html)
        self.assertIn("Sequence Diagram", html)
        self.assertIn("POST /api/v1/process", html)
        self.assertIn("200 OK", html)
        self.assertIn("<svg", html)
        self.assertNotIn("@startuml", html)

    def test_plantuml_unsupported_syntax_has_clear_fallback(self) -> None:
        xml = '''<ac:structured-macro ac:name="plantuml"><ac:plain-text-body><![CDATA[@startuml
class Account
@enduml]]></ac:plain-text-body></ac:structured-macro>'''
        with patch.dict("os.environ", {"PLANTUML_JAR": ""}):
            html = render(xml).body.decode("utf-8")
        self.assertIn("diagram-fallback", html)
        self.assertIn("set PLANTUML_JAR", html)
        self.assertIn("class Account", html)

    def test_plantuml_include_is_rejected_without_execution(self) -> None:
        xml = '''<ac:structured-macro ac:name="plantuml"><ac:plain-text-body><![CDATA[@startuml
!includeurl https://example.invalid/private.puml
Alice -> Bob: hello
@enduml]]></ac:plain-text-body></ac:structured-macro>'''
        html = render(xml).body.decode("utf-8")
        self.assertIn("diagram-fallback", html)
        self.assertIn("include/import directives are disabled", html)
        self.assertNotIn("<svg", html)

    def test_inline_drawio_xml_renders_as_local_svg(self) -> None:
        html = self.render_sample("drawio")
        self.assertIn('class="drawio-diagram"', html)
        self.assertIn('class="drawio-svg"', html)
        self.assertIn("checkout-architecture.drawio", html)
        self.assertIn("Web &amp; Mobile Clients", html)
        self.assertIn("API Gateway", html)
        self.assertIn("authorize payment", html)
        self.assertNotIn("diagram-fallback", html)

    def test_attachment_backed_drawio_macro_has_resolver_fallback(self) -> None:
        xml = '''<ac:structured-macro ac:name="drawio">
<ac:parameter ac:name="diagramName">attached.drawio</ac:parameter>
</ac:structured-macro>'''
        html = render(xml).body.decode("utf-8")
        self.assertIn("attached.drawio", html)
        self.assertIn("attachment resolver is required", html)
        self.assertIn("diagram-fallback", html)

    def test_every_sample_renders_successfully(self) -> None:
        for sample in SAMPLES:
            with self.subTest(sample=sample["id"]):
                self.assertEqual(render(sample["xml"]).status_code, 200)


if __name__ == "__main__":
    unittest.main()
