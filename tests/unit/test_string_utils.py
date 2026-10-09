#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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

"""Unit tests for string utility helpers: truncate_str and slugify."""

import pytest

from zenml.utils.string_utils import slugify, truncate_str


class TestTruncateStr:
    """Tests for the truncate_str utility function."""

    def test_returns_original_when_within_limit(self) -> None:
        """Short strings that fit within max_length are returned unchanged."""
        assert truncate_str("short", max_length=20) == "short"

    def test_returns_original_at_exact_limit(self) -> None:
        """Strings exactly equal to max_length are returned unchanged."""
        s = "a" * 20
        assert truncate_str(s, max_length=20) == s

    def test_truncates_long_string_with_default_suffix(self) -> None:
        """Strings exceeding max_length are shortened and get the default suffix."""
        result = truncate_str("a very long pipeline run name", max_length=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_truncates_with_custom_suffix(self) -> None:
        """A custom suffix is appended when truncating."""
        result = truncate_str("hello world foobar", max_length=10, suffix="…")
        assert len(result) == 10
        assert result.endswith("…")

    def test_empty_string_returns_empty(self) -> None:
        """An empty string is returned as-is."""
        assert truncate_str("", max_length=10) == ""

    def test_raises_when_max_length_less_than_suffix(self) -> None:
        """ValueError is raised when max_length cannot accommodate the suffix."""
        with pytest.raises(ValueError, match="max_length"):
            truncate_str("hello", max_length=2, suffix="...")

    def test_no_suffix_truncation(self) -> None:
        """With an empty suffix, plain truncation to max_length is applied."""
        result = truncate_str("hello world", max_length=5, suffix="")
        assert result == "hello"


class TestSlugify:
    """Tests for the slugify utility function."""

    def test_basic_slug(self) -> None:
        """Spaces and punctuation are converted to the default dash separator."""
        assert slugify("My Pipeline Run!") == "my-pipeline-run"

    def test_custom_separator(self) -> None:
        """A custom separator is applied between words."""
        assert slugify("Hello  World", separator="_") == "hello_world"

    def test_collapses_consecutive_separators(self) -> None:
        """Multiple consecutive non-alphanumeric chars produce a single separator."""
        assert slugify("foo---bar___baz") == "foo-bar-baz"

    def test_strips_leading_trailing_separators(self) -> None:
        """Leading and trailing separators are stripped from the result."""
        assert slugify("  hello  ") == "hello"

    def test_all_lowercase(self) -> None:
        """All uppercase characters are lowercased."""
        assert slugify("ZENML") == "zenml"

    def test_numeric_characters_preserved(self) -> None:
        """Numbers in the input are preserved in the slug."""
        assert slugify("pipeline-v2-run-42") == "pipeline-v2-run-42"

    def test_empty_string_returns_empty(self) -> None:
        """An empty input string produces an empty slug."""
        assert slugify("") == ""
