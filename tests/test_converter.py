import unittest
import sys
import os
import tempfile

# Add scripts directory to path to allow import
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
from md_to_confluence import (
    convert_file,
    convert_to_confluence,
    extract_mermaid_sources,
    render_mermaid_sources,
)

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

    def test_inline_code_escapes_confluence_emoticons(self):
        """Inline code should not become Confluence emoticons after backticks are removed."""
        result = convert_to_confluence("nested scalar subquery는 `cast(?)` 형태로 타입을 보강한다.")
        self.assertIn("cast\\(?)", result)
        self.assertNotIn("cast(?)", result)

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
        """Relative Markdown file links should become Confluence attachment links."""
        result = convert_to_confluence("[Overview](dataapi-docker-hub-repository-overview.md)")
        self.assertEqual(result.strip(), "[Overview|^dataapi-docker-hub-repository-overview.md]")

    def test_dot_relative_markdown_link_conversion(self):
        """Dot-relative Markdown file links should become Confluence attachment links."""
        result = convert_to_confluence("[Overview](./dataapi-docker-hub-repository-overview.md)")
        self.assertEqual(result.strip(), "[Overview|^dataapi-docker-hub-repository-overview.md]")

    def test_relative_markdown_link_in_numbered_list_conversion(self):
        """Relative links in numbered list items should not remain as raw Markdown."""
        input_md = "3. Write 탭에 [dataapi-docker-hub-repository-overview.md](dataapi-docker-hub-repository-overview.md) 파일"
        result = convert_to_confluence(input_md)
        self.assertIn(
            "# Write 탭에 [dataapi-docker-hub-repository-overview.md|^dataapi-docker-hub-repository-overview.md] 파일",
            result,
        )
        self.assertNotIn("\\[dataapi-docker-hub-repository-overview.md]", result)
        self.assertNotIn("](dataapi-docker-hub-repository-overview.md)", result)

    def test_relative_path_markdown_link_stays_regular_link(self):
        """Relative paths with directories are not assumed to be same-page attachments."""
        result = convert_to_confluence("[Spec](../product-specs/sql-api-contract.md)")
        self.assertEqual(result.strip(), "[Spec|../product-specs/sql-api-contract.md]")

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
        self.assertIn('* INSERT INTO T (INT_COL) VALUES \\(?) + "123": 일반 scalar 경로', result)
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

    def test_convert_file_omits_markdown_source_attachment_link_by_default(self):
        """File conversion should omit the source Markdown attachment link by default."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, 'configuration-matrix.md')
            output_path = os.path.join(temp_dir, 'configuration-matrix.wiki')
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write('# 설정 매트릭스\n')
            convert_file(input_path, output_path)
            with open(output_path, 'r', encoding='utf-8') as f:
                result = f.read()

        self.assertNotIn('h2. MarkDown 원본문서', result)
        self.assertNotIn('[configuration-matrix.md|^configuration-matrix.md]', result)

    def test_convert_file_appends_markdown_source_attachment_link_when_enabled(self):
        """File conversion should append the source Markdown attachment link when enabled."""
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, 'configuration-matrix.md')
            output_path = os.path.join(temp_dir, 'configuration-matrix.wiki')
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write('# 설정 매트릭스\n')
            convert_file(input_path, output_path, include_markdown_source=True)
            with open(output_path, 'r', encoding='utf-8') as f:
                result = f.read()

        self.assertIn('h2. MarkDown 원본문서', result)
        self.assertIn('[configuration-matrix.md|^configuration-matrix.md]', result)
        self.assertNotIn('[configuration-matrix.md^configuration-matrix.md]', result)


    def test_italic_text(self):
        """Markdown italic (*text*) is Confluence italic (_text_), not bold."""
        self.assertEqual(convert_to_confluence("a *ital* b").strip(), "a _ital_ b")
        self.assertEqual(convert_to_confluence("*기울임* 과 **굵게**").strip(), "_기울임_ 과  *굵게*")

    def test_italic_does_not_touch_literal_asterisks(self):
        """Wildcards, arithmetic and inline code must not be read as emphasis."""
        self.assertEqual(convert_to_confluence("경로는 /actuator/** 이고 파일은 *.log 이다").strip(),
                         "경로는 /actuator/** 이고 파일은 *.log 이다")
        self.assertEqual(convert_to_confluence("2 * 3 * 4").strip(), "2 * 3 * 4")
        self.assertEqual(convert_to_confluence("파일은 `*.log` 와 `*.txt` 이다").strip(), "파일은 *.log 와 *.txt 이다")
        self.assertEqual(convert_to_confluence("* *강조* 항목").strip(), "* _강조_ 항목")

    def test_strikethrough_text(self):
        """Markdown strikethrough (~~text~~) is Confluence strikethrough (-text-)."""
        self.assertEqual(convert_to_confluence("끝 ~~취소선~~ 입니다").strip(), "끝 -취소선- 입니다")
        self.assertEqual(convert_to_confluence("`~~x~~` 는 그대로").strip(), "~~x~~ 는 그대로")

    def test_table_escaped_pipe_stays_in_cell(self):
        """An escaped pipe inside a cell must not create an extra column."""
        input_md = """
| A \\| B | C |
|---|---|
| x\\|y | z |
"""
        result = convert_to_confluence(input_md)
        self.assertIn("|| A \\| B || C ||", result)
        self.assertIn("| x\\|y | z |", result)
        self.assertNotIn("| x\\ | y |", result)

    def test_bullet_list_after_numbered_list_is_separate_list(self):
        """A bullet (task) list after a blank line following the last numbered item is a new list."""
        input_md = """
1. 첫째
2. 둘째

- [ ] 할 일
- [x] 한 일
"""
        result = convert_to_confluence(input_md)
        self.assertIn("# 둘째\n\n* \\[ ] 할 일\n* \\[x] 한 일", result)
        self.assertNotIn("#* \\[ ] 할 일", result)

    def test_loose_bullets_between_numbered_items_stay_nested(self):
        """Bullets separated by blank lines stay nested when the numbered list continues afterwards."""
        input_md = """
1. 첫째

- 설명

2. 둘째
"""
        result = convert_to_confluence(input_md)
        self.assertIn("# 첫째\n#* 설명\n# 둘째", result)

    def test_bullets_under_numbered_item_keep_nested_depth(self):
        """Bullets nested under a numbered item keep each level, whatever the indent width."""
        for step in (2, 3, 4):
            pad = ' ' * step
            input_md = f"1. 단계\n{pad}- 하위\n{pad * 2}- 더 하위\n{pad * 3}- 가장 하위\n{pad}- 다시 하위\n2. 다음"
            result = convert_to_confluence(input_md)
            self.assertEqual(
                result,
                "# 단계\n#* 하위\n#** 더 하위\n#*** 가장 하위\n#* 다시 하위\n# 다음",
                f"indent width {step}",
            )

    def test_unindented_bullet_with_indented_child_under_numbered_item(self):
        """A child of an unindented bullet under a numbered item is one level deeper."""
        result = convert_to_confluence("1. 단계\n- 설명\n  - 세부\n2. 다음")
        self.assertEqual(result, "# 단계\n#* 설명\n#** 세부\n# 다음")

    def test_bullets_under_nested_numbered_item_keep_numbered_prefix(self):
        """Bullets under a nested numbered item stay under that item, not the top-level list."""
        result = convert_to_confluence("1. 상위\n   1. 하위 번호\n      - 불릿\n        - 불릿 하위")
        self.assertEqual(result, "# 상위\n## 하위 번호\n##* 불릿\n##** 불릿 하위")

    def test_box_bullets_under_numbered_item_keep_nested_depth(self):
        """Nested bullets inside a box keep each level too."""
        input_md = "> [!NOTE]\n> 1. 단계\n>    - 하위\n>      - 더 하위"
        result = convert_to_confluence(input_md)
        self.assertIn("# 단계\n#* 하위\n#** 더 하위", result)

    def test_extract_mermaid_sources_returns_name_and_body(self):
        """Only collapsed Mermaid blocks are extracted, with the .mmd name the image tag implies."""
        input_md = (
            "## Sync (Jenkins)\n\n```mermaid\nflowchart LR\n    A --> B\n```\n\n"
            "```bash\necho hi\n```\n\n"
            "## Order (Sequence)\n\n```mermaid\nsequenceDiagram\n    A->>B: hi\n```"
        )
        sources = extract_mermaid_sources(convert_to_confluence(input_md, "guide"))
        self.assertEqual(
            sources,
            [
                ("guide-jenkins.mmd", "flowchart LR\n    A --> B\n"),
                ("guide-sequence.mmd", "sequenceDiagram\n    A->>B: hi\n"),
            ],
        )

    def test_convert_file_renders_mermaid_with_mmdc(self):
        """--render-mermaid writes the .mmd source and asks mmdc for the .png the wiki refers to."""
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "fake-mmdc")
            calls = os.path.join(tmp, "calls.txt")
            with open(stub, "w", encoding="utf-8") as f:
                f.write(
                    f"#!{sys.executable}\n"
                    "import sys\n"
                    f"open({calls!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
                    "open(sys.argv[sys.argv.index('-o') + 1], 'wb').write(b'png')\n"
                )
            os.chmod(stub, 0o755)
            input_file = os.path.join(tmp, "guide.md")
            with open(input_file, "w", encoding="utf-8") as f:
                f.write("## Sync (Jenkins)\n\n```mermaid\nflowchart LR\n    A --> B\n```\n")
            output_file = os.path.join(tmp, "guide.wiki")
            image_dir = os.path.join(tmp, "images")

            convert_file(input_file, output_file, render_mermaid=True,
                         mermaid_dir=image_dir, mmdc_command=stub)

            with open(output_file, encoding="utf-8") as f:
                self.assertIn("!guide-jenkins.png|width=900!", f.read())
            with open(os.path.join(image_dir, "guide-jenkins.mmd"), encoding="utf-8") as f:
                self.assertEqual(f.read(), "flowchart LR\n    A --> B\n")
            self.assertTrue(os.path.exists(os.path.join(image_dir, "guide-jenkins.png")))
            with open(calls, encoding="utf-8") as f:
                self.assertIn("-b white -s 2", f.read())

    def test_mermaid_width_sets_image_tag_width(self):
        """--mermaid-width changes only the Mermaid image tags; Markdown images keep width=900."""
        input_md = "## Flow (Sync)\n\n```mermaid\nflowchart TB\n    A --> B\n```\n\n![Chart](images/chart.png)"
        result = convert_to_confluence(input_md, "guide", mermaid_width=350)
        self.assertIn("!guide-sync.png|width=350!", result)
        self.assertIn("!chart.png|width=900!", result)

    def test_render_mermaid_without_mmdc_reports_install_command(self):
        """A missing mmdc fails with the install command instead of leaving a dangling image tag silently."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError) as context:
                render_mermaid_sources([("a.mmd", "flowchart LR\n")], tmp, "no-such-mmdc-command")
            self.assertIn("@mermaid-js/mermaid-cli", str(context.exception))

if __name__ == '__main__':
    unittest.main()
