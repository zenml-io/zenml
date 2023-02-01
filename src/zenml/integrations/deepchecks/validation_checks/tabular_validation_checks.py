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
"""Definition of the Deepchecks tabular validation check types."""

import deepchecks.tabular.checks as tabular_checks

# not part of deepchecks.tabular.checks
from deepchecks.tabular.checks.data_integrity import FeatureFeatureCorrelation

from zenml.integrations.deepchecks.enums import (
    DeepchecksModuleName,
)
from zenml.integrations.deepchecks.validation_checks.base_validation_checks import (
    DeepchecksDataDriftCheck,
    DeepchecksDataValidationCheck,
    DeepchecksModelDriftCheck,
    DeepchecksModelValidationCheck,
)
from zenml.utils.source_utils import resolve_class


class DeepchecksTabularValidationCheck:
    """Base class for Deepchecks vision validation checks.

    Does not inherit from `BaseDeepchecksValidationCheck` because it is not
    allowed to inherit from multiple Enum subclasses.
    """

    @classmethod
    def get_deepchecks_module(cls) -> DeepchecksModuleName:
        """Return the Deepchecks module that contains the checks in this class.

        Returns:
            The Deepchecks module that contains the checks in this class.
        """
        return DeepchecksModuleName.TABULAR


class DeepchecksTabularDataValidationCheck(
    DeepchecksTabularValidationCheck, DeepchecksDataValidationCheck
):
    """Deepchecks data validation checks for tabular data.

    All these checks inherit from `deepchecks.tabular.SingleDatasetCheck`.

    For more information, see
    https://docs.deepchecks.com/en/stable/checks_gallery/tabular.html#data-integrity
    """

    TABULAR_COLUMNS_INFO = resolve_class(tabular_checks.ColumnsInfo)
    TABULAR_CONFLICTING_LABELS = resolve_class(
        tabular_checks.ConflictingLabels
    )
    TABULAR_DATA_DUPLICATES = resolve_class(tabular_checks.DataDuplicates)
    TABULAR_FEATURE_FEATURE_CORRELATION = resolve_class(
        FeatureFeatureCorrelation
    )
    TABULAR_FEATURE_LABEL_CORRELATION = resolve_class(
        tabular_checks.FeatureLabelCorrelation
    )
    TABULAR_IDENTIFIER_LEAKAGE = resolve_class(
        tabular_checks.IdentifierLeakage
    )
    TABULAR_IS_SINGLE_VALUE = resolve_class(tabular_checks.IsSingleValue)
    TABULAR_MIXED_DATA_TYPES = resolve_class(tabular_checks.MixedDataTypes)
    TABULAR_MIXED_NULLS = resolve_class(tabular_checks.MixedNulls)
    TABULAR_OUTLIER_SAMPLE_DETECTION = resolve_class(
        tabular_checks.OutlierSampleDetection
    )
    TABULAR_SPECIAL_CHARS = resolve_class(tabular_checks.SpecialCharacters)
    TABULAR_STRING_LENGTH_OUT_OF_BOUNDS = resolve_class(
        tabular_checks.StringLengthOutOfBounds
    )
    TABULAR_STRING_MISMATCH = resolve_class(tabular_checks.StringMismatch)


class DeepchecksTabularDataDriftCheck(
    DeepchecksTabularValidationCheck, DeepchecksDataDriftCheck
):
    """Deepchecks data drift checks for tabular data.

    All these checks inherit from `deepchecks.tabular.TrainTestCheck`.

    For more information, see
    https://docs.deepchecks.com/stable/checks_gallery/tabular.html#train-test-validation
    """

    TABULAR_CATEGORY_MISMATCH_TRAIN_TEST = resolve_class(
        tabular_checks.CategoryMismatchTrainTest
    )
    TABULAR_DATASET_SIZE_COMPARISON = resolve_class(
        tabular_checks.DatasetsSizeComparison
    )
    TABULAR_DATE_TRAIN_TEST_LEAKAGE_DUPLICATES = resolve_class(
        tabular_checks.DateTrainTestLeakageDuplicates
    )
    TABULAR_DATE_TRAIN_TEST_LEAKAGE_OVERLAP = resolve_class(
        tabular_checks.DateTrainTestLeakageOverlap
    )
    TABULAR_DOMINANT_FREQUENCY_CHANGE = resolve_class(
        tabular_checks.DominantFrequencyChange
    )
    TABULAR_FEATURE_LABEL_CORRELATION_CHANGE = resolve_class(
        tabular_checks.FeatureLabelCorrelationChange
    )
    TABULAR_INDEX_LEAKAGE = resolve_class(tabular_checks.IndexTrainTestLeakage)
    TABULAR_NEW_LABEL_TRAIN_TEST = resolve_class(
        tabular_checks.NewLabelTrainTest
    )
    TABULAR_STRING_MISMATCH_COMPARISON = resolve_class(
        tabular_checks.StringMismatchComparison
    )
    TABULAR_TRAIN_TEST_FEATURE_DRIFT = resolve_class(
        tabular_checks.TrainTestFeatureDrift
    )
    TABULAR_TRAIN_TEST_LABEL_DRIFT = resolve_class(
        tabular_checks.TrainTestLabelDrift
    )
    TABULAR_TRAIN_TEST_SAMPLES_MIX = resolve_class(
        tabular_checks.TrainTestSamplesMix
    )
    TABULAR_WHOLE_DATASET_DRIFT = resolve_class(
        tabular_checks.WholeDatasetDrift
    )


class DeepchecksTabularModelValidationCheck(
    DeepchecksTabularValidationCheck, DeepchecksModelValidationCheck
):
    """Deepchecks model validation checks for tabular data.

    All these checks inherit from `deepchecks.tabular.SingleDatasetCheck`.

    For more information, see
    https://docs.deepchecks.com/en/stable/checks_gallery/tabular.html#model-evaluation
    """

    TABULAR_CALIBRATION_SCORE = resolve_class(tabular_checks.CalibrationScore)
    TABULAR_CONFUSION_MATRIX_REPORT = resolve_class(
        tabular_checks.ConfusionMatrixReport
    )
    TABULAR_MODEL_INFERENCE_TIME = resolve_class(
        tabular_checks.ModelInferenceTime
    )
    TABULAR_REGRESSION_ERROR_DISTRIBUTION = resolve_class(
        tabular_checks.RegressionErrorDistribution
    )
    TABULAR_REGRESSION_SYSTEMATIC_ERROR = resolve_class(
        tabular_checks.RegressionSystematicError
    )
    TABULAR_ROC_REPORT = resolve_class(tabular_checks.RocReport)
    TABULAR_SEGMENT_PERFORMANCE = resolve_class(
        tabular_checks.SegmentPerformance
    )


class DeepchecksTabularModelDriftCheck(
    DeepchecksTabularValidationCheck, DeepchecksModelDriftCheck
):
    """Deepchecks model drift checks for tabular data.

    All these checks inherit from `deepchecks.tabular.TrainTestCheck`.

    For more information, see
    https://docs.deepchecks.com/en/stable/checks_gallery/tabular.html#model-evaluation
    """

    TABULAR_BOOSTING_OVERFIT = resolve_class(tabular_checks.BoostingOverfit)
    TABULAR_MODEL_ERROR_ANALYSIS = resolve_class(
        tabular_checks.ModelErrorAnalysis
    )
    TABULAR_PERFORMANCE_REPORT = resolve_class(
        tabular_checks.PerformanceReport
    )
    TABULAR_SIMPLE_MODEL_COMPARISON = resolve_class(
        tabular_checks.SimpleModelComparison
    )
    TABULAR_TRAIN_TEST_PREDICTION_DRIFT = resolve_class(
        tabular_checks.TrainTestPredictionDrift
    )
    TABULAR_UNUSED_FEATURES = resolve_class(tabular_checks.UnusedFeatures)
