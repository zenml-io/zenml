#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""ZenML declarative representation of Evidently Metrics."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

from evidently import metric_preset, metrics  # type: ignore[import-untyped]
from evidently.metric_preset.metric_preset import (  # type: ignore[import-untyped]
    MetricPreset,
)
from evidently.metrics.base_metric import (  # type: ignore[import-untyped]
    Metric,
    generate_column_metrics,
)
from evidently.utils.generators import (  # type: ignore[import-untyped]
    BaseGenerator,
)
from pydantic import BaseModel, ConfigDict, Field

from zenml.logger import get_logger
from zenml.utils import source_utils

logger = get_logger(__name__)


class EvidentlyMetricConfig(BaseModel):
    """Declarative Evidently Metric configuration.

    This is a declarative representation of the configuration that goes into an
    Evidently Metric, MetricPreset or Metric generator instance. We need this to
    be able to store the configuration as part of a ZenML step parameter and
    later instantiate the Evidently Metric from it.

    This representation covers all 3 possible ways of configuring an Evidently
    Metric or Metric-like object that can later be used in an Evidently Report:

    1. A Metric (derived from the Metric class).
    2. A MetricPreset (derived from the MetricPreset class).
    3. A column Metric generator (derived from the BaseGenerator class).

    Ideally, it should be possible to just pass a Metric or Metric-like
    object to this class and have it automatically derive the configuration used
    to instantiate it. Unfortunately, this is not possible because the Evidently
    Metric classes are not designed in a way that allows us to extract the
    constructor parameters from them in a generic way.

    Attributes:
        class_path: The full class path of the Evidently Metric class.
        parameters: The parameters of the Evidently Metric.
        is_generator: Whether this is an Evidently column Metric generator.
        columns: The columns that the Evidently column Metric generator is
            applied to. Only used if `generator` is True.
        skip_id_column: Whether to skip the ID column when applying the
            Evidently Metric generator. Only used if `generator` is True.
    """

    class_path: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    is_generator: bool = False
    columns: Optional[Union[str, List[str]]] = Field(
        default=None, union_mode="left_to_right"
    )
    skip_id_column: bool = False

    @staticmethod
    def get_metric_class(metric_name: str) -> Union[Metric, MetricPreset]:
        """Get the Evidently metric or metric preset class from a string.

        Args:
            metric_name: The metric or metric preset class or full class
                path.

        Returns:
            The Evidently metric or metric preset class.

        Raises:
            ValueError: If the name cannot be converted into a valid Evidently
                metric or metric preset class.
        """
        # First, try to interpret the metric name as a full class path.
        if "." in metric_name:
            try:
                metric_class = source_utils.load(metric_name)
            except (ImportError, AttributeError) as e:
                raise ValueError(
                    f"Could not import Evidently Metric or MetricPreset "
                    f"`{metric_name}`: {str(e)}"
                )

        else:
            # Next, try to interpret the metric as a Metric or MetricPreset
            # class name
            if hasattr(metrics, metric_name):
                metric_class = getattr(metrics, metric_name)
            elif hasattr(metric_preset, metric_name):
                metric_class = getattr(metric_preset, metric_name)
            else:
                raise ValueError(
                    f"Could not import Evidently Metric or MetricPreset "
                    f"`{metric_name}`"
                )

        if not issubclass(metric_class, (Metric, MetricPreset)):
            raise ValueError(
                f"Class `{metric_name}` is not a valid Evidently "
                f"Metric or MetricPreset."
            )

        return metric_class

    @classmethod
    def metric_generator(
        cls,
        metric: Union[Type[Metric], str],
        columns: Optional[Union[str, List[str]]] = None,
        skip_id_column: bool = False,
        **parameters: Any,
    ) -> "EvidentlyMetricConfig":
        """Create a declarative configuration for an Evidently column Metric generator.

        Call this method to get a declarative representation for the
        configuration of an Evidently column Metric generator.

        The `columns`, `skip_id_column` and `parameters` arguments will be
        passed to the Evidently `generate_column_metrics` function:

        - if `columns` is a list, it is interpreted as a list of column names.
        - if `columns` is a string, it can be one of values:
            - "all" - use all columns, including target/prediction columns
            - "num" - for numeric features
            - "cat" - for category features
            - "text" - for text features
            - "features" - for all features, not target/prediction columns.
        - a None value is the same as "all".

        Some examples
        -------------

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyMetric

        # Configure an Evidently Metric generator using a Metric class name
        # and pass additional parameters
        config = EvidentlyMetric.metric_generator(
            "ColumnQuantileMetric", columns="num", quantile=0.5
        )
        ```

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyMetric

        # Configure an Evidently Metric generator using a full Metric class
        # path
        config = EvidentlyMetric.metric_generator(
            "evidently.metrics.ColumnSummaryMetric", columns=["age", "name"]
        )
        ```

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyMetric

        # Configure an Evidently Metric generator using a Metric class
        from evidently.metrics import ColumnDriftMetric
        config = EvidentlyMetric.metric_generator(
            ColumnDriftMetric, columns="all", skip_id_column=True
        )
        ```

        Args:
            metric: The Evidently Metric class, class name or class path to use
                for the generator.
            columns: The columns to apply the generator to. Takes the same
                values that the Evidently `generate_column_metrics` function
                takes.
            skip_id_column: Whether to skip the ID column when applying the
                generator.
            parameters: Additional optional parameters needed to instantiate the
                Evidently Metric. These will be passed to the Evidently
                `generate_column_metrics` function.

        Returns:
            The EvidentlyMetric declarative representation of the Evidently
            Metric generator configuration.

        Raises:
            ValueError: If `metric` does not point to a valid Evidently Metric
                or MetricPreset class.
        """
        if isinstance(metric, str):
            metric_class = cls.get_metric_class(metric)
        elif issubclass(metric, (Metric, MetricPreset)):
            metric_class = metric
        else:
            raise ValueError(f"Invalid Evidently Metric class: {metric}")

        class_path = f"{metric_class.__module__}." f"{metric_class.__name__}"

        config = cls(
            class_path=class_path,
            parameters=parameters,
            columns=columns,
            skip_id_column=skip_id_column,
            is_generator=True,
        )

        # Try to instantiate the configuration to check if the parameters are
        # valid
        config.to_evidently_metric()

        return config

    @classmethod
    def metric(
        cls,
        metric: Union[Type[Metric], Type[MetricPreset], str],
        **parameters: Any,
    ) -> "EvidentlyMetricConfig":
        """Create a declarative configuration for an Evidently Metric.

        Call this method to get a declarative representation for the
        configuration of an Evidently Metric.

        Some examples
        -------------

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyMetric

        # Configure an Evidently MetricPreset using its class name
        config = EvidentlyMetric.metric("DataDriftPreset")
        ```

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyMetric

        # Configure an Evidently MetricPreset using its full class path
        config = EvidentlyMetric.metric(
            "evidently.metric_preset.DataDriftPreset"
        )
        ```

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyMetric

        # Configure an Evidently Metric using its class and pass additional
        # parameters
        from evidently.metrics import ColumnSummaryMetric
        config = EvidentlyMetric.metric(
            ColumnSummaryMetric, column_name="age"
        )
        ```

        Args:
            metric: The Evidently Metric or MetricPreset class, class name or
                class path.
            parameters: Additional optional parameters needed to instantiate the
                Evidently Metric or MetricPreset.

        Returns:
            The EvidentlyMetric declarative representation of the Evidently
            Metric configuration.

        Raises:
            ValueError: If `metric` does not point to a valid Evidently Metric
                or MetricPreset class.
        """
        if isinstance(metric, str):
            metric_class = cls.get_metric_class(metric)
        elif issubclass(metric, (Metric, MetricPreset)):
            metric_class = metric
        else:
            raise ValueError(
                f"Invalid Evidently Metric or MetricPreset class: {metric}"
            )

        class_path = f"{metric_class.__module__}." f"{metric_class.__name__}"

        config = cls(class_path=class_path, parameters=parameters)

        # Try to instantiate the configuration to check if the parameters are
        # valid
        config.to_evidently_metric()

        return config

    @classmethod
    def default_metrics(cls) -> List["EvidentlyMetricConfig"]:
        """Default Evidently metric configurations.

        Call this to fetch a default list of Evidently metrics to use in cases
        where no metrics are explicitly configured for a data validator.
        All available Evidently MetricPreset classes are used, except for the
        `TextOverviewPreset` which requires a text column, which we don't have
        by default.

        Returns:
            A list of EvidentlyMetricConfig objects to use as default metrics.
        """
        return [
            cls.metric(metric=metric_preset_class_name)
            for metric_preset_class_name in metric_preset.__all__
            # TextOverviewPreset requires a text column, which we don't
            # have by default
            if metric_preset_class_name != "TextOverviewPreset"
        ]

    def to_evidently_metric(
        self,
    ) -> Union[Metric, MetricPreset, BaseGenerator]:
        """Create an Evidently Metric, MetricPreset or metric generator object.

        Call this method to create an Evidently Metric, MetricPreset or metric
        generator instance from its declarative representation.

        Returns:
            The Evidently Metric, MetricPreset or metric generator object.

        Raises:
            ValueError: If the Evidently Metric, MetricPreset or column metric
                generator could not be instantiated.
        """
        metric_class = self.get_metric_class(self.class_path)

        if self.is_generator:
            try:
                return generate_column_metrics(
                    metric_class=metric_class,
                    columns=self.columns,
                    skip_id_column=self.skip_id_column,
                    parameters=self.parameters,
                )
            except Exception as e:
                raise ValueError(
                    f"Could not instantiate Evidently column Metric generator "
                    f"`{self.class_path}`: {str(e)}"
                )

        try:
            return metric_class(**self.parameters)
        except Exception as e:
            raise ValueError(
                f"Could not instantiate Evidently Metric or MetricPreset "
                f"`{self.class_path}`: {str(e)}"
            )

    model_config = ConfigDict(extra="forbid")
