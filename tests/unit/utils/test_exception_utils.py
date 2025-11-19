"""Unit tests for exception_utils module."""

import re
from unittest.mock import Mock, patch

import pytest

from zenml.utils.exception_utils import (
    collect_exception_information,
)


def test_regex_pattern_no_syntax_warning():
    """Test that the regex pattern in collect_exception_information doesn't produce SyntaxWarning."""
    # Create a mock step instance
    mock_step = Mock()
    mock_step.entrypoint = lambda: None

    # Mock the inspect functions to simulate a source file
    with (
        patch(
            "zenml.utils.exception_utils.inspect.getsourcefile"
        ) as mock_getsourcefile,
        patch(
            "zenml.utils.exception_utils.inspect.getsourcelines"
        ) as mock_getsourcelines,
    ):
        mock_getsourcefile.return_value = "/test/file.py"
        mock_getsourcelines.return_value = (
            ["def test():\n", "    pass\n"],
            10,
        )

        # Create a sample exception with traceback
        try:
            raise ValueError("test error")
        except ValueError as e:
            test_exception = e

        # This should not produce any SyntaxWarning
        with pytest.warns(None) as warning_list:
            result = collect_exception_information(test_exception, mock_step)

        # Check that no SyntaxWarning was raised
        syntax_warnings = [
            w for w in warning_list if issubclass(w.category, SyntaxWarning)
        ]
        assert len(syntax_warnings) == 0, "SyntaxWarning should not be raised"

        # Verify the function still works correctly
        assert result is not None


def test_regex_pattern_matches_correctly():
    """Test that the regex pattern correctly matches file paths and line numbers."""
    # Test the actual regex pattern used in the function (with re.escape as in production)
    source_file = "/path/to/test/file.py"
    line_pattern = re.compile(rf'File "{re.escape(source_file)}", line (\d+),')

    # Test various traceback line formats
    test_cases = [
        ('  File "/path/to/test/file.py", line 42, in function', "42"),
        ('File "/path/to/test/file.py", line 1, in <module>', "1"),
        ('  File "/path/to/test/file.py", line 999, in method', "999"),
    ]

    for test_line, expected_line_num in test_cases:
        match = line_pattern.search(test_line)
        assert match is not None, f"Pattern should match: {test_line}"
        assert match.group(1) == expected_line_num, (
            f"Should extract line number {expected_line_num}"
        )

    # Test non-matching lines
    non_matching = [
        'File "/different/file.py", line 42, in function',
        "Not a traceback line",
        '  File "/path/to/test/file.py" line 42 in function',  # Missing comma after quote
    ]

    for test_line in non_matching:
        match = line_pattern.search(test_line)
        assert match is None, f"Pattern should not match: {test_line}"


def test_regex_pattern_matches_windows_paths_and_special_chars():
    """Ensure Windows-style paths and special characters are matched correctly."""
    # Test Windows path with special characters
    source_file_win = r"C:\Program Files (x86)\MyApp\src\test(file)[v1].py"
    line_pattern_win = re.compile(
        rf'File "{re.escape(source_file_win)}", line (\d+),'
    )

    test_line = f'  File "{source_file_win}", line 123, in some_function'
    match = line_pattern_win.search(test_line)
    assert match is not None, (
        "Pattern should match Windows path with special characters"
    )
    assert match.group(1) == "123"

    # Non-matching different path
    non_match_line = (
        r'  File "C:\Other\path\file.py", line 123, in some_function'
    )
    assert line_pattern_win.search(non_match_line) is None
