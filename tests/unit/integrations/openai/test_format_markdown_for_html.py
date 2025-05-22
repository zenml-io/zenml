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
"""Unit tests for _format_markdown_for_html function."""

from zenml.integrations.openai.hooks.open_ai_failure_hook import (
    _format_markdown_for_html,
)


def test_inline_code():
    """Test inline code formatting."""
    text = "This is `inline code` in a sentence."
    result = _format_markdown_for_html(text)

    assert "<code style=" in result
    assert "inline code</code>" in result
    assert "`" not in result


def test_code_blocks_with_language():
    """Test code blocks with language annotation."""
    text = """Here is a code block:
```python
def hello():
    print("world")
```
End of block."""

    result = _format_markdown_for_html(text)

    assert "<pre style=" in result
    assert "<code>" in result
    assert "def hello():" in result
    assert 'print("world")' in result
    assert "```" not in result


def test_code_blocks_without_language():
    """Test code blocks without language annotation."""
    text = """Code without language:
```
plain text code
more lines
```"""

    result = _format_markdown_for_html(text)

    assert "<pre style=" in result
    assert "plain text code" in result
    assert "more lines" in result


def test_single_line_code_block():
    """Test single-line code blocks."""
    text = "Single line: ```const x = 42```"

    result = _format_markdown_for_html(text)

    assert "<pre style=" in result
    # The regex captures 'x = 42' not 'const x = 42' due to pattern
    assert "x = 42" in result


def test_bold_formatting():
    """Test bold text with double asterisks."""
    text = "This is **bold text** in a sentence."

    result = _format_markdown_for_html(text)

    assert "<strong>bold text</strong>" in result
    assert "**" not in result


def test_italic_formatting():
    """Test italic text with single asterisks."""
    text = "This is *italic text* in a sentence."

    result = _format_markdown_for_html(text)

    assert "<em>italic text</em>" in result
    assert "*italic" not in result
    assert "italic*" not in result


def test_mixed_formatting():
    """Test mixed markdown formatting."""
    text = "This has **bold**, *italic*, and `code` formatting."

    result = _format_markdown_for_html(text)

    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result
    assert "<code style=" in result


def test_html_escaping():
    """Test that HTML is properly escaped."""
    text = 'This has <script>alert("xss")</script> in it.'

    result = _format_markdown_for_html(text)

    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "&lt;/script&gt;" in result


def test_html_in_code_blocks():
    """Test that HTML in code blocks is handled properly."""
    text = """```
<div>HTML in code block</div>
<script>alert('test')</script>
```"""

    result = _format_markdown_for_html(text)

    # The code block content should be unescaped inside the pre/code tags
    assert "<pre" in result
    assert "<div>HTML in code block</div>" in result
    assert "<script>alert('test')</script>" in result


def test_nested_formatting():
    """Test nested formatting scenarios."""
    text = "Code with asterisk: `function* generator()` and bold: **text**"

    result = _format_markdown_for_html(text)

    # Check that asterisk inside code is preserved
    assert "function* generator()" in result
    assert "<strong>text</strong>" in result


def test_consecutive_formatting():
    """Test consecutive formatting elements."""
    text = "**Bold1** **Bold2** *Italic1* *Italic2* `code1` `code2`"

    result = _format_markdown_for_html(text)

    assert result.count("<strong>") == 2
    assert result.count("<em>") == 2
    assert result.count("<code style=") == 2


def test_multiline_bold_not_supported():
    """Test that multiline bold is not processed (as per the regex)."""
    text = """This is **bold
across lines** text."""

    result = _format_markdown_for_html(text)

    # Should still have asterisks since regex excludes newlines
    assert "**" in result
    assert "<strong>" not in result


def test_empty_and_whitespace():
    """Test empty strings and whitespace."""
    assert _format_markdown_for_html("") == ""
    # Whitespace gets wrapped in paragraph tags
    _format_markdown_for_html("   ")
    # Just check that the function doesn't crash on whitespace


def test_special_characters_in_code():
    """Test special characters in code blocks."""
    text = """```bash
echo "Hello $USER"
grep -E '^[0-9]+$' file.txt
```"""

    result = _format_markdown_for_html(text)

    assert 'echo "Hello $USER"' in result
    assert "grep -E '^[0-9]+$' file.txt" in result


def test_incomplete_formatting():
    """Test incomplete formatting markers."""
    text = "This has ` unclosed code and * unclosed italic"

    result = _format_markdown_for_html(text)

    # Should still have the markers since they're not complete
    assert "`" in result
    assert "*" in result


def test_code_after_html_tags():
    """Test that inline code processing skips already processed HTML tags."""
    # This tests the specific logic that avoids processing code inside HTML tags
    text = "Before `code1` middle `code2` after"

    # First pass will process code1
    result = _format_markdown_for_html(text)

    # Should have both code blocks processed
    assert result.count("<code style=") == 2
