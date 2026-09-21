from confluence_content_parser import ConfluenceParser

# Initialize the parser
parser = ConfluenceParser()

# Parse Confluence Storage Format content
content = """
<ac:layout>
    <ac:layout-section ac:type="fixed-width">
        <ac:layout-cell>
            <h2>My Document</h2>
            <p>This is a <strong>bold</strong> paragraph.</p>
            <ac:structured-macro ac:name="info">
                <ac:rich-text-body>
                    <p>This is an info panel.</p>
                </ac:rich-text-body>
            </ac:structured-macro>
        </ac:layout-cell>
    </ac:layout-section>
</ac:layout>
"""

# Parse the content
document = parser.parse(content)

# Access the structured data
print(f"Document text: {document.text}")

# Find all nodes of specific types
from confluence_content_parser import HeadingElement, PanelMacro

headings = document.find_all(HeadingElement)
panels = document.find_all(PanelMacro)

# Or find multiple types at once
headings, panels = document.find_all(HeadingElement, PanelMacro)

print(f"Found {len(headings)} headings and {len(panels)} panels")

# Navigate the structure
for node in document.walk():
    print(f"Node type: {type(node).__name__}")

