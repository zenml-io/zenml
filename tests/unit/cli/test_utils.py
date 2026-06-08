import io

import pytest
from rich.console import Console

from zenml.cli import utils as cli_utils
from zenml.console import zenml_custom_theme
from zenml.models import Page


def test_print_page_info_does_not_render_backticks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = io.StringIO()
    test_console = Console(
        file=output,
        force_terminal=False,
        theme=zenml_custom_theme,
        width=100,
    )
    monkeypatch.setattr(cli_utils, "console", test_console)

    page = Page(index=1, max_size=10, total_pages=1, total=1, items=[])
    cli_utils.print_page_info(page)

    rendered_output = output.getvalue()
    assert rendered_output == (
        "Page (1/1), 1 items found for the applied filters.\n"
    )
    assert "`" not in rendered_output
    assert "[cyan]" not in rendered_output
