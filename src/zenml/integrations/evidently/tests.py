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
"""ZenML declarative representation of Evidently Tests."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

from evidently import test_preset, tests  # type: ignore[import-untyped]
from evidently.test_preset.test_preset import (  # type: ignore[import-untyped]
    TestPreset,
)
from evidently.tests.base_test import (  # type: ignore[import-untyped]
    Test,
    generate_column_tests,
)
from evidently.utils.generators import (  # type: ignore[import-untyped]
    BaseGenerator,
)
from pydantic import BaseModel, ConfigDict, Field

from zenml.logger import get_logger
from zenml.utils import source_utils

logger = get_logger(__name__)


class EvidentlyTestConfig(BaseModel):
    """Declarative Evidently Test configuration.

    This is a declarative representation of the configuration that goes into an
    Evidently Test, TestPreset or Test generator instance. We need this to
    be able to store the configuration as part of a ZenML step parameter and
    later instantiate the Evidently Test from it.

    This representation covers all 3 possible ways of configuring an Evidently
    Test or Test-like object that can later be used in an Evidently TestSuite:

    1. A Test (derived from the Test class).
    2. A TestPreset (derived from the TestPreset class).
    3. A column Test generator (derived from the BaseGenerator class).

    Ideally, it should be possible to just pass a Test or Test-like
    object to this class and have it automatically derive the configuration used
    to instantiate it. Unfortunately, this is not possible because the Evidently
    Test classes are not designed in a way that allows us to extract the
    constructor parameters from them in a generic way.

    Attributes:
        class_path: The full class path of the Evidently Test class.
        parameters: The parameters of the Evidently Test.
        is_generator: Whether this is an Evidently column Test generator.
        columns: The columns that the Evidently column Test generator is
            applied to. Only used if `generator` is True.
    """

    class_path: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    is_generator: bool = False
    columns: Optional[Union[str, List[str]]] = Field(
        default=None, union_mode="left_to_right"
    )

    @staticmethod
    def get_test_class(test_name: str) -> Union[Test, TestPreset]:
        """Get the Evidently test or test preset class from a string.

        Args:
            test_name: The test or test preset class or full class
                path.

        Returns:
            The Evidently test or test preset class.

        Raises:
            ValueError: If the name cannot be converted into a valid Evidently
                test or test preset class.
        """
        # First, try to interpret the test name as a full class path.
        if "." in test_name:
            try:
                test_class = source_utils.load(test_name)
            except (ImportError, AttributeError) as e:
                raise ValueError(
                    f"Could not import Evidently Test or TestPreset "
                    f"`{test_name}`: {str(e)}"
                )

        else:
            # Next, try to interpret the test as a Test or TestPreset
            # class name
            if hasattr(tests, test_name):
                test_class = getattr(tests, test_name)
            elif hasattr(test_preset, test_name):
                test_class = getattr(test_preset, test_name)
            else:
                raise ValueError(
                    f"Could not import Evidently Test or TestPreset "
                    f"`{test_name}`"
                )

        if not issubclass(test_class, (Test, TestPreset)):
            raise ValueError(
                f"Class `{test_name}` is not a valid Evidently "
                f"Test or TestPreset."
            )

        return test_class

    @classmethod
    def test_generator(
        cls,
        test: Union[Type[Test], str],
        columns: Optional[Union[str, List[str]]] = None,
        **parameters: Any,
    ) -> "EvidentlyTestConfig":
        """Create a declarative configuration for an Evidently column Test generator.

        Call this method to get a declarative representation for the
        configuration of an Evidently column Test generator.

        The `columns`, `parameters` arguments will be
        passed to the Evidently `generate_column_tests` function:

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
        from zenml.integrations.evidently.data_validators import EvidentlyTest

        # Configure an Evidently Test generator using a Test class name
        # and pass additional parameters
        config = EvidentlyTest.test_generator(
            "TestColumnValueMin", columns="num", gt=0.5
        )
        ```

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyTest

        # Configure an Evidently Test generator using a full Test class
        # path
        config = EvidentlyTest.test_generator(
            "evidently.tests.TestColumnShareOfMissingValues", columns=["age", "name"]
        )
        ```

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyTest

        # Configure an Evidently Test generator using a Test class
        from evidently.tests import TestColumnQuantile
        config = EvidentlyTest.test_generator(
            TestColumnQuantile, columns="all", quantile=0.5
        )
        ```

        Args:
            test: The Evidently Test class, class name or class path to use
                for the generator.
            columns: The columns to apply the generator to. Takes the same
                values that the Evidently `generate_column_tests` function
                takes.
            parameters: Additional optional parameters needed to instantiate the
                Evidently Test. These will be passed to the Evidently
                `generate_column_tests` function.

        Returns:
            The EvidentlyTest declarative representation of the Evidently
            Test generator configuration.

        Raises:
            ValueError: If `test` does not point to a valid Evidently Test
                or TestPreset class.
        """
        if isinstance(test, str):
            test_class = cls.get_test_class(test)
        elif issubclass(test, (Test, TestPreset)):
            test_class = test
        else:
            raise ValueError(f"Invalid Evidently Test class: {test}")

        class_path = f"{test_class.__module__}.{test_class.__name__}"

        config = cls(
            class_path=class_path,
            parameters=parameters,
            columns=columns,
            is_generator=True,
        )

        # Try to instantiate the configuration to check if the parameters are
        # valid
        config.to_evidently_test()

        return config

    @classmethod
    def test(
        cls,
        test: Union[Type[Test], Type[TestPreset], str],
        **parameters: Any,
    ) -> "EvidentlyTestConfig":
        """Create a declarative configuration for an Evidently Test.

        Call this method to get a declarative representation for the
        configuration of an Evidently Test.

        Some examples
        -------------

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyTest

        # Configure an Evidently TestPreset using its class name
        config = EvidentlyTest.test("DataDriftPreset")
        ```

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyTest

        # Configure an Evidently TestPreset using its full class path
        config = EvidentlyTest.test(
            "evidently.test_preset.DataDriftPreset"
        )
        ```

        ```python
        from zenml.integrations.evidently.data_validators import EvidentlyTest

        # Configure an Evidently Test using its class and pass additional
        # parameters
        from evidently.tests import ColumnSummaryTest
        config = EvidentlyTest.test(
            ColumnSummaryTest, column_name="age"
        )
        ```

        Args:
            test: The Evidently Test or TestPreset class, class name or
                class path.
            parameters: Additional optional parameters needed to instantiate the
                Evidently Test or TestPreset.

        Returns:
            The EvidentlyTest declarative representation of the Evidently
            Test configuration.

        Raises:
            ValueError: If `test` does not point to a valid Evidently Test
                or TestPreset class.
        """
        if isinstance(test, str):
            test_class = cls.get_test_class(test)
        elif issubclass(test, (Test, TestPreset)):
            test_class = test
        else:
            raise ValueError(
                f"Invalid Evidently Test or TestPreset class: {test}"
            )

        class_path = f"{test_class.__module__}.{test_class.__name__}"
        config = cls(class_path=class_path, parameters=parameters)

        # Try to instantiate the configuration to check if the parameters are
        # valid
        config.to_evidently_test()

        return config

    @classmethod
    def default_tests(cls) -> List["EvidentlyTestConfig"]:
        """Default Evidently test configurations.

        Call this to fetch a default list of Evidently tests to use in cases
        where no tests are explicitly configured for a data validator.
        All available Evidently TestPreset classes are used.

        Returns:
            A list of EvidentlyTestConfig objects to use as default tests.
        """
        return [
            cls.test(test=test_preset_class_name)
            for test_preset_class_name in test_preset.__all__
        ]

    def to_evidently_test(self) -> Union[Test, TestPreset, BaseGenerator]:
        """Create an Evidently Test, TestPreset or test generator object.

        Call this method to create an Evidently Test, TestPreset or test
        generator instance from its declarative representation.

        Returns:
            The Evidently Test, TestPreset or test generator object.

        Raises:
            ValueError: If the Evidently Test, TestPreset or column test
                generator could not be instantiated.
        """
        test_class = self.get_test_class(self.class_path)

        if self.is_generator:
            try:
                return generate_column_tests(
                    test_class=test_class,
                    columns=self.columns,
                    parameters=self.parameters,
                )
            except Exception as e:
                raise ValueError(
                    f"Could not instantiate Evidently column Test generator "
                    f"`{self.class_path}`: {str(e)}"
                )

        try:
            return test_class(**self.parameters)
        except Exception as e:
            raise ValueError(
                f"Could not instantiate Evidently Test or TestPreset "
                f"`{self.class_path}`: {str(e)}"
            )

    model_config = ConfigDict(extra="ignore")
