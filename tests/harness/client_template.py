#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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

"""Test-only helper for materializing a reusable ZenML client template.

The ``build_client_template_dir`` function runs the full
Client/GlobalConfiguration bring-up (alembic migrations, default
project/user/stack) into a target directory once, so the pytest
``clean_client`` fixture can copy the resulting tree instead of paying
the ~17s init cost on every test.

This lives under ``tests/harness/`` because it mutates test-only
singleton state (GlobalConfiguration, Client, CredentialsStore) and is
never imported by the ``zenml`` runtime package. CI also imports it
from ``scripts/ci/build_zenml_template.py`` to bake the template into
the Modal sandbox image at build time.
"""

import logging
import os
from pathlib import Path

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_CONFIG_PATH
from zenml.login.credentials_store import CredentialsStore


def build_client_template_dir(template_dir: Path) -> Path:
    """Materialize a clean ZenML client tree at ``template_dir``.

    Runs the full Client/GlobalConfiguration initialization once
    (alembic migrations, default project, default stack) and leaves the
    resulting ``zenml/`` subtree on disk so that later callers can copy
    it instead of paying the full initialization cost again. No-op if
    the template already exists.

    Args:
        template_dir: Directory where the template should be created.
            A ``zenml/`` subdirectory will be populated inside it.

    Returns:
        The directory containing the materialized template.
    """
    template_dir.mkdir(parents=True, exist_ok=True)
    template_zenml = template_dir / "zenml"
    if template_zenml.exists():
        return template_dir

    original_config = GlobalConfiguration.get_instance()
    original_client = Client.get_instance()
    original_credentials = CredentialsStore.get_instance()
    orig_config_path = os.getenv(ENV_ZENML_CONFIG_PATH)
    orig_cwd = os.getcwd()

    try:
        CredentialsStore.reset_instance()
        GlobalConfiguration._reset_instance()
        Client._reset_instance()

        os.chdir(template_dir)
        os.environ[ENV_ZENML_CONFIG_PATH] = str(template_zenml)
        os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"

        gc = GlobalConfiguration()
        gc.analytics_opt_in = False
        client = Client()
        # The template directory is not itself a ZenML repo root, so
        # Client()._sanitize_config() never touches the store. Force
        # zen_store init explicitly so that the SQLite DB and default
        # project/stack/user are materialized inside the template tree.
        _ = client.zen_store

        # Seed the per-component `local_stores/<UUID>` directories.
        # `LocalArtifactStore.path` creates the UUID subdir lazily on
        # first property access, but going through `client.active_stack`
        # would populate `_STACK_CACHE` and leak initialized component
        # instances into later tests that expect a fresh artifact store.
        #
        # Query the DB through the zen_store instead so the template
        # includes the local artifact-store directories without touching
        # `Stack.from_model(...)`.
        try:
            from zenml.enums import StackComponentType
            from zenml.models import ComponentFilter

            local_stores_root = Path(gc.local_stores_path)
            filter_model = ComponentFilter(
                type=StackComponentType.ARTIFACT_STORE,
            )
            components = client.zen_store.list_stack_components(
                component_filter_model=filter_model,
            )
            for component in components.items:
                (local_stores_root / str(component.id)).mkdir(
                    parents=True, exist_ok=True
                )
        except OSError as exc:
            logging.warning(
                "Failed to pre-create artifact store path in template: %s",
                exc,
                exc_info=True,
            )
    finally:
        os.chdir(orig_cwd)
        if orig_config_path is not None:
            os.environ[ENV_ZENML_CONFIG_PATH] = orig_config_path
        elif ENV_ZENML_CONFIG_PATH in os.environ:
            del os.environ[ENV_ZENML_CONFIG_PATH]
        GlobalConfiguration._reset_instance(original_config)
        Client._reset_instance(original_client)
        CredentialsStore.reset_instance(original_credentials)

    return template_dir
