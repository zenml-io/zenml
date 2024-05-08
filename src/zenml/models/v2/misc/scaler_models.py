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
"""Model definitions for ZenML scalers."""

from typing import Any, Callable, TypeVar

from pydantic import BaseModel

F = TypeVar("F", bound=Callable[..., None])


class ScalerModel(BaseModel):
    """Domain model for scalers."""

    def run(self, step_function: F, **kwargs: Any) -> None:
        """Run the step using scaler.

        Args:
            step_function: The step function to run.
            **kwargs: Additional arguments to pass to the step function.

        Raises:
            NotImplementedError: If the scaler does not implement the
                `run` method.
        """
        raise NotImplementedError
