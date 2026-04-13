"""Pre-build a clean ZenML config + SQLite DB for fast test setup.

Run this script once during CI image preparation. It materializes a
fully-migrated ZenML client tree at the target directory (defaults to
``/opt/zenml-template``). At test time, the
``_zenml_client_template`` pytest fixture (see ``tests/conftest.py``)
detects ``ZENML_CLIENT_TEMPLATE_DIR``, copies the contents into each
test's tmp_path, and skips the ~17s alembic+default-stack init that
``Client()`` would otherwise run from scratch on every test.

Why a standalone script: CI needs this at image-build time, so the
entrypoint stays in ``scripts/ci`` while the actual template-building
logic lives in ``zenml.utils.client_template_utils`` and is shared with
the pytest harness.
"""

from __future__ import annotations

import sys
from pathlib import Path

from zenml.utils.client_template_utils import build_client_template_dir

DEFAULT_TEMPLATE_DIR = Path("/opt/zenml-template")


def main(argv: list[str]) -> int:
    """Build the reusable ZenML client template for CI."""

    target = Path(argv[1]) if len(argv) > 1 else DEFAULT_TEMPLATE_DIR
    template_dir = build_client_template_dir(target)
    print(
        f"[build_zenml_template] template ready at {template_dir / 'zenml'}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
