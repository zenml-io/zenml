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
"""Definition of the Deepchecks validation check types."""

import re
from typing import Type

import deepchecks.tabular.checks as tabular_checks
import deepchecks.vision.checks as vision_checks
from deepchecks.core.checks import BaseCheck

# not part of deepchecks.tabular.checks
from deepchecks.tabular.checks.data_integrity import FeatureFeatureCorrelation

from zenml.logger import get_logger
from zenml.utils import source_utils_v2
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)


class DeepchecksValidationCheck(StrEnum):
    """Base class for all Deepchecks categories of validation checks.

    This base class defines some conventions used for all enum values used to
    identify the various validation checks that can be performed with
    Deepchecks:

      * enum values represent fully formed class paths pointing to Deepchecks
      BaseCheck subclasses
      * all tabular data checks are located under the
      `deepchecks.tabular.checks` module sub-tree
      * all computer vision data checks are located under the
      `deepchecks.vision.checks` module sub-tree
    """

    @classmethod
    def validate_check_name(cls, check_name: str) -> None:
        """Validate a Deepchecks check identifier.

        Args:
            check_name: Identifies a builtin Deepchecks check. The identifier
                must be formatted as `deepchecks.{tabular|vision}.checks.<...>.<class-name>`.

        Raises:
            ValueError: If the check identifier does not follow the convention
                used by ZenML to identify Deepchecks builtin checks.
        """
        if not re.match(
            r"^deepchecks\.(tabular|vision)\.checks\.",
            check_name,
        ):
            raise ValueError(
                f"The supplied Deepcheck check identifier does not follow the "
                f"convention used by ZenML: `{check_name}`. The identifier "
                f"must be formatted as `deepchecks.<tabular|vision>.checks...` "
                f"and must be resolvable to a valid Deepchecks BaseCheck "
                f"subclass."
            )

    @classmethod
    def is_tabular_check(cls, check_name: str) -> bool:
        """Check if a validation check is applicable to tabular data.

        Args:
            check_name: Identifies a builtin Deepchecks check.

        Returns:
            True if the check is applicable to tabular data, otherwise False.
        """
        cls.validate_check_name(check_name)
        return check_name.startswith("deepchecks.tabular.")

    @classmethod
    def is_vision_check(cls, check_name: str) -> bool:
        """Check if a validation check is applicable to computer vision data.

        Args:
            check_name: Identifies a builtin Deepchecks check.

        Returns:
            True if the check is applicable to compute vision data, otherwise
            False.
        """
        cls.validate_check_name(check_name)
        return check_name.startswith("deepchecks.vision.")

    @classmethod
    def get_check_class(cls, check_name: str) -> Type[BaseCheck]:
        """Get the Deepchecks check class associated with an enum value or a custom check name.

        Args:
            check_name: Identifies a builtin Deepchecks check. The identifier
                must be formatted as `deepchecks.{tabular|vision}.checks.<class-name>`
                and must be resolvable to a valid Deepchecks BaseCheck class.

        Returns:
            The Deepchecks check class associated with this enum value.

        Raises:
            ValueError: If the check name could not be converted to a valid
                Deepchecks check class. This can happen for example if the enum
                values fall out of sync with the Deepchecks code base or if a
                custom check name is supplied that cannot be resolved to a valid
                Deepchecks BaseCheck class.
        """
        cls.validate_check_name(check_name)

        try:
            check_class: Type[
                BaseCheck
            ] = source_utils_v2.load_and_validate_class(
                check_name, expected_class=BaseCheck
            )
        except AttributeError:
            raise ValueError(
                f"Could not map the `{check_name}` check identifier to a valid "
                f"Deepchecks check class."
            )

        if check_name not in cls.values():
            logger.warning(
                f"You are using a custom Deepchecks check identifier that is "
                f"not listed in the `{str(cls)}` enum type. This could lead "
                f"to unexpected behavior."
            )

        return check_class

    @property
    def check_class(self) -> Type[BaseCheck]:
        """Convert the enum value to a valid Deepchecks check class.

        Returns:
            The Deepchecks check class associated with the enum value.
        """
        return self.get_check_class(self.value)


class DeepchecksDataIntegrityCheck(DeepchecksValidationCheck):
    """Categories of Deepchecks data integrity checks.

    This list reflects the set of data integrity checks provided by Deepchecks:

      * [for tabular data](https://docs.deepchecks.com/en/stable/checks_gallery/tabular.html#data-integrity)
      * [for computer vision](https://docs.deepchecks.com/en/stable/checks_gallery/vision.html#data-integrity)

    All these checks inherit from `deepchecks.tabular.SingleDatasetCheck` or
    `deepchecks.vision.SingleDatasetCheck` and require a single dataset as input.
    """

    TABULAR_COLUMNS_INFO = source_utils_v2.resolve(tabular_checks.ColumnsInfo)
    TABULAR_CONFLICTING_LABELS = source_utils_v2.resolve(
        tabular_checks.ConflictingLabels
    )

    TABULAR_DATA_DUPLICATES = source_utils_v2.resolve(
        tabular_checks.DataDuplicates
    )
    TABULAR_FEATURE_FEATURE_CORRELATION = source_utils_v2.resolve(
        FeatureFeatureCorrelation
    )
    TABULAR_FEATURE_LABEL_CORRELATION = source_utils_v2.resolve(
        tabular_checks.FeatureLabelCorrelation
    )
    TABULAR_IDENTIFIER_LEAKAGE = source_utils_v2.resolve(
        tabular_checks.IdentifierLeakage
    )
    TABULAR_IS_SINGLE_VALUE = source_utils_v2.resolve(
        tabular_checks.IsSingleValue
    )
    TABULAR_MIXED_DATA_TYPES = source_utils_v2.resolve(
        tabular_checks.MixedDataTypes
    )
    TABULAR_MIXED_NULLS = source_utils_v2.resolve(tabular_checks.MixedNulls)
    TABULAR_OUTLIER_SAMPLE_DETECTION = source_utils_v2.resolve(
        tabular_checks.OutlierSampleDetection
    )
    TABULAR_SPECIAL_CHARS = source_utils_v2.resolve(
        tabular_checks.SpecialCharacters
    )
    TABULAR_STRING_LENGTH_OUT_OF_BOUNDS = source_utils_v2.resolve(
        tabular_checks.StringLengthOutOfBounds
    )
    TABULAR_STRING_MISMATCH = source_utils_v2.resolve(
        tabular_checks.StringMismatch
    )

    VISION_IMAGE_PROPERTY_OUTLIERS = source_utils_v2.resolve(
        vision_checks.ImagePropertyOutliers
    )
    VISION_LABEL_PROPERTY_OUTLIERS = source_utils_v2.resolve(
        vision_checks.LabelPropertyOutliers
    )


class DeepchecksDataDriftCheck(DeepchecksValidationCheck):
    """Categories of Deepchecks data drift checks.

    This list reflects the set of train-test validation checks provided by
    Deepchecks:

      * [for tabular data](https://docs.deepchecks.com/stable/checks_gallery/tabular.html#train-test-validation)
      * [for computer vision](https://docs.deepchecks.com/stable/checks_gallery/vision.html#train-test-validation)

    All these checks inherit from `deepchecks.tabular.TrainTestCheck` or
    `deepchecks.vision.TrainTestCheck` and require two datasets as input.
    """

    TABULAR_CATEGORY_MISMATCH_TRAIN_TEST = source_utils_v2.resolve(
        tabular_checks.CategoryMismatchTrainTest
    )
    TABULAR_DATASET_SIZE_COMPARISON = source_utils_v2.resolve(
        tabular_checks.DatasetsSizeComparison
    )
    TABULAR_DATE_TRAIN_TEST_LEAKAGE_DUPLICATES = source_utils_v2.resolve(
        tabular_checks.DateTrainTestLeakageDuplicates
    )
    TABULAR_DATE_TRAIN_TEST_LEAKAGE_OVERLAP = source_utils_v2.resolve(
        tabular_checks.DateTrainTestLeakageOverlap
    )
    TABULAR_DOMINANT_FREQUENCY_CHANGE = source_utils_v2.resolve(
        tabular_checks.DominantFrequencyChange
    )
    TABULAR_FEATURE_LABEL_CORRELATION_CHANGE = source_utils_v2.resolve(
        tabular_checks.FeatureLabelCorrelationChange
    )
    TABULAR_INDEX_LEAKAGE = source_utils_v2.resolve(
        tabular_checks.IndexTrainTestLeakage
    )
    TABULAR_NEW_LABEL_TRAIN_TEST = source_utils_v2.resolve(
        tabular_checks.NewLabelTrainTest
    )
    TABULAR_STRING_MISMATCH_COMPARISON = source_utils_v2.resolve(
        tabular_checks.StringMismatchComparison
    )
    TABULAR_TRAIN_TEST_FEATURE_DRIFT = source_utils_v2.resolve(
        tabular_checks.TrainTestFeatureDrift
    )
    TABULAR_TRAIN_TEST_LABEL_DRIFT = source_utils_v2.resolve(
        tabular_checks.TrainTestLabelDrift
    )
    TABULAR_TRAIN_TEST_SAMPLES_MIX = source_utils_v2.resolve(
        tabular_checks.TrainTestSamplesMix
    )
    TABULAR_WHOLE_DATASET_DRIFT = source_utils_v2.resolve(
        tabular_checks.WholeDatasetDrift
    )

    VISION_FEATURE_LABEL_CORRELATION_CHANGE = source_utils_v2.resolve(
        vision_checks.FeatureLabelCorrelationChange
    )
    VISION_HEATMAP_COMPARISON = source_utils_v2.resolve(
        vision_checks.HeatmapComparison
    )
    VISION_IMAGE_DATASET_DRIFT = source_utils_v2.resolve(
        vision_checks.ImageDatasetDrift
    )
    VISION_IMAGE_PROPERTY_DRIFT = source_utils_v2.resolve(
        vision_checks.ImagePropertyDrift
    )
    VISION_NEW_LABELS = source_utils_v2.resolve(vision_checks.NewLabels)
    VISION_SIMILAR_IMAGE_LEAKAGE = source_utils_v2.resolve(
        vision_checks.SimilarImageLeakage
    )
    VISION_TRAIN_TEST_LABEL_DRIFT = source_utils_v2.resolve(
        vision_checks.TrainTestLabelDrift
    )


class DeepchecksModelValidationCheck(DeepchecksValidationCheck):
    """Categories of Deepchecks model validation checks.

    This list includes a subset of the model evaluation checks provided by
    Deepchecks that require a single dataset and a mandatory model as input:

      * [for tabular data](https://docs.deepchecks.com/en/stable/checks_gallery/tabular.html#model-evaluation)
      * [for computer vision](https://docs.deepchecks.com/stable/checks_gallery/vision.html#model-evaluation)

    All these checks inherit from `deepchecks.tabular.SingleDatasetCheck` or
    `deepchecks.vision.SingleDatasetCheck and require a dataset and a mandatory
    model as input.
    """

    TABULAR_CALIBRATION_SCORE = source_utils_v2.resolve(
        tabular_checks.CalibrationScore
    )
    TABULAR_CONFUSION_MATRIX_REPORT = source_utils_v2.resolve(
        tabular_checks.ConfusionMatrixReport
    )
    TABULAR_MODEL_INFERENCE_TIME = source_utils_v2.resolve(
        tabular_checks.ModelInferenceTime
    )
    TABULAR_REGRESSION_ERROR_DISTRIBUTION = source_utils_v2.resolve(
        tabular_checks.RegressionErrorDistribution
    )
    TABULAR_REGRESSION_SYSTEMATIC_ERROR = source_utils_v2.resolve(
        tabular_checks.RegressionSystematicError
    )
    TABULAR_ROC_REPORT = source_utils_v2.resolve(tabular_checks.RocReport)
    TABULAR_SEGMENT_PERFORMANCE = source_utils_v2.resolve(
        tabular_checks.SegmentPerformance
    )

    VISION_CONFUSION_MATRIX_REPORT = source_utils_v2.resolve(
        vision_checks.ConfusionMatrixReport
    )
    VISION_IMAGE_SEGMENT_PERFORMANCE = source_utils_v2.resolve(
        vision_checks.ImageSegmentPerformance
    )
    VISION_MEAN_AVERAGE_PRECISION_REPORT = source_utils_v2.resolve(
        vision_checks.MeanAveragePrecisionReport
    )
    VISION_MEAN_AVERAGE_RECALL_REPORT = source_utils_v2.resolve(
        vision_checks.MeanAverageRecallReport
    )
    VISION_ROBUSTNESS_REPORT = source_utils_v2.resolve(
        vision_checks.RobustnessReport
    )
    VISION_SINGLE_DATASET_SCALAR_PERFORMANCE = source_utils_v2.resolve(
        vision_checks.SingleDatasetScalarPerformance
    )


class DeepchecksModelDriftCheck(DeepchecksValidationCheck):
    """Categories of Deepchecks model drift checks.

    This list includes a subset of the model evaluation checks provided by
    Deepchecks that require two datasets and a mandatory model as input:

      * [for tabular data](https://docs.deepchecks.com/en/stable/checks_gallery/tabular.html#model-evaluation)
      * [for computer vision](https://docs.deepchecks.com/stable/checks_gallery/vision.html#model-evaluation)

    All these checks inherit from `deepchecks.tabular.TrainTestCheck` or
    `deepchecks.vision.TrainTestCheck` and require two datasets and a mandatory
    model as input.
    """

    TABULAR_BOOSTING_OVERFIT = source_utils_v2.resolve(
        tabular_checks.BoostingOverfit
    )
    TABULAR_MODEL_ERROR_ANALYSIS = source_utils_v2.resolve(
        tabular_checks.ModelErrorAnalysis
    )
    TABULAR_PERFORMANCE_REPORT = source_utils_v2.resolve(
        tabular_checks.PerformanceReport
    )
    TABULAR_SIMPLE_MODEL_COMPARISON = source_utils_v2.resolve(
        tabular_checks.SimpleModelComparison
    )
    TABULAR_TRAIN_TEST_PREDICTION_DRIFT = source_utils_v2.resolve(
        tabular_checks.TrainTestPredictionDrift
    )
    TABULAR_UNUSED_FEATURES = source_utils_v2.resolve(
        tabular_checks.UnusedFeatures
    )

    VISION_CLASS_PERFORMANCE = source_utils_v2.resolve(
        vision_checks.ClassPerformance
    )
    VISION_MODEL_ERROR_ANALYSIS = source_utils_v2.resolve(
        vision_checks.ModelErrorAnalysis
    )
    VISION_SIMPLE_MODEL_COMPARISON = source_utils_v2.resolve(
        vision_checks.SimpleModelComparison
    )
    VISION_TRAIN_TEST_PREDICTION_DRIFT = source_utils_v2.resolve(
        vision_checks.TrainTestPredictionDrift
    )
