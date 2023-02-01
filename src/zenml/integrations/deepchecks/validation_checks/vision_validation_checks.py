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
"""Definition of the Deepchecks vision validation check types."""

import deepchecks.vision.checks as vision_checks

from zenml.integrations.deepchecks.enums import DeepchecksModuleName
from zenml.integrations.deepchecks.validation_checks.base_validation_checks import (
    DeepchecksDataDriftCheck,
    DeepchecksDataValidationCheck,
    DeepchecksModelDriftCheck,
    DeepchecksModelValidationCheck,
)
from zenml.utils.source_utils import resolve_class


class DeepchecksVisionValidationCheck:
    """Base class for Deepchecks Vision validation checks.

    Does not inherit from `BaseDeepchecksValidationCheck` because it is not
    allowed to inherit from multiple Enum subclasses.
    """

    @classmethod
    def get_deepchecks_module(cls) -> DeepchecksModuleName:
        """Return the Deepchecks module that contains the checks in this class.

        Returns:
            The Deepchecks module that contains the checks in this class.
        """
        return DeepchecksModuleName.VISION


class DeepchecksVisionDataValidationCheck(
    DeepchecksVisionValidationCheck, DeepchecksDataValidationCheck
):
    """Deepchecks data validation checks for vision data.

    All these checks inherit from `deepchecks.vision.SingleDatasetCheck`.

    For more information, see
    https://docs.deepchecks.com/en/stable/checks_gallery/vision.html#data-integrity
    """

    VISION_IMAGE_PROPERTY_OUTLIERS = resolve_class(
        vision_checks.ImagePropertyOutliers
    )
    VISION_LABEL_PROPERTY_OUTLIERS = resolve_class(
        vision_checks.LabelPropertyOutliers
    )


class DeepchecksVisionDataDriftCheck(
    DeepchecksVisionValidationCheck, DeepchecksDataDriftCheck
):
    """Deepchecks data drift checks for vision data.

    All these checks inherit from `deepchecks.vision.TrainTestCheck`.

    For more information, see
    https://docs.deepchecks.com/stable/checks_gallery/vision.html#train-test-validation)
    """

    VISION_FEATURE_LABEL_CORRELATION_CHANGE = resolve_class(
        vision_checks.FeatureLabelCorrelationChange
    )
    VISION_HEATMAP_COMPARISON = resolve_class(vision_checks.HeatmapComparison)
    VISION_IMAGE_DATASET_DRIFT = resolve_class(vision_checks.ImageDatasetDrift)
    VISION_IMAGE_PROPERTY_DRIFT = resolve_class(
        vision_checks.ImagePropertyDrift
    )
    VISION_NEW_LABELS = resolve_class(vision_checks.NewLabels)
    VISION_SIMILAR_IMAGE_LEAKAGE = resolve_class(
        vision_checks.SimilarImageLeakage
    )
    VISION_TRAIN_TEST_LABEL_DRIFT = resolve_class(
        vision_checks.TrainTestLabelDrift
    )


class DeepchecksVisionModelValidationCheck(
    DeepchecksVisionValidationCheck, DeepchecksModelValidationCheck
):
    """Deepchecks model validation checks for vision data.

    All these checks inherit from `deepchecks.vision.SingleDatasetCheck`.

    For more information, see
    https://docs.deepchecks.com/stable/checks_gallery/vision.html#model-evaluation
    """

    VISION_CONFUSION_MATRIX_REPORT = resolve_class(
        vision_checks.ConfusionMatrixReport
    )
    VISION_IMAGE_SEGMENT_PERFORMANCE = resolve_class(
        vision_checks.ImageSegmentPerformance
    )
    VISION_MEAN_AVERAGE_PRECISION_REPORT = resolve_class(
        vision_checks.MeanAveragePrecisionReport
    )
    VISION_MEAN_AVERAGE_RECALL_REPORT = resolve_class(
        vision_checks.MeanAverageRecallReport
    )
    VISION_ROBUSTNESS_REPORT = resolve_class(vision_checks.RobustnessReport)
    VISION_SINGLE_DATASET_SCALAR_PERFORMANCE = resolve_class(
        vision_checks.SingleDatasetScalarPerformance
    )


class DeepchecksVisionModelDriftCheck(
    DeepchecksVisionValidationCheck, DeepchecksModelDriftCheck
):
    """Deepchecks model validation checks for vision data.

    All these checks inherit from `deepchecks.vision.TrainTestCheck`.

    For more information, see
    https://docs.deepchecks.com/stable/checks_gallery/vision.html#model-evaluation
    """

    VISION_CLASS_PERFORMANCE = resolve_class(vision_checks.ClassPerformance)
    VISION_MODEL_ERROR_ANALYSIS = resolve_class(
        vision_checks.ModelErrorAnalysis
    )
    VISION_SIMPLE_MODEL_COMPARISON = resolve_class(
        vision_checks.SimpleModelComparison
    )
    VISION_TRAIN_TEST_PREDICTION_DRIFT = resolve_class(
        vision_checks.TrainTestPredictionDrift
    )
