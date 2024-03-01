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
import yaml
from great_expectations.checkpoint.types.checkpoint_result import (  # type: ignore[import-untyped]
    CheckpointResult,
)
from great_expectations.core import (  # type: ignore[import-untyped]
    ExpectationSuite,
)
from great_expectations.data_context.data_context import (  # type: ignore[import-untyped]
    BaseDataContext,
    DataContext,
)
from great_expectations.data_context.types.base import (  # type: ignore[import-untyped]
    DataContextConfig,
)
from great_expectations.data_context.types.resource_identifiers import (  # type: ignore[import-untyped]
    ExpectationSuiteIdentifier,
)
from great_expectations.profile.user_configurable_profiler import (  # type: ignore[import-untyped]
    UserConfigurableProfiler,
)

from zenml import get_step_context
from zenml.client import Client
from zenml.data_validators import BaseDataValidator, BaseDataValidatorFlavor
from zenml.integrations.great_expectations.flavors.great_expectations_data_validator_flavor import (
    GreatExpectationsDataValidatorConfig,
    GreatExpectationsDataValidatorFlavor,
)
from zenml.integrations.great_expectations.ge_store_backend import (
    ZenMLArtifactStoreBackend,
)
from zenml.integrations.great_expectations.utils import create_batch_request
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils
from zenml.utils.string_utils import random_str

logger = get_logger(__name__)


class GreatExpectationsDataValidator(BaseDataValidator):
    """Great Expectations data validator stack component."""

    NAME: ClassVar[str] = "Great Expectations"
    FLAVOR: ClassVar[
        Type[BaseDataValidatorFlavor]
    ] = GreatExpectationsDataValidatorFlavor

    _context: BaseDataContext = None
    _context_config: Optional[Dict[str, Any]] = None

    @property
    def config(self) -> GreatExpectationsDataValidatorConfig:
        """Returns the `GreatExpectationsDataValidatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(GreatExpectationsDataValidatorConfig, self._config)

    @classmethod
    def get_data_context(cls) -> BaseDataContext:
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
    def context_config(self) -> Optional[Dict[str, Any]]:
        """Get the Great Expectations data context configuration.

        The first time the context config is loaded from the stack component
        config, it is converted from JSON/YAML string format to a dict.

        Raises:
            ValueError: If the context_config value is not a valid JSON/YAML or
                if the GE configuration extracted from it fails GE validation.

        Returns:
            A dictionary with the GE data context configuration.
        """
        # If the context config is already loaded, return it
        if self._context_config is not None:
            return self._context_config

        # Otherwise, load it from the stack component config
        context_config = self.config.context_config
        if context_config is None:
            return None
        if isinstance(context_config, dict):
            self._context_config = context_config
            return self._context_config

        # If the context config is a string, try to parse it as JSON/YAML
        try:
            context_config_dict = yaml.safe_load(context_config)
        except yaml.parser.ParserError as e:
            raise ValueError(
                f"Malformed `context_config` value. Only JSON and YAML "
                f"formats are supported: {str(e)}"
            )

        # Validate that the context config is a valid GE config
        try:
            context_config = DataContextConfig(**context_config_dict)
            BaseDataContext(project_config=context_config)
        except Exception as e:
            raise ValueError(f"Invalid `context_config` value: {str(e)}")

        self._context_config = cast(Dict[str, Any], context_config_dict)
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
    def data_context(self) -> BaseDataContext:
        """Returns the Great Expectations data context configured for this component.

        Returns:
            The Great Expectations data context configured for this component.
        """
        if not self._context:
            expectations_store_name = "zenml_expectations_store"
            validations_store_name = "zenml_validations_store"
            checkpoint_store_name = "zenml_checkpoint_store"
            profiler_store_name = "zenml_profiler_store"
            evaluation_parameter_store_name = "evaluation_parameter_store"

            zenml_context_config = dict(
                stores={
                    expectations_store_name: self.get_store_config(
                        "ExpectationsStore", "expectations"
                    ),
                    validations_store_name: self.get_store_config(
                        "ValidationsStore", "validations"
                    ),
                    checkpoint_store_name: self.get_store_config(
                        "CheckpointStore", "checkpoints"
                    ),
                    profiler_store_name: self.get_store_config(
                        "ProfilerStore", "profilers"
                    ),
                    evaluation_parameter_store_name: {
                        "class_name": "EvaluationParameterStore"
                    },
                },
                expectations_store_name=expectations_store_name,
                validations_store_name=validations_store_name,
                checkpoint_store_name=checkpoint_store_name,
                profiler_store_name=profiler_store_name,
                evaluation_parameter_store_name=evaluation_parameter_store_name,
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
                self._context = DataContext(self.config.context_root_dir)
            else:
                # create an in-memory data context configuration that is not
                # backed by a local YAML file (see https://docs.greatexpectations.io/docs/guides/setup/configuring_data_contexts/how_to_instantiate_a_data_context_without_a_yml_file/).
                if self.context_config:
                    context_config = DataContextConfig(**self.context_config)
                else:
                    context_config = DataContextConfig(**zenml_context_config)
                    # skip adding the stores after initialization, as they are
                    # already baked in the initial configuration
                    configure_zenml_stores = False
                self._context = BaseDataContext(project_config=context_config)

            if configure_zenml_stores:
                self._context.config.expectations_store_name = (
                    expectations_store_name
                )
                self._context.config.validations_store_name = (
                    validations_store_name
                )
                self._context.config.checkpoint_store_name = (
                    checkpoint_store_name
                )
                self._context.config.profiler_store_name = profiler_store_name
                self._context.config.evaluation_parameter_store_name = (
                    evaluation_parameter_store_name
                )
                for store_name, store_config in zenml_context_config[  # type: ignore[attr-defined]
                    "stores"
                ].items():
                    self._context.add_store(
                        store_name=store_name,
                        store_config=store_config,
                    )
                for site_name, site_config in zenml_context_config[  # type: ignore[attr-defined]
                    "data_docs_sites"
                ].items():
                    self._context.config.data_docs_sites[
                        site_name
                    ] = site_config

            if self.config.configure_local_docs:
                client = Client()
                artifact_store = client.active_stack.artifact_store
                if artifact_store.flavor != "local":
                    self._context.config.data_docs_sites[
                        "zenml_local"
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
            self.flavor,
            str(self.id),
        )

        if not os.path.exists(path):
            fileio.makedirs(path)

        return path

    def data_profiling(
        self,
        dataset: pd.DataFrame,
        comparison_dataset: Optional[Any] = None,
        profile_list: Optional[Sequence[str]] = None,
        expectation_suite_name: Optional[str] = None,
        data_asset_name: Optional[str] = None,
        profiler_kwargs: Optional[Dict[str, Any]] = None,
        overwrite_existing_suite: bool = True,
        **kwargs: Any,
    ) -> ExpectationSuite:
        """Infer a Great Expectation Expectation Suite from a given dataset.

        This Great Expectations specific data profiling method implementation
        builds an Expectation Suite automatically by running a
        UserConfigurableProfiler on an input dataset [as covered in the official
        GE documentation](https://docs.greatexpectations.io/docs/guides/expectations/how_to_create_and_edit_expectations_with_a_profiler).

        Args:
            dataset: The dataset from which the expectation suite will be
                inferred.
            comparison_dataset: Optional dataset used to generate data
                comparison (i.e. data drift) profiles. Not supported by the
                Great Expectation data validator.
            profile_list: Optional list identifying the categories of data
                profiles to be generated. Not supported by the Great Expectation
                data validator.
            expectation_suite_name: The name of the expectation suite to create
                or update. If not supplied, a unique name will be generated from
                the current pipeline and step name, if running in the context of
                a pipeline step.
            data_asset_name: The name of the data asset to use to identify the
                dataset in the Great Expectations docs.
            profiler_kwargs: A dictionary of custom keyword arguments to pass to
                the profiler.
            overwrite_existing_suite: Whether to overwrite an existing
                expectation suite, if one exists with that name.
            kwargs: Additional keyword arguments (unused).

        Returns:
            The inferred Expectation Suite.

        Raises:
            ValueError: if an `expectation_suite_name` value is not supplied and
                a name for the expectation suite cannot be generated from the
                current step name and pipeline name.
        """
        context = self.data_context

        if comparison_dataset is not None:
            logger.warning(
                "A comparison dataset is not required by Great Expectations "
                "to do data profiling. Silently ignoring the supplied dataset "
            )

        if not expectation_suite_name:
            try:
                step_context = get_step_context()
                pipeline_name = step_context.pipeline.name
                step_name = step_context.step_run.name
                expectation_suite_name = f"{pipeline_name}_{step_name}"
            except RuntimeError:
                raise ValueError(
                    "A expectation suite name is required when not running in "
                    "the context of a pipeline step."
                )

        suite_exists = False
        if context.expectations_store.has_key(  # noqa
            ExpectationSuiteIdentifier(expectation_suite_name)
        ):
            suite_exists = True
            suite = context.get_expectation_suite(expectation_suite_name)
            if not overwrite_existing_suite:
                logger.info(
                    f"Expectation Suite `{expectation_suite_name}` "
                    f"already exists and `overwrite_existing_suite` is not set "
                    f"in the step configuration. Skipping re-running the "
                    f"profiler."
                )
                return suite

        batch_request = create_batch_request(context, dataset, data_asset_name)

        try:
            if suite_exists:
                validator = context.get_validator(
                    batch_request=batch_request,
                    expectation_suite_name=expectation_suite_name,
                )
            else:
                validator = context.get_validator(
                    batch_request=batch_request,
                    create_expectation_suite_with_name=expectation_suite_name,
                )

            profiler = UserConfigurableProfiler(
                profile_dataset=validator, **profiler_kwargs
            )

            suite = profiler.build_suite()
            context.save_expectation_suite(
                expectation_suite=suite,
                expectation_suite_name=expectation_suite_name,
            )

            context.build_data_docs()
        finally:
            context.delete_datasource(batch_request.datasource_name)

        return suite

    def data_validation(
        self,
        dataset: pd.DataFrame,
        comparison_dataset: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        expectation_suite_name: Optional[str] = None,
        data_asset_name: Optional[str] = None,
        action_list: Optional[List[Dict[str, Any]]] = None,
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
            expectation_suite_name: The name of the expectation suite to use to
                validate the dataset. A value must be provided.
            data_asset_name: The name of the data asset to use to identify the
                dataset in the Great Expectations docs.
            action_list: A list of additional Great Expectations actions to run after
                the validation check.
            kwargs: Additional keyword arguments (unused).

        Returns:
            The Great Expectations validation (checkpoint) result.

        Raises:
            ValueError: if the `expectation_suite_name` argument is omitted.
        """
        if not expectation_suite_name:
            raise ValueError("Missing expectation_suite_name argument value.")

        if comparison_dataset is not None:
            logger.warning(
                "A comparison dataset is not required by Great Expectations "
                "to do data validation. Silently ignoring the supplied dataset "
            )

        try:
            step_context = get_step_context()
            run_name = step_context.pipeline_run.name
            step_name = step_context.step_run.name
        except RuntimeError:
            # if not running inside a pipeline step, use random values
            run_name = f"pipeline_{random_str(5)}"
            step_name = f"step_{random_str(5)}"

        context = self.data_context

        checkpoint_name = f"{run_name}_{step_name}"

        batch_request = create_batch_request(context, dataset, data_asset_name)

        action_list = action_list or [
            {
                "name": "store_validation_result",
                "action": {"class_name": "StoreValidationResultAction"},
            },
            {
                "name": "store_evaluation_params",
                "action": {"class_name": "StoreEvaluationParametersAction"},
            },
            {
                "name": "update_data_docs",
                "action": {"class_name": "UpdateDataDocsAction"},
            },
        ]

        checkpoint_config = {
            "name": checkpoint_name,
            "run_name_template": run_name,
            "config_version": 1,
            "class_name": "Checkpoint",
            "expectation_suite_name": expectation_suite_name,
            "action_list": action_list,
        }
        context.add_checkpoint(**checkpoint_config)

        try:
            results = context.run_checkpoint(
                checkpoint_name=checkpoint_name,
                validations=[{"batch_request": batch_request}],
            )
        finally:
            context.delete_datasource(batch_request.datasource_name)
            context.delete_checkpoint(checkpoint_name)

        return results
