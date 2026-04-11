"""Pre-build a clean ZenML config + SQLite DB for fast test setup.

Run this script once during CI image preparation. It materializes a
fully-migrated ZenML client tree at the target directory (defaults to
``/opt/zenml-template``). At test time, the
``_zenml_client_template`` pytest fixture (see ``tests/conftest.py``)
detects ``ZENML_CLIENT_TEMPLATE_DIR``, copies the contents into each
test's tmp_path, and skips the ~17s alembic+default-stack init that
``Client()`` would otherwise run from scratch on every test.

Why a standalone script: ``tests/harness/utils.py`` is the natural
home for ``build_client_template_dir`` but it imports the rest of the
test harness, which is unwanted at image-build time. This script is
intentionally a thin wrapper that only depends on ``zenml`` itself.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

DEFAULT_TEMPLATE_DIR = Path("/opt/zenml-template")


def build_template(template_dir: Path) -> None:
    """Materialize the ZenML config + DB tree under ``template_dir``."""
    template_zenml = template_dir / "zenml"
    if template_zenml.exists():
        print(
            f"[build_zenml_template] template already exists at "
            f"{template_zenml}, skipping",
            flush=True,
        )
        return

    template_dir.mkdir(parents=True, exist_ok=True)
    os.environ["ZENML_CONFIG_PATH"] = str(template_zenml)
    os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"

    from zenml.client import Client
    from zenml.config.global_config import GlobalConfiguration

    gc = GlobalConfiguration()
    gc.analytics_opt_in = False
    client = Client()
    # Force zen_store materialization. Client() alone doesn't trigger
    # it because the template directory isn't a ZenML repo root, so
    # _sanitize_config() never touches the store.
    _ = client.zen_store

    print(
        f"[build_zenml_template] template ready at {template_zenml}",
        flush=True,
    )


def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else DEFAULT_TEMPLATE_DIR
    build_template(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
