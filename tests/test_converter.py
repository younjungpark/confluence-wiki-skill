import unittest
import sys
import os

# Add scripts directory to path to allow import
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
from md_to_confluence import convert_file, convert_to_confluence

class TestMdToConfluence(unittest.TestCase):
    
    def test_headings(self):
        """Test Heading Conversion"""
        self.assertIn("h1. Title", convert_to_confluence("# Title"))
        self.assertIn("h2. SubTitle", convert_to_confluence("## SubTitle"))
        self.assertIn("h3. SubSubTitle", convert_to_confluence("### SubSubTitle"))
        
        # New: Test heading with leading spaces (Robustness fix)
        self.assertIn("h2. Space Title", convert_to_confluence("  ## Space Title"))
        
        # New: Test heading with formatting (Order of operations fix)
        self.assertIn("h2. Formatted Title", convert_to_confluence("## **Formatted Title**"))

        # New: Inline code in headings should not keep markdown backticks
        self.assertIn("h2. 설정 설계 (application.yml)", convert_to_confluence("## 설정 설계 (`application.yml`)"))

    def test_heading_with_markdown_link_conversion(self):
        """Heading markdown links should be converted to Confluence link syntax."""
        input_md = "### 8.1 단위 테스트 ([ConnectionPoolManagerTest](/c:/work/path/ConnectionPoolManagerTest.java))"
        result = convert_to_confluence(input_md)
        self.assertIn(
            "h3. 8.1 단위 테스트 ([ConnectionPoolManagerTest|/c:/work/path/ConnectionPoolManagerTest.java])",
            result
        )

    def test_bold_text(self):
        """Test Bold Text Conversion"""
        # Should add spaces for better rendering in Confluence
        self.assertEqual(convert_to_confluence("**Bold**").strip(), "*Bold*")
        self.assertEqual(convert_to_confluence("Text**Bold**Text").strip(), "Text *Bold* Text")

    def test_basic_lists(self):
        """Test Basic List Conversion"""
        self.assertEqual(convert_to_confluence("* Item 1").strip(), "* Item 1")
        self.assertEqual(convert_to_confluence("  * Item 2").strip(), "** Item 2")
        self.assertEqual(convert_to_confluence("1. Item 1").strip(), "# Item 1")

    def test_nested_bullet_list_three_levels(self):
        """Two-space indents should preserve nested depth (root -> child -> grandchild)."""
        input_md = """
- Root
  - Child
    - Grandchild
"""
        result = convert_to_confluence(input_md)
        self.assertIn("* Root", result)
        self.assertIn("** Child", result)
        self.assertIn("*** Grandchild", result)

    def test_numbered_list_nested_under_bullet(self):
        """Nested numbered list under bullet list should be rendered as mixed markers (e.g., **#)."""
        input_md = """
- 권장안
  - 동작:
    1. Step 1
    2. Step 2
"""
        result = convert_to_confluence(input_md)
        self.assertIn("* 권장안", result)
        self.assertIn("** 동작:", result)
        self.assertIn("**# Step 1", result)
        self.assertIn("**# Step 2", result)
        self.assertNotIn("## Step 1", result)

    def test_bullet_lines_under_numbered_list_keep_numbering(self):
        """Bullets directly under numbered items should be converted to #* to avoid numbering reset in Confluence."""
        input_md = """
1. Draining 전환
- 종료 절차 시작

2. 대기
- 종료 시작 시각 기록
"""
        result = convert_to_confluence(input_md)
        self.assertIn("# Draining 전환", result)
        self.assertIn("#* 종료 절차 시작", result)
        self.assertIn("# 대기", result)
        self.assertIn("#* 종료 시작 시각 기록", result)
        self.assertNotIn("\n* 종료 절차 시작", result)

    def test_numbered_list_with_code_block_keeps_visible_numbers(self):
        """When a numbered item is followed by code block, preserve explicit numbering text."""
        input_md = """
1. Codex

```text
C:\\Users\\user\\.codex\\skills\\confluence-wiki-skill
```

2. Antigravity + Gemini

```text
C:\\Users\\user\\.gemini\\skills\\confluence-wiki-skill
```
"""
        result = convert_to_confluence(input_md)
        self.assertIn("1) Codex", result)
        self.assertIn("2) Antigravity + Gemini", result)
        self.assertNotIn("# Codex", result)
        self.assertNotIn("# Antigravity + Gemini", result)

    def test_mermaid_code_block_is_collapsed_without_fence_markers(self):
        """Mermaid code blocks should include attachment image markup before collapsed source code."""
        input_md = """
```mermaid
sequenceDiagram
    A->>B: Hello
```
"""
        result = convert_to_confluence(input_md)
        self.assertIn("!mermaid-diagram-1.png|width=900!", result)
        self.assertIn("{code:title=mermaid-diagram-1.mmd|collapse=true}", result)
        self.assertNotIn("첨부 이미지:", result)
        self.assertIn("sequenceDiagram", result)
        self.assertIn("A->>B: Hello", result)
        self.assertNotIn("```mermaid", result)
        self.assertNotIn("```", result)

    def test_mermaid_attachment_name_uses_source_and_nearest_non_generic_heading(self):
        """Mermaid attachment names should use the source file stem and the nearest useful heading."""
        input_md = """
## 1. 동적 커넥션 풀 생명주기 (Dynamic Connection Pool)

### 동작 흐름도

```mermaid
flowchart TD
    A --> B
```
"""
        result = convert_to_confluence(input_md, source_base_name='core-mechanisms')
        self.assertIn("!core-mechanisms-dynamic-connection-pool.png|width=900!", result)
        self.assertIn("{code:title=core-mechanisms-dynamic-connection-pool.mmd|collapse=true}", result)
        self.assertNotIn("첨부 이미지:", result)

    def test_info_box_detection(self):
        """Test Info/Warning/Note Box Detection with various formats"""
        
        # Standard Info
        self.assertIn("{info:title=Info}", convert_to_confluence("> **Info**"))
        self.assertIn("{info:title=Info}", convert_to_confluence("> **ℹ️ Info**"))
        
        # Warning
        self.assertIn("{warning:title=Warning}", convert_to_confluence("> **Warning**"))
        self.assertIn("{warning:title=Warning}", convert_to_confluence("> **⚠️ Warning**"))
        
        # Note (bracket support - RECENT FIX)
        self.assertIn("{note:title=참고}", convert_to_confluence("> **[참고]**"))
        self.assertIn("{note:title=참고}", convert_to_confluence("> **참고**"))
        
        # Important
        self.assertIn("{warning:title=중요}", convert_to_confluence("> **중요**"))

    def test_box_content_with_lists(self):
        """Test Lists inside Check Boxes (Regression for Indentation Bug)"""
        input_md = """
> **[참고]**
> 1. Step 1
> 2. Step 2
>    * Detail A
>    * Detail B
"""
        result = convert_to_confluence(input_md)
        
        self.assertIn("{note:title=참고}", result)
        self.assertIn("# Step 1", result)
        self.assertIn("# Step 2", result)
        # Indented bullets under numbered list should be #*
        self.assertIn("#* Detail A", result) 
        self.assertIn("#* Detail B", result)

    def test_box_content_with_code_block(self):
        """Test Code Blocks inside Boxes"""
        input_md = """
> **Info**
> ```sql
> SELECT * FROM table;
> ```
"""
        result = convert_to_confluence(input_md)
        self.assertIn("{code}", result)
        self.assertIn("SELECT * FROM table;", result)

    def test_generic_blockquote_conversion(self):
        """Plain markdown blockquotes should become Confluence quote macros."""
        input_md = """
> DAT-16은 접속 정책을 먼저 고정한다.
>
> 후속 SQL 실행 엔진은 별도 단계에서 다룬다.
"""
        result = convert_to_confluence(input_md)
        self.assertIn("{quote}", result)
        self.assertIn("DAT-16은 접속 정책을 먼저 고정한다.", result)
        self.assertIn("후속 SQL 실행 엔진은 별도 단계에서 다룬다.", result)
        self.assertNotIn("> DAT-16은", result)

    def test_table_conversion(self):
        """Test Table Conversion"""
        input_md = """
| Header A | Header B |
|---|---|
| Cell 1 | Cell 2 |
"""
        result = convert_to_confluence(input_md)
        self.assertIn("|| Header A || Header B ||", result)
        self.assertIn("| Cell 1 | Cell 2 |", result)

    def test_link_conversion(self):
        """Test Link Conversion"""
        self.assertEqual(convert_to_confluence("[Google](https://google.com)").strip(), "[Google|https://google.com]")

    def test_relative_markdown_link_conversion(self):
        """Relative Markdown links should become Confluence link syntax."""
        result = convert_to_confluence("[Overview](dataapi-docker-hub-repository-overview.md)")
        self.assertEqual(result.strip(), "[Overview|dataapi-docker-hub-repository-overview.md]")

    def test_relative_markdown_link_in_numbered_list_conversion(self):
        """Relative links in numbered list items should not remain as raw Markdown."""
        input_md = "3. Write 탭에 [dataapi-docker-hub-repository-overview.md](dataapi-docker-hub-repository-overview.md) 파일"
        result = convert_to_confluence(input_md)
        self.assertIn(
            "# Write 탭에 [dataapi-docker-hub-repository-overview.md|dataapi-docker-hub-repository-overview.md] 파일",
            result,
        )
        self.assertNotIn("\\[dataapi-docker-hub-repository-overview.md]", result)
        self.assertNotIn("](dataapi-docker-hub-repository-overview.md)", result)

    def test_image_conversion_to_attachment_markup(self):
        """Markdown images should become Confluence attachment image markup."""
        result = convert_to_confluence("![10 VU p95](images/p95-latency-10vu.png)")
        self.assertEqual(result.strip(), "!p95-latency-10vu.png|width=900!")
        self.assertNotIn("![", result)
        self.assertNotIn("images/", result)

    def test_image_conversion_with_absolute_windows_path(self):
        """Only the image file name should remain for local attachment references."""
        result = convert_to_confluence("![Chart](C:\\work\\report\\images\\chart.png)")
        self.assertEqual(result.strip(), "!chart.png|width=900!")

    def test_inline_code_in_box(self):
        """Test Inline Code conversion inside Box (Bug Fix)"""
        input_md = "> **[Note]**\n> Use `CREATE USER` command."
        result = convert_to_confluence(input_md)
        self.assertIn("{note:title=참고}", result)
        # Should NOT contain backticks (Confluence doesn't interpret them)
        self.assertNotIn("`CREATE USER`", result)
        self.assertIn("Use CREATE USER command.", result)

    def test_inline_code_is_converted_to_plain_text(self):
        """Inline code should become plain text without Markdown backticks or Confluence styling."""
        input_md = '* `INSERT INTO T (INT_COL) VALUES (?)` + `"123"`: 일반 scalar 경로'
        result = convert_to_confluence(input_md)
        self.assertIn('* INSERT INTO T (INT_COL) VALUES (?) + "123": 일반 scalar 경로', result)
        self.assertNotIn('{{', result)

    def test_inline_code_does_not_add_visible_escape_for_hyphen(self):
        """Inline code should not add visible escapes around hyphens."""
        input_md = 'DataAPI는 `data-api-<version>-altibase7x.jar`를 제공한다.'
        result = convert_to_confluence(input_md)
        self.assertIn('data-api-<version>-altibase7x.jar', result)
        self.assertNotIn('data\\-api\\-<version>\\-altibase7x.jar', result)
        self.assertNotIn('data&#45;api', result)
        self.assertNotIn('{{', result)

    def test_inline_code_does_not_add_visible_escape_for_underscore(self):
        """Inline code should not add visible escapes around underscores."""
        result = convert_to_confluence('기본 role은 `DATA_API_ACCESS`이다.')
        self.assertIn('DATA_API_ACCESS', result)
        self.assertNotIn('DATA&#95;API', result)
        self.assertNotIn('{{', result)

    def test_inline_code_url_keeps_hyphen_without_visible_escape(self):
        """Inline code URLs should not gain visible backslash escapes around hyphens."""
        result = convert_to_confluence('* Swagger UI: `http://localhost:8080/dataapi/swagger-ui.html`')
        self.assertIn('http://localhost:8080/dataapi/swagger-ui.html', result)
        self.assertNotIn('swagger\\-ui', result)
        self.assertNotIn('swagger&#45;ui', result)
        self.assertNotIn('{{', result)

    def test_horizontal_rule_removal(self):
        """Test Horizontal Rule (---) is removed"""
        result = convert_to_confluence("Text Before\n---\nText After")
        self.assertNotIn("---", result)
        self.assertIn("Text Before", result)
        self.assertIn("Text After", result)

    def test_convert_file_appends_markdown_source_attachment_link(self):
        """File conversion should append a Confluence attachment link to the source Markdown."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, 'configuration-matrix.md')
            output_path = os.path.join(temp_dir, 'configuration-matrix.wiki')
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write('# 설정 매트릭스\n')
            convert_file(input_path, output_path)
            with open(output_path, 'r', encoding='utf-8') as f:
                result = f.read()

        self.assertIn('h2. MarkDown 원본문서', result)
        self.assertIn('[configuration-matrix.md|^configuration-matrix.md]', result)
        self.assertNotIn('[configuration-matrix.md^configuration-matrix.md]', result)


if __name__ == '__main__':
    unittest.main()
