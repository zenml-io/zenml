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
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Type, cast

import pandas as pd
import great_expectations as ge
from great_expectations.checkpoint.checkpoint import (  # type: ignore[import-untyped]
    CheckpointResult,
)
from great_expectations.core import (  # type: ignore[import-untyped]
    ExpectationSuite,
)
from great_expectations.data_context.data_context import (
    project_manager
)
from great_expectations.data_context.data_context.abstract_data_context import (
    AbstractDataContext,
)
from great_expectations.data_context.data_context.context_factory import (
    get_context,
)
from great_expectations.data_context.data_context.ephemeral_data_context import (
    EphemeralDataContext,
)
from great_expectations.data_context.types.base import (
    DataContextConfig,
)
from great_expectations.data_context.types.resource_identifiers import (
    ExpectationSuiteIdentifier,
)

from zenml import get_step_context
from zenml.client import Client
from zenml.data_validators import BaseDataValidator, BaseDataValidatorFlavor
from zenml.integrations.great_expectations.data_validators.expectations import GreatExpectationExpectationConfig
from zenml.integrations.great_expectations.flavors.great_expectations_data_validator_flavor import (
    GreatExpectationsDataValidatorConfig,
    GreatExpectationsDataValidatorFlavor,
)
from zenml.integrations.great_expectations.ge_store_backend import (
    ZenMLArtifactStoreBackend,
)
from zenml.integrations.great_expectations.utils import create_batch_definition
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils
from zenml.utils.string_utils import random_str

logger = get_logger(__name__)


class GreatExpectationsDataValidator(BaseDataValidator):
    """Great Expectations data validator stack component."""

    NAME: ClassVar[str] = "Great Expectations"
    FLAVOR: ClassVar[Type[BaseDataValidatorFlavor]] = (
        GreatExpectationsDataValidatorFlavor
    )

    _context: Optional[AbstractDataContext] = None
    _context_config: Optional[DataContextConfig] = None

    @property
    def config(self) -> GreatExpectationsDataValidatorConfig:
        """Returns the `GreatExpectationsDataValidatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(GreatExpectationsDataValidatorConfig, self._config)

    @classmethod
    def get_data_context(cls) -> AbstractDataContext:
        """Get the Great Expectations data context managed by ZenML.

        Call this method to retrieve the data context managed by ZenML
        through the active Great Expectations data validator stack component.

        Returns:
            A Great Expectations data context managed by ZenML as configured
            through the active data validator stack component.
        """
        data_validator = cast(
            "GreatExpectationsDataValidator", cls.get_active_data_validator()
        )
        return data_validator.data_context

    @property
    def context_config(self) -> Optional[DataContextConfig]:
        """Get the Great Expectations data context configuration.

        Raises:
            ValueError: In case there is an invalid context_config value

        Returns:
            A dictionary with the GE data context configuration.
        """
        # If the context config is already loaded, return it
        if self._context_config is not None:
            return self._context_config

        # Otherwise, use the configuration from the stack component config, if
        # set
        context_config_dict = self.config.context_config
        if context_config_dict is None:
            return None

        # Validate that the context config is a valid GE config
        try:
            self._context_config = DataContextConfig(**context_config_dict)
        except Exception as e:
            raise ValueError(f"Invalid `context_config` value: {str(e)}")

        return self._context_config

    @property
    def local_path(self) -> Optional[str]:
        """Return a local path where this component stores information.

        If an existing local GE data context is used, it is
        interpreted as a local path that needs to be accessible in
        all runtime environments.

        Returns:
            The local path where this component stores information.
        """
        return self.config.context_root_dir

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
                "prefix": f"{str(self.id)}/{prefix}",
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
                "prefix": f"{str(self.id)}/{prefix}",
            }

        return {
            "class_name": "SiteBuilder",
            "store_backend": store_backend,
            "site_index_builder": {
                "class_name": "DefaultSiteIndexBuilder",
            },
        }

    @property
    def data_context(self) -> AbstractDataContext:
        """Returns the Great Expectations data context configured for this component.

        Returns:
            The Great Expectations data context configured for this component.
        """
        if not self._context:
            expectations_store_name = "zenml_expectations_store"
            validation_results_store_name = "zenml_validation_results_store"
            checkpoint_store_name = "zenml_checkpoint_store"
            validation_definition_store_name = "validation_definition_store"

            # Define default configuration options that plug the GX stores
            # in the active ZenML artifact store
            zenml_context_config: Dict[str, Any] = dict(
                stores={
                    expectations_store_name: self.get_store_config(
                        "ExpectationsStore", "expectations"
                    ),
                    validation_results_store_name: self.get_store_config(
                        "ValidationResultsStore", "validation_results"
                    ),
                    checkpoint_store_name: self.get_store_config(
                        "CheckpointStore", "checkpoints"
                    ),
                    validation_definition_store_name: self.get_store_config(
                        "ValidationDefinitionStore", "validation_definitions"
                    )
                },
                expectations_store_name=expectations_store_name,
                validation_results_store_name=validation_results_store_name,
                checkpoint_store_name=checkpoint_store_name,
                data_docs_sites={
                    "zenml_artifact_store": self.get_data_docs_config(
                        "data_docs"
                    )
                },
            )

            configure_zenml_stores = self.config.configure_zenml_stores
            if self.config.context_root_dir:
                # initialize the local data context, if a local path was
                # configured
                self._context = get_context(
                    context_root_dir=self.config.context_root_dir
                )

            else:
                # create an ephemeral in-memory data context that is not
                # backed by a local YAML file (see https://docs.greatexpectations.io/docs/core/set_up_a_gx_environment/create_a_data_context?context_type=ephemeral).
                if self.context_config:
                    # Use the data context configuration provided in the stack
                    # component configuration
                    context_config = self.context_config
                else:
                    # Initialize the data context with the default ZenML
                    # configuration options effectively plugging the GX stores
                    # into the ZenML artifact store
                    context_config = DataContextConfig(**zenml_context_config)
                    # skip adding the stores after initialization, as they are
                    # already baked in the initial configuration
                    configure_zenml_stores = False

                self._context = get_context(mode="ephemeral", project_config=context_config)

            if configure_zenml_stores:
                self._context.config.expectations_store_name = (
                    expectations_store_name
                )
                self._context.config.validation_results_store_name = (
                    validation_results_store_name
                )
                self._context.config.checkpoint_store_name = (
                    checkpoint_store_name
                )
                for store_name, store_config in zenml_context_config[
                    "stores"
                ].items():
                    self._context.add_store(
                        store_name=store_name,
                        store_config=store_config,
                    )
                if self._context.config.data_docs_sites is not None:
                    for site_name, site_config in zenml_context_config[
                        "data_docs_sites"
                    ].items():
                        self._context.config.data_docs_sites[site_name] = (
                            site_config
                        )

            if (
                self.config.configure_local_docs
                and self._context.config.data_docs_sites is not None
            ):
                client = Client()
                artifact_store = client.active_stack.artifact_store
                if artifact_store.flavor != "local":
                    self._context.config.data_docs_sites["zenml_local"] = (
                        self.get_data_docs_config("data_docs", local=True)
                    )

        project_manager.set_project(self._context)
        return self._context

    @property
    def root_directory(self) -> str:
        """Returns path to the root directory for all local files concerning this data validator.

        Returns:
            Path to the root directory.
        """
        path = os.path.join(
            io_utils.get_global_config_directory(),
            self.flavor,
            str(self.id),
        )

        if not os.path.exists(path):
            fileio.makedirs(path)

        return path

    def data_validation(
        self,
        dataset: pd.DataFrame,
        comparison_dataset: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        expectations_list: Optional[Sequence[GreatExpectationExpectationConfig]] = None,
        expectation_parameters: Optional[Dict[str, Any]] = None,
        expectation_suite_name: Optional[str] = None,
        data_asset_name: Optional[str] = None,
        action_list: Optional[List[ge.checkpoint.actions.ValidationAction]] = None,
        result_format: str = "SUMMARY",
        **kwargs: Any,
    ) -> CheckpointResult:
        """Great Expectations data validation.

        This Great Expectations specific data validation method
        implementation validates an input dataset against an Expectation Suite
        (the GE definition of a profile) [as covered in the official GE
        documentation](https://docs.greatexpectations.io/docs/guides/validation/how_to_validate_data_by_running_a_checkpoint).

        Args:
            dataset: The dataset to validate.
            comparison_dataset: Optional dataset used to run data
                comparison (i.e. data drift) checks. Not supported by the
                Great Expectation data validator.
            check_list: Optional list identifying the data validation checks to
                be performed. Not supported by the Great Expectations data
                validator.
            expectations_list: A list of Great Expectations expectations to
                use to validate the dataset. Either this or expectation_suite_name
                must be provided, but not both.
            expectation_parameters: Optional parameters to pass to the
                expectations if you have defined any parameters in the
                expectations.
            expectation_suite_name: The name of the expectation suite to use to
                validate the dataset. Either this or expectations_list must be
                provided, but not both.
            data_asset_name: The name of the data asset to use to identify the
                dataset in the Great Expectations docs.
            action_list: A list of additional Great Expectations actions to run after
                the validation check.
            result_format: The format in which to return the results of the validation definitions. Default is "SUMMARY".
                Other options are: "BOOLEAN_ONLY", "BASIC", "COMPLETE". Details in the docs:
                https://docs.greatexpectations.io/docs/core/trigger_actions_based_on_results/choose_a_result_format/#define-a-result-format-configuration
            kwargs: Additional keyword arguments.

        Returns:
            The Great Expectations validation (checkpoint) result.

        Raises:
            ValueError: If both expectation_suite_name and expectations_list are provided,
                or if neither are provided.
        """
        if comparison_dataset is not None:
            logger.warning(
                "A comparison dataset is not required by Great Expectations "
                "to do data validation. Silently ignoring the supplied dataset "
            )

        if expectation_suite_name and expectations_list:
            raise ValueError("Only one of `expectation_suite_name` and `expectations_list` can be provided.")
        
        if not expectation_suite_name and not expectations_list:
            raise ValueError("Either `expectation_suite_name` or `expectations_list` must be provided.")
        
        try:
            step_context = get_step_context()
            run_name = step_context.pipeline_run.name
            step_name = step_context.step_run.name
        except RuntimeError:
            # if not running inside a pipeline step, use random values
            run_name = f"pipeline_{random_str(5)}"
            step_name = f"step_{random_str(5)}"

        context = self.data_context

        # get all expectations from the list
        if expectations_list:
            # construct an expectation suite name from the pipeline and step names
            suite_name = f"{run_name}_{step_name}"
            expectation_suite = ExpectationSuite(
                name=suite_name,
                expectations=[exp.get_expectation() for exp in expectations_list]
            )
            context.suites.add(expectation_suite)
        
        else:  # when the expectation_suite_name is provided
            expectation_suite = context.suites.get(name=expectation_suite_name)

        batch_definition, batch_parameters, data_source = create_batch_definition(context, dataset, data_asset_name)                

        validation_definition = {
            "name": f"{run_name}_{step_name}",
            "data": {
                "datasource": {
                    "name": data_source.name,
                    "id": data_source.id
                },
                "asset": {
                    "name": data_source.assets[0].name,
                    "id": data_source.assets[0].id
                },
                "batch_definition": {
                    "name": batch_definition.name,
                    "id": batch_definition.id
                }
            },
            "suite": {
                "name": expectation_suite.name,
                "id": expectation_suite.id
            },
        }

        validation_definition_obj = ge.ValidationDefinition(
            data=batch_definition, suite=expectation_suite,
            name=f"{run_name}_{step_name}"
        )
        # create a validation definition
        _ = context.validation_definitions.add(validation_definition_obj)

        # add an action to update all data docs sites
        # not specifying site_names, so this will update all data docs sites
        action_update_data_docs = {
            "name": "update_data_docs",
            "type": "update_data_docs"
        }

        # create a checkpoint
        checkpoint_name = f"{run_name}_{step_name}"
        checkpoint = ge.Checkpoint(
            name=checkpoint_name,
            validation_definitions=[validation_definition],
            actions=action_list or [action_update_data_docs],
            result_format={"result_format": result_format},
        )

        checkpoint = context.checkpoints.add(checkpoint)
        
        # run a checkpoint
        try:
            results = checkpoint.run(
                batch_parameters=batch_parameters,
                expectation_parameters=expectation_parameters
            )
        except Exception as e:
            raise e

        return results
