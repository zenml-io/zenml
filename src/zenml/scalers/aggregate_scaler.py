#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Aggregate local scaler."""

import inspect
from multiprocessing.pool import ThreadPool
from typing import Any, Callable, Dict, List, TypeVar

from pydantic import validator

from zenml.enums import AggregateFunction
from zenml.logger import get_logger
from zenml.models.v2.misc.scaler_models import ScalerModel
from zenml.scalers.utils import AGGREGATE_FUNCTIONS

logger = get_logger(__name__)
F = TypeVar("F", bound=Callable[..., None])


class AggregateScaler(ScalerModel):
    """Aggregate scaler.

    Example:
        ```python
        from zenml import step, pipeline
        from zenml.scalers import AggregateScaler

        @step(scaler=AggregateScaler(parameters={"a":[1,2,3],"b":[4,5,6]}, agg_function="sum"))
        def training_step_with_sum_aggregation(a:int = None, b:int = None, c:int = 2)->int:
            # your code is below
            return a+b+c

        @pipeline
        def pipeline_with_aggregate_scaler():
            training_step_with_sum_aggregation(c=3)
        # actual step output would be (1+4+3)+(2+5+3)+(3+6+3) = 30,
        # where last "+3" comes from constant `c` parameter
        ```

    Args:
        parameters: The parameters to run on.
        num_processes: The number of processes to use (shall be less or equal to GPUs count).
        agg_function: The aggregation function to use.
    """

    parameters: Dict[str, List[Any]]
    num_processes: int = 1
    agg_function: AggregateFunction = AggregateFunction.SUM

    @validator("parameters")
    def validate_values(
        cls, parameters: Dict[str, List[Any]]
    ) -> Dict[str, List[Any]]:
        """Validate the parameters.

        Args:
            parameters: The parameters to run on.

        Returns:
            The validated parameters.

        Raises:
            ValueError: If the parameters are not of the same length.
        """
        lengths = {}
        first_length = None
        lengths_are_different = False
        for k, v in parameters.items():
            lengths[k] = len(v)
            if first_length is None:
                first_length = len(v)
            elif len(v) != first_length:
                lengths_are_different = True
        if lengths_are_different:
            raise ValueError(
                f"Parameters are not of the same length: {lengths}"
            )
        return parameters

    def run(self, step_function: F, **function_kwargs: Any) -> Any:
        """Run a function with matrix strategy.

        Args:
            step_function: The step function to run.
            **function_kwargs: Additional arguments to pass to the step function.

        Returns:
            The result of the step function.

        Raises:
            ValueError: If the function arguments do not match the parameters.
        """
        logger.info("Starting aggregate job...")
        function_arg_names = inspect.getargs(step_function.__code__).args
        given_arg_names = set(self.parameters.keys()).union(
            set(function_kwargs.keys())
        )
        if set(function_arg_names) != given_arg_names:
            raise ValueError(
                f"Function arguments {function_arg_names} do not match parameters configured {given_arg_names}"
            )
        params_to_pass: List[List[Any]] = []
        for i in range(len(self.parameters[function_arg_names[0]])):
            params_to_pass.append([])
            for arg_name in function_arg_names:
                if arg_name in self.parameters:
                    params_to_pass[i].append(self.parameters[arg_name][i])
                else:
                    params_to_pass[i].append(function_kwargs[arg_name])

        result = ThreadPool(processes=self.num_processes).starmap(
            step_function,
            params_to_pass,
        )

        return AGGREGATE_FUNCTIONS[self.agg_function](result)
