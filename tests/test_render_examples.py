import unittest

from confluence_content_server.app import render


class AtlassianStorageFormatExamplesTest(unittest.TestCase):
    def render_html(self, xml: str) -> str:
        response = render(xml)
        self.assertEqual(response.status_code, 200)
        return response.body.decode("utf-8")

    def test_structured_info_callout_panel(self) -> None:
        xml = """
        <p>
          <ac:structured-macro ac:name="info" ac:schema-version="1">
            <ac:parameter ac:name="title">Important Notice</ac:parameter>
            <ac:rich-text-body>
              <p>This is a highlighted info panel content.</p>
            </ac:rich-text-body>
          </ac:structured-macro>
        </p>
        """

        html = self.render_html(xml)

        self.assertIn('class="panel panel-info"', html)
        self.assertIn('class="panel-title">Important Notice</div>', html)
        self.assertIn("<p>This is a highlighted info panel content.</p>", html)
        self.assertNotIn("<p><aside", html)

    def test_code_block_macro(self) -> None:
        xml = '''
        <p>
          <ac:structured-macro ac:name="code" ac:schema-version="1">
            <ac:parameter ac:name="language">python</ac:parameter>
            <ac:parameter ac:name="title">Example Script</ac:parameter>
            <ac:parameter ac:name="linenumbers">true</ac:parameter>
            <ac:plain-text-body><![CDATA[def hello_world():
    print("Hello from Confluence XML!")
]]></ac:plain-text-body>
          </ac:structured-macro>
        </p>
        '''

        html = self.render_html(xml)

        self.assertIn('class="code-title">Example Script</div>', html)
        self.assertIn('data-language="python"', html)
        self.assertIn('data-line-numbers="true"', html)
        self.assertIn("def hello_world():", html)
        self.assertIn("&quot;Hello from Confluence XML!&quot;", html)
        self.assertNotIn("<p><pre", html)

    def test_internal_confluence_page_link(self) -> None:
        xml = '''
        <p>
          <ac:link>
            <ri:page ri:content-title="Target Page Title" ri:space-key="DOCS" />
            <ac:plain-text-link-body><![CDATA[Click here to read more]]></ac:plain-text-link-body>
          </ac:link>
        </p>
        '''

        html = self.render_html(xml)

        self.assertIn('class="internal-link"', html)
        self.assertIn('title="Confluence page: Target Page Title"', html)
        self.assertIn('data-space-key="DOCS"', html)
        self.assertIn(">Click here to read more</span>", html)

    def test_status_badge(self) -> None:
        xml = """
        <p>
          Status:
          <ac:structured-macro ac:name="status" ac:schema-version="1">
            <ac:parameter ac:name="title">IN PROGRESS</ac:parameter>
            <ac:parameter ac:name="colour">Yellow</ac:parameter>
          </ac:structured-macro>
        </p>
        """

        html = self.render_html(xml)

        self.assertIn("Status:", html)
        self.assertIn('class="status-lozenge status-Yellow"', html)
        self.assertIn(">IN PROGRESS</span>", html)

    def test_two_column_equal_layout(self) -> None:
        xml = """
        <ac:layout>
          <ac:layout-section ac:type="two_equal">
            <ac:layout-cell>
              <p>Left column content</p>
            </ac:layout-cell>
            <ac:layout-cell>
              <p>Right column content</p>
            </ac:layout-cell>
          </ac:layout-section>
        </ac:layout>
        """

        html = self.render_html(xml)

        self.assertIn('class="layout"', html)
        self.assertEqual(html.count('class="layout-cell"'), 2)
        self.assertIn("<p>Left column content</p>", html)
        self.assertIn("<p>Right column content</p>", html)

    def test_expand_collapsible_block(self) -> None:
        xml = """
        <p>
          <ac:structured-macro ac:name="expand" ac:schema-version="1">
            <ac:parameter ac:name="title">Click to view details</ac:parameter>
            <ac:rich-text-body>
              <p>Hidden text that expands on user click.</p>
            </ac:rich-text-body>
          </ac:structured-macro>
        </p>
        """

        html = self.render_html(xml)

        self.assertIn("<details>", html)
        self.assertIn("<summary>Click to view details</summary>", html)
        self.assertIn("<p>Hidden text that expands on user click.</p>", html)
        self.assertNotIn("<p><details", html)

    def test_embedded_internal_attachment_image(self) -> None:
        xml = """
        <p>
          <ac:image ac:align="center" ac:width="500">
            <ri:attachment ri:filename="screenshot.png" />
          </ac:image>
        </p>
        """

        html = self.render_html(xml)

        self.assertIn('class="image-placeholder image-center"', html)
        self.assertIn('data-filename="screenshot.png"', html)
        self.assertIn('data-width="500"', html)
        self.assertIn('style="max-width: 500px"', html)
        self.assertIn("Attachment: screenshot.png", html)

    def test_table_of_contents_macro(self) -> None:
        xml = """
        <p>
          <ac:structured-macro ac:name="toc" ac:schema-version="1">
            <ac:parameter ac:name="printable">true</ac:parameter>
            <ac:parameter ac:name="maxLevel">3</ac:parameter>
            <ac:parameter ac:name="type">list</ac:parameter>
          </ac:structured-macro>
        </p>
        """

        html = self.render_html(xml)

        self.assertIn('class="toc-macro"', html)
        self.assertIn('aria-label="Table of contents"', html)
        self.assertIn("Table of contents", html)

    def test_table_of_contents_resolves_page_headings_and_respects_max_level(self) -> None:
        xml = """
        <h1>Release Plan</h1>
        <ac:structured-macro ac:name="toc">
          <ac:parameter ac:name="maxLevel">2</ac:parameter>
          <ac:parameter ac:name="type">list</ac:parameter>
        </ac:structured-macro>
        <h2>Scope &amp; Goals</h2>
        <h3>Implementation detail</h3>
        <h2>Scope &amp; Goals</h2>
        """

        html = self.render_html(xml)

        self.assertIn('<h1 id="release-plan">Release Plan</h1>', html)
        self.assertIn('<h2 id="scope-goals">Scope &amp; Goals</h2>', html)
        self.assertIn('<h2 id="scope-goals-2">Scope &amp; Goals</h2>', html)
        self.assertIn('<a href="#release-plan">Release Plan</a>', html)
        self.assertIn('<a href="#scope-goals">Scope &amp; Goals</a>', html)
        self.assertIn('<a href="#scope-goals-2">Scope &amp; Goals</a>', html)
        self.assertNotIn('<a href="#implementation-detail">', html)

    def test_user_mention(self) -> None:
        xml = """
        <p>
          Hey <ac:link><ri:user ri:userkey="8a7f80824b260021014b26002e210000" /></ac:link>, please review this section.
        </p>
        """

        html = self.render_html(xml)

        self.assertIn("Hey ", html)
        self.assertIn('class="user-mention"', html)
        self.assertIn('data-user-key="8a7f80824b260021014b26002e210000"', html)
        self.assertIn("@8a7f80824b260021014b26002e210000", html)
        self.assertIn(", please review this section.", html)

    def test_jira_issues_macro(self) -> None:
        xml = """
        <p>
          <ac:structured-macro ac:name="jira" ac:schema-version="1">
            <ac:parameter ac:name="server">JIRA Local</ac:parameter>
            <ac:parameter ac:name="jqlQuery">project = PROJ AND status = Open</ac:parameter>
            <ac:parameter ac:name="maximumIssues">10</ac:parameter>
          </ac:structured-macro>
        </p>
        """

        html = self.render_html(xml)

        self.assertIn('class="jira-macro"', html)
        self.assertIn('data-maximum-issues="10"', html)
        self.assertIn("JIRA Local", html)
        self.assertIn("project = PROJ AND status = Open", html)
        self.assertNotIn("<p><section", html)

    def test_task_checkbox_list(self) -> None:
        xml = """
        <ac:task-list>
          <ac:task>
            <ac:task-id>1</ac:task-id>
            <ac:task-status>complete</ac:task-status>
            <ac:task-body>Draft initial documentation</ac:task-body>
          </ac:task>
          <ac:task>
            <ac:task-id>2</ac:task-id>
            <ac:task-status>incomplete</ac:task-status>
            <ac:task-body>Review with product owner</ac:task-body>
          </ac:task>
        </ac:task-list>
        """

        html = self.render_html(xml)

        self.assertIn('<ul class="task-list">', html)
        self.assertEqual(html.count('type="checkbox"'), 2)
        self.assertEqual(html.count(" checked"), 1)
        self.assertIn("Draft initial documentation", html)
        self.assertIn("Review with product owner", html)


if __name__ == "__main__":
    unittest.main()
