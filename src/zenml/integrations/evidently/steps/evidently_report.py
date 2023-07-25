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
"""Implementation of the Evidently Report Step."""

from typing import Any, Dict, List, Optional, Sequence, Tuple, cast

import pandas as pd
from typing_extensions import Annotated

from zenml import step
from zenml.integrations.evidently.column_mapping import EvidentlyColumnMapping
from zenml.integrations.evidently.data_validators import EvidentlyDataValidator
from zenml.integrations.evidently.metrics import EvidentlyMetricConfig
from zenml.logger import get_logger
from zenml.types import HTMLString

logger = get_logger(__name__)


@step
def evidently_report_step(
    reference_dataset: pd.DataFrame,
    comparison_dataset: Optional[pd.DataFrame] = None,
    column_mapping: Optional[EvidentlyColumnMapping] = None,
    ignored_cols: Optional[List[str]] = None,
    metrics: Optional[List[EvidentlyMetricConfig]] = None,
    report_options: Optional[Sequence[Tuple[str, Dict[str, Any]]]] = None,
    download_nltk_data: bool = False,
) -> Tuple[
    Annotated[str, "report_json"], Annotated[HTMLString, "report_html"]
]:
    """Generate an Evidently report on one or two pandas datasets.

    Args:
        reference_dataset: a Pandas DataFrame
        comparison_dataset: a Pandas DataFrame of new data you wish to
            compare against the reference data
        column_mapping: properties of the DataFrame columns used
        ignored_cols: columns to ignore during the Evidently report step
        metrics: a list of Evidently metric configurations to use for the
            report.
        report_options: a list of tuples containing the name of the report
            and a dictionary of options for the report.
        download_nltk_data: whether to download the NLTK data for the report
            step. Defaults to False.

    Returns:
        A tuple containing the Evidently report in JSON and HTML
        formats.
    """
    if not metrics:
        metrics = EvidentlyMetricConfig.default_metrics()

    data_validator = cast(
        EvidentlyDataValidator,
        EvidentlyDataValidator.get_active_data_validator(),
    )

    if ignored_cols:
        exception_msg = (
            "Columns {extra_cols} configured in the `ignored_cols` "
            "parameter are not found in the {dataset} dataset. "
        )
        extra_cols = set(ignored_cols) - set(reference_dataset.columns)
        if extra_cols:
            logger.warning(
                exception_msg.format(
                    extra_cols=extra_cols, dataset="reference"
                )
            )
        reference_dataset = reference_dataset.drop(
            labels=list(set(ignored_cols) - extra_cols), axis=1
        )

        if comparison_dataset is not None:
            extra_cols = set(ignored_cols) - set(comparison_dataset.columns)
            if extra_cols:
                logger.warning(
                    exception_msg.format(
                        extra_cols=extra_cols, dataset="comparison"
                    )
                )

            comparison_dataset = comparison_dataset.drop(
                labels=list(set(ignored_cols) - extra_cols), axis=1
            )

    if column_mapping:
        evidently_column_mapping = column_mapping.to_evidently_column_mapping()
    else:
        evidently_column_mapping = None
    report = data_validator.data_profiling(
        dataset=reference_dataset,
        comparison_dataset=comparison_dataset,
        profile_list=metrics,
        column_mapping=evidently_column_mapping,
        report_options=report_options or [],
        download_nltk_data=download_nltk_data,
    )
    return report.json(), HTMLString(report.show(mode="inline").data)
