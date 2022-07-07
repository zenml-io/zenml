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
"""Implementation of the Deepchecks data validator."""

import re
from typing import (
    Any,
    ClassVar,
    Dict,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)

import deepchecks.tabular.checks as tabular_checks
import deepchecks.vision.checks as vision_checks
import pandas as pd
from deepchecks.core.checks import BaseCheck
from deepchecks.core.suite import SuiteResult
from deepchecks.tabular import Dataset as TabularData
from deepchecks.tabular import Suite as TabularSuite

# not part of deepchecks.tabular.checks
from deepchecks.tabular.checks.data_integrity import FeatureFeatureCorrelation
from deepchecks.tabular.suites import full_suite as full_tabular_suite
from deepchecks.vision import Suite as VisionSuite
from deepchecks.vision import VisionData
from deepchecks.vision.suites import full_suite as full_vision_suite
from sklearn.base import ClassifierMixin
from torch.nn import Module  # type: ignore[attr-defined]
from torch.utils.data.dataloader import DataLoader

from zenml.data_validators import BaseDataValidator
from zenml.environment import Environment
from zenml.integrations.deepchecks import DEEPCHECKS_DATA_VALIDATOR_FLAVOR
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.steps import STEP_ENVIRONMENT_NAME, StepEnvironment
from zenml.utils.enum_utils import StrEnum
from zenml.utils.source_utils import import_class_by_path, resolve_class
from zenml.utils.string_utils import random_str

logger = get_logger(__name__)


class DeepchecksValidationCheck(StrEnum):
    """Base class for all Deepchecks categories of validation checks.

    This base class defines some conventions used for all enum values used to
    identify the various validation checks that can be performed with
    Deepchecks:

      * enum values represent fully formed class paths pointing to Deepchecks
      BaseCheck subclasses
      * all tabular data checks are located under the
      `deepchecks.tabular.checks` module subtree
      * all computer vision data checks are located under the
      `deepchecks.vision.checks` module subtree
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
            check_class = import_class_by_path(check_name)
        except AttributeError:
            raise ValueError(
                f"Could not map the `{check_name}` check identifier to a valid "
                f"Deepchecks check class."
            )

        if not issubclass(check_class, BaseCheck):
            raise ValueError(
                f"The `{check_name}` check identifier is mapped to an invalid "
                f"data type. Expected a {str(BaseCheck)} subclass, but instead "
                f"got: {str(check_class)}."
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

    TABULAR_COLUMNS_INFO = resolve_class(tabular_checks.ColumnsInfo)
    TABULAR_CONFLICTING_LABELS = resolve_class(tabular_checks.ConflictingLabels)
    TABULAR_DATA_DUPLICATES = resolve_class(tabular_checks.DataDuplicates)
    TABULAR_FEATURE_FEATURE_CORRELATION = resolve_class(
        FeatureFeatureCorrelation
    )
    TABULAR_FEATURE_LABEL_CORRELATION = resolve_class(
        tabular_checks.FeatureLabelCorrelation
    )
    TABULAR_IDENTIFIER_LEAKAGE = resolve_class(tabular_checks.IdentifierLeakage)
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

    VISION_IMAGE_PROPERTY_OUTLIERS = resolve_class(
        vision_checks.ImagePropertyOutliers
    )
    VISION_LABEL_PROPERTY_OUTLIERS = resolve_class(
        vision_checks.LabelPropertyOutliers
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


class DeepchecksDataDriftCheck(DeepchecksValidationCheck):
    """Categories of Deepchecks data drift checks.

    This list reflects the set of train-test validation checks provided by
    Deepchecks:

      * [for tabular data](https://docs.deepchecks.com/stable/checks_gallery/tabular.html#train-test-validation)
      * [for computer vision](https://docs.deepchecks.com/stable/checks_gallery/vision.html#train-test-validation)

    All these checks inherit from `deepchecks.tabular.TrainTestCheck` or
    `deepchecks.vision.TrainTestCheck` and only require two datasets as input.
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


class DeepchecksModelDriftCheck(DeepchecksValidationCheck):
    """Categories of Deepchecks model drift checks.

    This list includes a subset of the model evaluation checks provided by
    Deepchecks that require two dataset and a mandatory model as input:

      * [for tabular data](https://docs.deepchecks.com/en/stable/checks_gallery/tabular.html#model-evaluation)
      * [for computer vision](https://docs.deepchecks.com/stable/checks_gallery/vision.html#model-evaluation)

    All these checks inherit from `deepchecks.tabular.TrainTestCheck` or
    `deepchecks.vision.TrainTestCheck` and require two datasets and a mandatory
    model as input.
    """

    TABULAR_BOOSTING_OVERFIT = resolve_class(tabular_checks.BoostingOverfit)
    TABULAR_MODEL_ERROR_ANALYSIS = resolve_class(
        tabular_checks.ModelErrorAnalysis
    )
    TABULAR_PERFORMANCE_REPORT = resolve_class(tabular_checks.PerformanceReport)
    TABULAR_SIMPLE_MODEL_COMPARISON = resolve_class(
        tabular_checks.SimpleModelComparison
    )
    TABULAR_TRAIN_TEST_PREDICTION_DRIFT = resolve_class(
        tabular_checks.TrainTestPredictionDrift
    )
    TABULAR_UNUSED_FEATURES = resolve_class(tabular_checks.UnusedFeatures)

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


class DeepchecksDataValidator(BaseDataValidator):
    """Deepchecks data validator stack component."""

    # Class Configuration
    FLAVOR: ClassVar[str] = DEEPCHECKS_DATA_VALIDATOR_FLAVOR

    @classmethod
    def get_active_data_validator(cls) -> "DeepchecksDataValidator":
        """Get the Deepchecks data validator registered in the active stack.

        Returns:
            The Deepchecks data validator registered in the active stack.

        Raises:
            TypeError: if a Deepchecks data validator is not part of the
                active stack.
        """
        repo = Repository(skip_repository_check=True)  # type: ignore[call-arg]
        data_validator = repo.active_stack.data_validator
        if data_validator and isinstance(data_validator, cls):
            return data_validator

        raise TypeError(
            f"The active stack needs to have a Deepchecks data "
            f"validator component registered to be able to run data validation "
            f"actions with Deepchecks. You can create a new stack with "
            f"a Deepchecks data validator component or update your "
            f"active stack to add this component, e.g.:\n\n"
            f"  `zenml data-validator register deepchecks "
            f"--flavor={cls.FLAVOR} ...`\n"
            f"  `zenml stack register stack-name -dv deepchecks ...`\n"
            f"  or:\n"
            f"  `zenml stack update -dv deepchecks`\n\n"
        )

    @staticmethod
    def _split_checks(
        check_list: Sequence[str],
    ) -> Tuple[Sequence[str], Sequence[str]]:
        """Split a list of check identifiers in two lists, one for tabular and one for computer vision checks.

        Args:
            check_list: A list of check identifiers.

        Returns:
            List of tabular check identifiers and list of computer vision
            check identifiers.
        """
        tabular_checks = list(
            filter(
                lambda check: DeepchecksValidationCheck.is_tabular_check(check),
                check_list,
            )
        )
        vision_checks = list(
            filter(
                lambda check: DeepchecksValidationCheck.is_vision_check(check),
                check_list,
            )
        )
        return tabular_checks, vision_checks

    # flake8: noqa: C901
    @classmethod
    def _create_and_run_check_suite(
        cls,
        check_enum: Type[DeepchecksValidationCheck],
        reference_dataset: Union[pd.DataFrame, DataLoader[Any]],
        target_dataset: Optional[Union[pd.DataFrame, DataLoader[Any]]] = None,
        model: Optional[Union[ClassifierMixin, Module]] = None,
        check_list: Optional[Sequence[str]] = None,
        dataset_kwargs: Dict[str, Any] = {},
        check_kwargs: Dict[str, Dict[str, Any]] = {},
        run_kwargs: Dict[str, Any] = {},
    ) -> SuiteResult:
        """Create and run a Deepcheck check suite corresponding to the input parameters.

        This method contains generic logic common to all Deepcheck data
        validator methods that validates the input arguments and uses them to
        generate and run a Deepchecks check suite.

        Args:
            check_enum: ZenML enum type grouping together Deepchecks checks with
                the same characteristics. This is used to generate a default
                list of checks, if a custom list isn't provided via the
                `check_list` argument.
            reference_dataset: Primary (reference) dataset argument used during
                validation.
            target_dataset: Optional secondary (target) dataset argument used
                during validation.
            model: Optional model argument used during validation.
            check_list: Optional list of ZenML Deepchecks check identifiers
                specifying the list of Deepchecks checks to be performed.
            dataset_kwargs: Additional keyword arguments to be passed to the
                Deepchecks tabular.Dataset or vision.VisionData constructor.
            check_kwargs: Additional keyword arguments to be passed to the
                Deepchecks check object constructors. Arguments are grouped for
                each check and indexed using the full check class name or
                check enum value as dictionary keys.
            run_kwargs: Additional keyword arguments to be passed to the
                Deepchecks Suite `run` method.

        Returns:
            Deepchecks SuiteResult object with the Suite run results.

        Raises:
            TypeError: If the datasets, model and check list arguments combine
                data types and/or checks from different categories (tabular and
                computer vision).
        """
        # Detect what type of check to perform (tabular or computer vision) from
        # the dataset/model datatypes and the check list. At the same time,
        # validate the combination of data types used for dataset and model
        # arguments and the check list.
        is_tabular = False
        is_vision = False
        for dataset in [reference_dataset, target_dataset]:
            if dataset is None:
                continue
            if isinstance(dataset, pd.DataFrame):
                is_tabular = True
            elif isinstance(dataset, DataLoader):
                is_vision = True
            else:
                raise TypeError(
                    f"Unsupported dataset data type found: {type(dataset)}. "
                    f"Supported data types are {str(pd.DataFrame)} for tabular "
                    f"data and {str(DataLoader)} for computer vision data."
                )

        if model:
            if isinstance(model, ClassifierMixin):
                is_tabular = True
            elif isinstance(model, Module):
                is_vision = True
            else:
                raise TypeError(
                    f"Unsupported model data type found: {type(model)}. "
                    f"Supported data types are {str(ClassifierMixin)} for "
                    f"tabular data and {str(Module)} for computer vision "
                    f"data."
                )

        if is_tabular and is_vision:
            raise TypeError(
                f"Tabular and computer vision data types used for datasets and "
                f"models cannot be mixed. They must all belong to the same "
                f"category. Supported data types for tabular data are "
                f"{str(pd.DataFrame)} for datasets and {str(ClassifierMixin)} "
                f"for models. Supported data types for computer vision data "
                f"are {str(pd.DataFrame)} for datasets and and {str(Module)} "
                f"for models."
            )

        if not check_list:
            # default to executing all the checks listed in the supplied
            # checks enum type if a custom check list is not supplied
            tabular_checks, vision_checks = cls._split_checks(
                check_enum.values()
            )
            if is_tabular:
                check_list = tabular_checks
                vision_checks = []
            else:
                check_list = vision_checks
                tabular_checks = []
        else:
            tabular_checks, vision_checks = cls._split_checks(check_list)

        if tabular_checks and vision_checks:
            raise TypeError(
                f"The check list cannot mix tabular checks "
                f"({tabular_checks}) and computer vision checks ("
                f"{vision_checks})."
            )

        if is_tabular and vision_checks:
            raise TypeError(
                f"Tabular data types used for datasets and models can only "
                f"be used with tabular validation checks. The following "
                f"computer vision checks included in the check list are "
                f"not valid: {vision_checks}."
            )

        if is_vision and tabular_checks:
            raise TypeError(
                f"Computer vision data types used for datasets and models "
                f"can only be used with computer vision validation checks. "
                f"The following tabular checks included in the check list "
                f"are not valid: {tabular_checks}."
            )

        check_classes = map(
            lambda check: (
                check,
                check_enum.get_check_class(check),
            ),
            check_list,
        )

        # use the pipeline name and the step name to generate a unique suite
        # name
        try:
            # get pipeline name and step name
            step_env = cast(
                StepEnvironment, Environment()[STEP_ENVIRONMENT_NAME]
            )
            suite_name = f"{step_env.pipeline_name}_{step_env.step_name}"
        except KeyError:
            # if not running inside a pipeline step, use random values
            suite_name = f"suite_{random_str(5)}"

        if is_tabular:
            dataset_class = TabularData
            suite_class = TabularSuite
            full_suite = full_tabular_suite()
        else:
            dataset_class = VisionData
            suite_class = VisionSuite
            full_suite = full_vision_suite()

        train_dataset = dataset_class(reference_dataset, **dataset_kwargs)
        test_dataset = None
        if target_dataset is not None:
            test_dataset = dataset_class(target_dataset, **dataset_kwargs)
        suite = suite_class(name=suite_name)

        # Some Deepchecks checks require a minimum configuration such as
        # conditions to be configured (see https://docs.deepchecks.com/stable/user-guide/general/customizations/examples/plot_configure_check_conditions.html#sphx-glr-user-guide-general-customizations-examples-plot-configure-check-conditions-py)
        # for their execution to have meaning. For checks that don't have
        # custom configuration attributes explicitly specified in the
        # `check_kwargs` input parameter, we use the default check
        # instances extracted from the full suite shipped with Deepchecks.
        default_checks = {
            check.__class__: check for check in full_suite.checks.values()
        }
        for check_name, check_class in check_classes:
            extra_kwargs = check_kwargs.get(check_name, {})
            default_check = default_checks.get(check_class)
            if extra_kwargs or not default_check:
                suite.add(check_class(**check_kwargs))
            else:
                suite.add(default_check)
        return suite.run(
            train_dataset=train_dataset,
            test_dataset=test_dataset,
            model=model,
            **run_kwargs,
        )

    def data_validation(
        self,
        dataset: Union[pd.DataFrame, DataLoader[Any]],
        check_list: Optional[Sequence[str]] = None,
        model: Optional[Union[ClassifierMixin, Module]] = None,
        dataset_kwargs: Dict[str, Any] = {},
        check_kwargs: Dict[str, Dict[str, Any]] = {},
        run_kwargs: Dict[str, Any] = {},
        **kwargs: Any,
    ) -> SuiteResult:
        """Run one or more Deepchecks data integrity checks on a dataset.

        Call this method to analyze and identify potential integrity problems
        with a single dataset (e.g. missing values, conflicting labels, mixed
        data types etc.).

        The `check_list` argument may be used to specify a custom set of
        Deepchecks data integrity checks to perform, identified by
        `DeepchecksDataIntegrityCheck` enum values. If omitted, a suite with
        all available data integrity checks will be performed on the input data.
        See `DeepchecksDataIntegrityCheck` for a list of Deepchecks builtin
        checks that are compatible with this method.

        Some Deepchecks integrity checks may require that a model be present
        during the validation process to provide or dynamically generate
        additional information (e.g. label predictions, prediction probabilities,
        feature importance etc.) that is otherwise missing from the input
        dataset. Where that is the case, the method also takes in a model as
        argument. Alternatively, the missing information can be supplied using
        custom `dataset_kwargs`, `check_kwargs` or `run_args` keyword
        arguments.

        Args:
            dataset: Target dataset to be validated.
            check_list: Optional list of ZenML Deepchecks check identifiers
                specifying the data integrity checks to be performed.
                `DeepchecksDataIntegrityCheck` enum values should be used as
                elements.
            model: Optional model to use to provide or dynamically generate
                additional information necessary for data validation (e.g.
                labels, prediction probabilities, feature importance etc.).
            dataset_kwargs: Additional keyword arguments to be passed to the
                Deepchecks tabular.Dataset or vision.VisionData constructor.
            check_kwargs: Additional keyword arguments to be passed to the
                Deepchecks check object constructors. Arguments are grouped for
                each check and indexed using the full check class name or
                check enum value as dictionary keys.
            run_kwargs: Additional keyword arguments to be passed to the
                Deepchecks Suite `run` method.
            kwargs: Additional keyword arguments (unused).

        Returns:
            A Datachecks SuiteResult with the results of the validation.
        """
        return self._create_and_run_check_suite(
            check_enum=DeepchecksDataIntegrityCheck,
            reference_dataset=dataset,
            target_dataset=None,
            model=model,
            check_list=check_list,
            dataset_kwargs=dataset_kwargs,
            check_kwargs=check_kwargs,
            run_kwargs=run_kwargs,
        )

    def model_validation(
        self,
        dataset: Union[pd.DataFrame, DataLoader[Any]],
        model: Union[ClassifierMixin, Module],
        check_list: Optional[Sequence[str]] = None,
        dataset_kwargs: Dict[str, Any] = {},
        check_kwargs: Dict[str, Dict[str, Any]] = {},
        run_kwargs: Dict[str, Any] = {},
        **kwargs: Any,
    ) -> Any:
        """Run one or more Deepchecks model validation checks.

        Call this method to perform model validation checks (e.g. confusion
        matrix validation, performance reports, model error analyses, etc).

        The `check_list` argument may be used to specify a custom set of
        Deepchecks model validation checks to perform, identified by
        `DeepchecksModelValidationCheck` enum values. If omitted, a suite with
        all available model validation checks that take a single dataset as
        input will be performed on the input data.
        See `DeepchecksModelValidationCheck` for a list of Deepchecks builtin
        checks that are compatible with this method.

        Args:
            dataset: Target dataset to be validated.
            model: Target model to be validated.
            check_list: Optional list of ZenML Deepchecks check identifiers
                specifying the model validation checks to be performed.
                `DeepchecksModelValidationCheck` enum values should be used as
                elements.
            dataset_kwargs: Additional keyword arguments to be passed to the
                Deepchecks tabular.Dataset or vision.VisionData constructor.
            check_kwargs: Additional keyword arguments to be passed to the
                Deepchecks check object constructors. Arguments are grouped for
                each check and indexed using the full check class name or
                check enum value as dictionary keys.
            run_kwargs: Additional keyword arguments to be passed to the
                Deepchecks Suite `run` method.
            kwargs: Additional keyword arguments (unused).

        Returns:
            A Datachecks SuiteResult with the results of the validation.
        """
        return self._create_and_run_check_suite(
            check_enum=DeepchecksModelValidationCheck,
            reference_dataset=dataset,
            target_dataset=None,
            model=model,
            check_list=check_list,
            dataset_kwargs=dataset_kwargs,
            check_kwargs=check_kwargs,
            run_kwargs=run_kwargs,
        )

    def data_comparison(
        self,
        reference_dataset: Union[pd.DataFrame, DataLoader[Any]],
        target_dataset: Union[pd.DataFrame, DataLoader[Any]],
        check_list: Optional[Sequence[str]] = None,
        model: Optional[Union[ClassifierMixin, Module]] = None,
        dataset_kwargs: Dict[str, Any] = {},
        check_kwargs: Dict[str, Dict[str, Any]] = {},
        run_kwargs: Dict[str, Any] = {},
        **kwargs: Any,
    ) -> Any:
        """Run one or more data comparison (data drift) checks.

        Call this method to perform dataset comparison checks (e.g. data drift
        checks) by comparing a target dataset to a reference dataset.

        The `check_list` argument may be used to specify a custom set of
        Deepchecks data comparison checks to perform, identified by
        `DeepchecksDataDriftCheck` enum values. If omitted, a suite with
        all available data comparison checks that don't require a model as
        input will be performed on the input datasets.
        See `DeepchecksDataDriftCheck` for a list of Deepchecks builtin
        checks that are compatible with this method.

        Some Deepchecks data comparison checks may require that a model be
        present during the validation process to provide or dynamically generate
        additional information (e.g. label predictions, prediction probabilities,
        feature importance etc.) that is otherwise missing from the input
        datasets. Where that is the case, the method also takes in a model as
        argument. Alternatively, the missing information can be supplied using
        custom `dataset_kwargs`, `check_kwargs` or `run_args` keyword
        arguments.

        Args:
            reference_dataset: Reference dataset (e.g. dataset used during model
                training).
            target_dataset: Dataset to be validated (e.g. dataset used during
                model validation or new data used in production).
            check_list: Optional list of ZenML Deepchecks check identifiers
                specifying the data comparison checks to be performed.
                `DeepchecksDataDriftCheck` enum values should be used as
                elements.
            model: Optional model to use to provide or dynamically generate
                additional information necessary for data comparison (e.g.
                labels, prediction probabilities, feature importance etc.).
            dataset_kwargs: Additional keyword arguments to be passed to the
                Deepchecks tabular.Dataset or vision.VisionData constructor.
            check_kwargs: Additional keyword arguments to be passed to the
                Deepchecks check object constructors. Arguments are grouped for
                each check and indexed using the full check class name or
                check enum value as dictionary keys.
            run_kwargs: Additional keyword arguments to be passed to the
                Deepchecks Suite `run` method.
            kwargs: Additional keyword arguments (unused).

        Returns:
            A Datachecks SuiteResult with the results of the validation.
        """
        return self._create_and_run_check_suite(
            check_enum=DeepchecksDataDriftCheck,
            reference_dataset=reference_dataset,
            target_dataset=target_dataset,
            model=model,
            check_list=check_list,
            dataset_kwargs=dataset_kwargs,
            check_kwargs=check_kwargs,
            run_kwargs=run_kwargs,
        )

    def model_comparison(
        self,
        reference_dataset: Union[pd.DataFrame, DataLoader[Any]],
        target_dataset: Union[pd.DataFrame, DataLoader[Any]],
        model: Union[ClassifierMixin, Module],
        check_list: Optional[Sequence[str]] = None,
        dataset_kwargs: Dict[str, Any] = {},
        check_kwargs: Dict[str, Dict[str, Any]] = {},
        run_kwargs: Dict[str, Any] = {},
        **kwargs: Any,
    ) -> Any:
        """Validate a model using a target and a reference dataset.

        This method should be implemented by data validators that support
        identifying changes in a model performance by analyzing how it performs
        on a target dataset in comparison to how it performs on a reference
        dataset.

        The `check_list` argument may be used to specify a custom set of
        Deepchecks model comparison checks to perform, identified by
        `DeepchecksModelDriftCheck` enum values. If omitted, a suite with
        all available model comparison checks will be performed on the input
        datasets and model.
        See `DeepchecksModelDriftCheck` for a list of Deepchecks builtin
        checks that are compatible with this method.

        Args:
            reference_dataset: Reference dataset (e.g. dataset used during model
                training).
            target_dataset: Dataset to be validated (e.g. dataset used during
                model validation or new data used in production).
            model: Target model to be validated.
            check_list: Optional list of ZenML Deepchecks check identifiers
                specifying the model comparison checks to be performed.
                `DeepchecksModelDriftCheck` enum values should be used as
                elements.
            dataset_kwargs: Additional keyword arguments to be passed to the
                Deepchecks tabular.Dataset or vision.VisionData constructor.
            check_kwargs: Additional keyword arguments to be passed to the
                Deepchecks check object constructors. Arguments are grouped for
                each check and indexed using the full check class name or
                check enum value as dictionary keys.
            run_kwargs: Additional keyword arguments to be passed to the
                Deepchecks Suite `run` method.
            kwargs: Additional keyword arguments (unused).

        Returns:
            A Datachecks SuiteResult with the results of the validation.
        """
        return self._create_and_run_check_suite(
            check_enum=DeepchecksModelDriftCheck,
            reference_dataset=reference_dataset,
            target_dataset=target_dataset,
            model=model,
            check_list=check_list,
            dataset_kwargs=dataset_kwargs,
            check_kwargs=check_kwargs,
            run_kwargs=run_kwargs,
        )
