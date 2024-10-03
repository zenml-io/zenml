#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Great Expectations data validator flavor."""

import os
from typing import TYPE_CHECKING, Any, Dict, Optional, Type

import yaml
from pydantic import field_validator, model_validator
from yaml.parser import ParserError

from zenml.data_validators.base_data_validator import (
    BaseDataValidatorConfig,
    BaseDataValidatorFlavor,
)
from zenml.integrations.great_expectations import (
    GREAT_EXPECTATIONS_DATA_VALIDATOR_FLAVOR,
)
from zenml.io import fileio
from zenml.utils.pydantic_utils import before_validator_handler

if TYPE_CHECKING:
    from zenml.integrations.great_expectations.data_validators import (
        GreatExpectationsDataValidator,
    )


class GreatExpectationsDataValidatorConfig(BaseDataValidatorConfig):
    """Config for the Great Expectations data validator.

    Attributes:
        project_root_dir: location of the root directory of the Great Expectations project.
        context_root_dir: location of an already initialized Great Expectations
            data context. If configured, the data validator will only be usable
            with local orchestrators.
        context_config: in-line Great Expectations data context configuration.
            If the `context_root_dir` attribute is also set, this configuration
            will be ignored.
        configure_zenml_stores: if set, ZenML will automatically configure
            stores that use the Artifact Store as a backend. If neither
            `context_root_dir` nor `context_config` are set, this is the default
            behavior.
        configure_local_docs: configure a local data docs site where Great
            Expectations docs are generated and can be visualized locally.
    """

    project_root_dir: Optional[str] = None
    context_root_dir: Optional[str] = None
    context_config: Optional[Dict[str, Any]] = None
    configure_zenml_stores: bool = False
    configure_local_docs: bool = True

    @field_validator("context_root_dir")
    @classmethod
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

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def validate_context_config(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert the context configuration if given in JSON/YAML format.

        Args:
            data: The configuration values.

        Returns:
            The validated configuration values.

        Raises:
            ValueError: If the context configuration is not a valid
                JSON/YAML object.
        """
        if isinstance(data.get("context_config"), str):
            try:
                data["context_config"] = yaml.safe_load(data["context_config"])
            except ParserError as e:
                raise ValueError(
                    f"Malformed `context_config` value. Only JSON and YAML "
                    f"formats are supported: {str(e)}"
                )

        return data

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        # If an existing local GE data context is used, it is
        # interpreted as a local path that needs to be accessible in
        # all runtime environments.
        return self.context_root_dir is not None


class GreatExpectationsDataValidatorFlavor(BaseDataValidatorFlavor):
    """Great Expectations data validator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return GREAT_EXPECTATIONS_DATA_VALIDATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/data_validator/greatexpectations.jpeg"

    @property
    def config_class(self) -> Type[GreatExpectationsDataValidatorConfig]:
        """Returns `GreatExpectationsDataValidatorConfig` config class.

        Returns:
                The config class.
        """
        return GreatExpectationsDataValidatorConfig

    @property
    def implementation_class(self) -> Type["GreatExpectationsDataValidator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.great_expectations.data_validators import (
            GreatExpectationsDataValidator,
        )

        return GreatExpectationsDataValidator
