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

from typing import Any, Dict, Type

from great_expectations.expectations.expectation import Expectation

from pydantic import BaseModel

from zenml.config.source import Source, SourceType
from zenml.logger import get_logger
from zenml.utils import source_utils
from importlib import import_module

logger = get_logger(__name__)


class GreatExpectationExpectationConfig(BaseModel):
    """Great Expectation expectation configuration.

    This class defines the configuration parameters that can be used to
    customize the behavior of a Great Expectation Expectation. This includes
    the expectation name (in snake case), and any input options that the
    expectation expects. This could be the column name, the value to 
    compare against, etc.

    You can also choose to pass in parameters as the value to an input option. 
    You can then supply the parameters as a dictionary to the expectation_parameters 
    field. But this is not particularly useful when you are defining the expectations 
    directly with ZenML. The value of defining parameters in expectations and 
    passing the values at runtime is more pronounced when you already have a suite 
    of expectations defined and you use this suite with ZenML, with different 
    parameters.

    Attributes:
        expectation_name: The name of the Great Expectation expectation to apply in snake case.
        expectation_args: Input arguments to pass to the expectation. These can be 
            used to pass the column name, the value to compare against, etc.

    """
    expectation_name: str
    expectation_args: Dict[str, Any] = {}
    
    @staticmethod
    def get_expectation_class(expectation_name: str) -> Type[Expectation]:
        """Get the Great Expectation expectation class associated with this config.

        Returns:
            The Great Expectation expectation class associated with this config.

        Raises:
            TypeError: If the expectation name could not be converted to a valid
                Great Expectation expectation class. This can happen for example
                if the expectation name does not map to a valid Great Expectation
                expectation class.
        """
        module_name = f"great_expectations.expectations.core.{expectation_name}"
        class_name = "".join(word.capitalize() for word in expectation_name.split("_"))
        
        return source_utils.load_and_validate_class(
            source=Source(module=module_name, attribute=class_name, type=SourceType.USER),
            expected_class=Expectation,
        )

    def get_expectation(self) -> Expectation:
        """Get the Great Expectation expectation object associated with this config.

        Returns:
            The Great Expectation expectation object associated with this config.
        """
        try:
            expectation_class = self.get_expectation_class(self.expectation_name)
            expectation = expectation_class(**self.expectation_args)
        except TypeError:
            raise ValueError(
                f"Could not map the `{self.expectation_name}` expectation "
                f"identifier to a valid Great Expectation expectation class."
            )
        except Exception as e:
            raise ValueError(
                f"An error occurred while trying to instantiate the "
                f"`{self.expectation_name}` expectation class "
                f"with the following parameters: {self.expectation_args}"
                f"Exception: {str(e)}"
            )
        
        return expectation
