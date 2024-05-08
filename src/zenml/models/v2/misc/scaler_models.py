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

from typing import Any, Callable, ClassVar, Dict, Optional, Set, TypeVar

from pydantic import BaseModel, root_validator

F = TypeVar("F", bound=Callable[..., None])


class ScalerModel(BaseModel):
    """Domain model for scalers."""

    scaler_flavor: Optional[str] = None

    ALLOWED_SCALER_FLAVORS: ClassVar[Set[str]] = {
        # "ScalerModel",
        "AccelerateScaler",
    }

    @root_validator(pre=True)
    def validate_scaler_flavor(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the scaler flavor."""
        if values.get("scaler_flavor", None) is None:
            values["scaler_flavor"] = cls.__name__
        if values["scaler_flavor"] not in cls.ALLOWED_SCALER_FLAVORS:
            raise ValueError(
                f"Invalid scaler flavor {values['scaler_flavor']}. "
                f"Allowed values are {cls.ALLOWED_SCALER_FLAVORS}"
            )
        return values

    def run(self, step_function: F, **kwargs: Any) -> None:
        """Run the step using scaler.

        Args:
            step_function: The step function to run.
            **kwargs: Additional arguments to pass to the step function.
        """
        if self.scaler_flavor == "AccelerateScaler":
            from zenml.integrations.accelerate import AccelerateScaler

            runner = AccelerateScaler(**self.dict())
        else:
            raise NotImplementedError

        return runner.run(step_function, **kwargs)

    class Config:
        """Pydantic model configuration."""

        extra = "allow"
