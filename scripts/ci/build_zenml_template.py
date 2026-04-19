"""Pre-build a clean ZenML config + SQLite DB for fast test setup.

Run this script once during CI image preparation. It materializes a
fully-migrated ZenML client tree at the target directory (defaults to
``/opt/zenml-template``). At test time, the
``_zenml_client_template`` pytest fixture (see ``tests/conftest.py``)
detects ``ZENML_CLIENT_TEMPLATE_DIR``, copies the contents into each
test's tmp_path, and skips the ~17s alembic+default-stack init that
``Client()`` would otherwise run from scratch on every test.

The actual template-building logic lives in
``tests.harness.client_template`` so it stays out of the shipped
``zenml`` runtime package; this script is just the CI entry point
that wires the repository root onto ``sys.path`` so the helper is
importable when invoked directly from the Docker image build.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# The sys.path insert above must precede this import; hence the E402
# and I001 silencers. The template-building logic deliberately lives
# under tests/harness/ so it stays out of the shipped zenml package.
from tests.harness.client_template import (  # noqa: E402, I001
    build_client_template_dir,
)

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
