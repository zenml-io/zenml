#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Implementation of the Great Expectations data validator."""

import os
from typing import Any, ClassVar, Dict, Optional

import great_expectations as ge  # type: ignore[import]
from great_expectations.data_context.data_context import (  # type: ignore[import]
    BaseDataContext,
    DataContext,
)
from great_expectations.data_context.types.base import (  # type: ignore[import]
    DataContextConfig,
)
from pydantic import validator

from zenml.data_validators import BaseDataValidator
from zenml.integrations.great_expectations import (
    GREAT_EXPECTATIONS_DATA_VALIDATOR_FLAVOR,
)
from zenml.integrations.great_expectations.ge_store_backend import (
    ZenMLArtifactStoreBackend,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.utils import io_utils

logger = get_logger(__name__)


class GreatExpectationsDataValidator(BaseDataValidator):
    """Great Expectations data validator stack component.

    Attributes:
        context_root_dir: location of an already initialized Great Expectations
            data context. If configured, the data validator will only be usable
            with local orchestrators.
        context_config: in-line Great Expectations data context configuration.
        configure_zenml_stores: if set, ZenML will automatically configure
            stores that use the Artifact Store as a backend. If neither
            `context_root_dir` nor `context_config` are set, this is the default
            behavior.
        configure_local_docs: configure a local data docs site where Great
            Expectations docs are generated and can be visualized locally.
        local_docs_site: the name of the local data docs site that will be used
            to visualize results on the local machine.
    """

    context_root_dir: Optional[str] = None
    context_config: Optional[Dict[str, Any]] = None
    configure_zenml_stores: bool = False
    configure_local_docs: bool = False
    local_docs_site_name: str = "local"
    _context: BaseDataContext = None

    # Class Configuration
    FLAVOR: ClassVar[str] = GREAT_EXPECTATIONS_DATA_VALIDATOR_FLAVOR

    @validator("context_root_dir")
    def _ensure_valid_context_root_dir(
        cls, context_root_dir: Optional[str] = None
    ) -> Optional[str]:
        """Ensures that the root directory is an absolute path and points to an existing path.

        Args:
            context_root_dir: The context_root_dir value to validate.

        Returns:
            The context_root_dir if it is valid.

        Raises:
            ValueError: If the context_root_dir is not valid.
        """
        if context_root_dir:
            context_root_dir = os.path.abspath(context_root_dir)
            if not fileio.exists(context_root_dir):
                raise ValueError(
                    f"The Great Expectations context_root_dir value doesn't "
                    f"point to an existing data context path: {context_root_dir}"
                )
        return context_root_dir

    @classmethod
    def get_data_context(cls) -> BaseDataContext:
        """Get the Great Expectations data context managed by ZenML.

        Call this method to retrieve the data context managed by ZenML
        through the active Great Expectations data validator stack component.
        The default context as returned by the GE `` call will be returned
        if a Great Expectations data validator component is not present in the
        active stack.

        Returns:
            A Great Expectations data context managed by ZenML as configured
            through the active data validator stack component, or the default
            data context if a Great Expectations data validator stack component
            is not present in the active stack.
        """
        repo = Repository(skip_repository_check=True)  # type: ignore[call-arg]
        data_validator = repo.active_stack.data_validator
        if data_validator and isinstance(data_validator, cls):
            return data_validator.data_context

        logger.warning(
            f"The active stack does not include a Great Expectations data "
            f"validator component. It is highly recommended to register one to "
            f"be able to configure Great Expectations and use it together "
            f"with ZenML in a consistent manner that uses the same "
            f"configuration across different stack configurations and runtime "
            f"environments. You can create a new stack with a Great "
            f"Expectations data validator component or update your existing "
            f"stack to add this component, e.g.:\n\n"
            f"  `zenml data-validator register great_expectations "
            f"--flavor={GREAT_EXPECTATIONS_DATA_VALIDATOR_FLAVOR} ...`\n"
            f"  `zenml stack register stack-name -dv great_expectations ...`\n"
            f"  or:\n"
            f"  `zenml stack update stack-name -dv great_expectations`\n\n"
            f"Defaulting to the local Great Expectations data context..."
        )
        return ge.get_context()

    @property
    def local_path(self) -> Optional[str]:
        """Return a local path where this component stores information.

        If an existing local GE data context is used, it is
        interpreted as a local path that needs to be accessible in
        all runtime environments.

        Returns:
            The local path where this component stores information.
        """
        return self.context_root_dir

    def get_store_config(self, class_name: str, prefix: str) -> Dict[str, Any]:
        """Generate a Great Expectations store configuration.

        Args:
            class_name: The store class name
            prefix: The path prefix for the ZenML store configuration

        Returns:
            A dictionary with the GE store configuration.
        """
        return {
            "class_name": class_name,
            "store_backend": {
                "module_name": ZenMLArtifactStoreBackend.__module__,
                "class_name": ZenMLArtifactStoreBackend.__name__,
                "prefix": f"{str(self.uuid)}/{prefix}",
                "suppress_store_backend_id": False,
            },
        }

    def get_data_docs_config(
        self, prefix: str, local: bool = False
    ) -> Dict[str, Any]:
        """Generate Great Expectations data docs configuration.

        Args:
            prefix: The path prefix for the ZenML data docs configuration
            local: Whether the data docs site is local or remote.

        Returns:
            A dictionary with the GE data docs site configuration.
        """
        if local:
            store_backend = {
                "class_name": "TupleFilesystemStoreBackend",
                "base_directory": f"{self.root_directory}/{prefix}",
            }
        else:
            store_backend = {
                "module_name": ZenMLArtifactStoreBackend.__module__,
                "class_name": ZenMLArtifactStoreBackend.__name__,
                "prefix": f"{str(self.uuid)}/{prefix}",
            }

        return {
            "class_name": "SiteBuilder",
            "store_backend": store_backend,
            "site_index_builder": {
                "class_name": "DefaultSiteIndexBuilder",
            },
        }

    @property
    def data_context(self) -> BaseDataContext:
        """Returns the Great Expectations data context configured for this component.

        Returns:
            The Great Expectations data context configured for this component.
        """
        if not self._context:
            if self.context_root_dir:
                # initialize the local data context, if a local path was
                # configured
                self._context = DataContext(self.context_root_dir)
            else:
                # create an in-memory data context configuration that is not
                # backed by a local YAML file (see https://docs.greatexpectations.io/docs/guides/setup/configuring_data_contexts/how_to_instantiate_a_data_context_without_a_yml_file/).
                self.configure_zenml_stores = True
                if self.context_config:
                    context_config = DataContextConfig(**self.context_config)
                else:
                    context_config = DataContextConfig()
                self._context = BaseDataContext(project_config=context_config)

            if self.configure_zenml_stores:
                store_name = "zenml_expectations_store"
                self._context.add_store(
                    store_name=store_name,
                    store_config=self.get_store_config(
                        "ExpectationsStore", "expectations"
                    ),
                )
                self._context.config.expectations_store_name = store_name

                store_name = "zenml_validations_store"
                self._context.add_store(
                    store_name=store_name,
                    store_config=self.get_store_config(
                        "ValidationsStore", "validations"
                    ),
                )
                self._context.config.validations_store_name = store_name

                store_name = "zenml_checkpoint_store"
                self._context.add_store(
                    store_name=store_name,
                    store_config=self.get_store_config(
                        "CheckpointStore", "checkpoints"
                    ),
                )
                self._context.config.checkpoint_store_name = store_name

                store_name = "zenml_profiler_store"
                self._context.add_store(
                    store_name=store_name,
                    store_config=self.get_store_config(
                        "ProfilerStore", "profilers"
                    ),
                )
                self._context.config.profiler_store_name = store_name

                self._context.config.data_docs_sites[
                    "zenml_artifact_store"
                ] = self.get_data_docs_config("data_docs")

            if self.configure_local_docs:
                self._context.config.data_docs_sites[
                    self.local_docs_site_name
                ] = self.get_data_docs_config("data_docs", local=True)

        return self._context

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for all local files concerning this data validator.

        Returns:
            Path to the root directory.
        """
        path = os.path.join(
            io_utils.get_global_config_directory(),
            "great_expectations",
            str(self.uuid),
        )

        if not os.path.exists(path):
            fileio.makedirs(path)

        return path
