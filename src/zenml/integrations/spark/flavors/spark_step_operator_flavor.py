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
"""Spark step operator flavor."""

import json
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

from pydantic import validator

from zenml.config.base_settings import BaseSettings
from zenml.step_operators.base_step_operator import (
    BaseStepOperatorConfig,
    BaseStepOperatorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.spark.step_operators.spark_step_operator import (
        SparkStepOperator,
    )


class SparkStepOperatorSettings(BaseSettings):
    """Spark step operator settings.

    Attributes:
        deploy_mode: can either be 'cluster' (default) or 'client' and it
            decides where the driver node of the application will run.
        submit_kwargs: is the JSON string of a dict, which will be used
            to define additional params if required (Spark has quite a
            lot of different parameters, so including them, all in the step
            operator was not implemented).
    """

    deploy_mode: str = "cluster"
    submit_kwargs: Optional[Dict[str, Any]] = None

    @validator("submit_kwargs", pre=True)
    def _convert_json_string(
        cls, value: Union[None, str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Converts potential JSON strings passed via the CLI to dictionaries.

        Args:
            value: The value to convert.

        Returns:
            The converted value.

        Raises:
            TypeError: If the value is not a `str`, `Dict` or `None`.
            ValueError: If the value is an invalid json string or a json string
                that does not decode into a dictionary.
        """
        if isinstance(value, str):
            try:
                dict_ = json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid json string '{value}'") from e

            if not isinstance(dict_, Dict):
                raise ValueError(
                    f"Json string '{value}' did not decode into a dictionary."
                )

            return dict_
        elif isinstance(value, Dict) or value is None:
            return value
        else:
            raise TypeError(f"{value} is not a json string or a dictionary.")


class SparkStepOperatorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseStepOperatorConfig, SparkStepOperatorSettings
):
    """Spark step operator config.

    Attributes:
        master: is the master URL for the cluster. You might see different
            schemes for different cluster managers which are supported by Spark
            like Mesos, YARN, or Kubernetes. Within the context of this PR,
            the implementation supports Kubernetes as a cluster manager.
    """

    master: str


class SparkStepOperatorFlavor(BaseStepOperatorFlavor):
    """Spark step operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return "spark"

    @property
    def config_class(self) -> Type[SparkStepOperatorConfig]:
        """Returns `SparkStepOperatorConfig` config class.

        Returns:
                The config class.
        """
        return SparkStepOperatorConfig

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
    def implementation_class(self) -> Type["SparkStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.spark.step_operators.spark_step_operator import (
            SparkStepOperator,
        )

        return SparkStepOperator
