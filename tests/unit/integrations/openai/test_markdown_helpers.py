#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Unit tests for individual markdown formatting helper functions."""

from zenml.integrations.openai.hooks.open_ai_failure_hook import (
    _escape_html_safely,
    _format_bold,
    _format_bullet_lists,
    _format_code_blocks,
    _format_headers,
    _format_inline_code,
    _format_italics,
    _format_numbered_lists,
    _format_paragraphs,
)


def test_escape_html_safely():
    """Test HTML escaping."""
    text = '<script>alert("xss")</script>'
    result = _escape_html_safely(text)
    
    assert "&lt;script&gt;" in result
    assert "&lt;/script&gt;" in result
    assert "<script>" not in result


def test_format_code_blocks_basic():
    """Test basic code block formatting."""
    text = "```\ncode here\n```"
    result = _format_code_blocks(_escape_html_safely(text))
    
    assert "<pre style=" in result
    assert "<code>code here</code>" in result
    assert "```" not in result


def test_format_code_blocks_with_language():
    """Test code blocks with language identifier."""
    text = "```python\ndef hello():\n    pass\n```"
    result = _format_code_blocks(_escape_html_safely(text))
    
    assert "<pre style=" in result
    assert "def hello():" in result
    assert "pass" in result


def test_format_code_blocks_multiple():
    """Test multiple code blocks in same text."""
    text = "First:\n```\ncode1\n```\n\nSecond:\n```\ncode2\n```"
    result = _format_code_blocks(_escape_html_safely(text))
    
    assert result.count("<pre style=") == 2
    assert "code1" in result
    assert "code2" in result


def test_format_inline_code_basic():
    """Test basic inline code formatting."""
    text = "This is `inline code` here."
    result = _format_inline_code(text)
    
    assert '<code style="background-color: #f5f5f5' in result
    assert "inline code</code>" in result


def test_format_inline_code_skips_html_tags():
    """Test that inline code formatting skips existing HTML tags."""
    text = 'Before <pre>some pre</pre> middle `code` after'
    result = _format_inline_code(text)
    
    # Should not process content inside <pre> tags
    assert '<pre>some pre</pre>' in result
    # Should process code outside HTML tags
    assert '<code style=' in result


def test_format_bold_basic():
    """Test basic bold formatting."""
    text = "This is **bold text** here."
    result = _format_bold(text)
    
    assert "<strong>bold text</strong>" in result
    assert "**" not in result


def test_format_bold_multiple():
    """Test multiple bold sections."""
    text = "**First** and **second** bold"
    result = _format_bold(text)
    
    assert result.count("<strong>") == 2
    assert result.count("</strong>") == 2


def test_format_italics_asterisk():
    """Test italic formatting with asterisks."""
    text = "This is *italic text* here."
    result = _format_italics(text)
    
    assert "<em>italic text</em>" in result
    assert "*italic" not in result


def test_format_italics_underscore():
    """Test italic formatting with underscores."""
    text = "This is _italic text_ here."
    result = _format_italics(text)
    
    assert "<em>italic text</em>" in result
    assert "_italic" not in result


def test_format_italics_with_adjacent_bold():
    """Test that italic formatting handles text with bold markers correctly."""
    # Since we process bold before italics in the main function,
    # this test should reflect what _format_italics does when given text with asterisks
    text = "This has **bold** text"
    result = _format_italics(text)
    
    # The function will match *bold* within **bold** and convert it
    # This is expected behavior - in practice, bold is processed first
    assert "*<em>bold</em>*" in result


def test_format_headers_h1():
    """Test H1 header formatting."""
    text = "# Header 1\nSome text"
    result = _format_headers(text)
    
    assert "<h1>Header 1</h1>" in result
    assert "#" not in result


def test_format_headers_multiple_levels():
    """Test multiple header levels."""
    text = "# H1\n## H2\n### H3"
    result = _format_headers(text)
    
    assert "<h1>H1</h1>" in result
    assert "<h2>H2</h2>" in result
    assert "<h3>H3</h3>" in result


def test_format_headers_only_at_line_start():
    """Test that headers are only converted at line start."""
    text = "Not a # header\n# Real header"
    result = _format_headers(text)
    
    assert "Not a # header" in result  # Should remain unchanged
    assert "<h1>Real header</h1>" in result


def test_format_numbered_lists():
    """Test numbered list conversion to bullets."""
    text = "1. First item\n2. Second item\n3. Third item"
    result = _format_numbered_lists(text)
    
    assert "• First item" in result
    assert "• Second item" in result
    assert "• Third item" in result
    assert "1." not in result
    assert "2." not in result


def test_format_numbered_lists_mixed_content():
    """Test numbered lists with other content."""
    text = "Text before\n1. Item one\nNot a list\n2. Item two"
    result = _format_numbered_lists(text)
    
    assert "Text before" in result
    assert "• Item one" in result
    assert "Not a list" in result
    assert "• Item two" in result


def test_format_bullet_lists_basic():
    """Test basic bullet list formatting."""
    text = "- Item 1\n- Item 2\n- Item 3"
    result = _format_bullet_lists(text)
    
    assert "<ul>" in result
    assert "<li>Item 1</li>" in result
    assert "<li>Item 2</li>" in result
    assert "<li>Item 3</li>" in result
    assert "</ul>" in result


def test_format_bullet_lists_different_markers():
    """Test bullet lists with different markers."""
    text = "* Star item\n+ Plus item\n- Dash item\n• Bullet item"
    result = _format_bullet_lists(text)
    
    assert result.count("<li>") == 4
    assert "<li>Star item</li>" in result
    assert "<li>Plus item</li>" in result
    assert "<li>Dash item</li>" in result
    assert "<li>Bullet item</li>" in result


def test_format_bullet_lists_with_gaps():
    """Test bullet lists with non-list content between them."""
    text = "- Item 1\n- Item 2\n\nNot a list\n\n- Item 3\n- Item 4"
    result = _format_bullet_lists(text)
    
    # Should create two separate lists
    assert result.count("<ul>") == 2
    assert result.count("</ul>") == 2
    assert "Not a list" in result


def test_format_paragraphs_basic():
    """Test basic paragraph formatting."""
    text = "First paragraph.\n\nSecond paragraph."
    result = _format_paragraphs(text)
    
    assert "<p>First paragraph.</p>" in result
    assert "<p>Second paragraph.</p>" in result


def test_format_paragraphs_with_line_breaks():
    """Test paragraphs with line breaks."""
    text = "Line one\nLine two\nLine three"
    result = _format_paragraphs(text)
    
    assert "<p>Line one<br>Line two<br>Line three</p>" in result


def test_format_paragraphs_skips_block_elements():
    """Test that paragraphs skip existing block-level HTML."""
    text = "<h1>Header</h1>\n\nNormal paragraph\n\n<pre>Code</pre>"
    result = _format_paragraphs(text)
    
    # Should not wrap existing block elements
    assert "<p><h1>" not in result
    assert "<p><pre>" not in result
    # Should wrap normal text
    assert "<p>Normal paragraph</p>" in result


def test_format_paragraphs_multiple_empty_lines():
    """Test handling of multiple empty lines."""
    text = "First\n\n\n\nSecond"
    result = _format_paragraphs(text)
    
    # Should treat multiple empty lines as single paragraph break
    assert "<p>First</p>" in result
    assert "<p>Second</p>" in result
    assert result.count("<p>") == 2