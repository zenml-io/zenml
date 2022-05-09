#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import functools
from typing import Any, Callable, Optional, Type, TypeVar, Union, cast, overload

from zenml.integrations.mlflow.experiment_trackers.mlflow_experiment_tracker import (
    MLFlowExperimentTracker,
)
from zenml.integrations.mlflow.mlflow_utils import (
    get_missing_mlflow_experiment_tracker_error,
)
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.steps import BaseStep
from zenml.steps.utils import STEP_INNER_FUNC_NAME

logger = get_logger(__name__)


# step entrypoint type
F = TypeVar("F", bound=Callable[..., Any])

# step class type
S = TypeVar("S", bound=Type[BaseStep])


@overload
def enable_mlflow(
    _step: S,
) -> S:
    """Type annotations for mlflow step decorator in case of no arguments."""
    ...


@overload
def enable_mlflow() -> Callable[[S], S]:
    """Type annotations for mlflow step decorator in case of arguments."""
    ...


def enable_mlflow(
    _step: Optional[S] = None,
) -> Union[S, Callable[[S], S]]:
    """Decorator to enable mlflow for a step function.

    Apply this decorator to a ZenML pipeline step to enable MLflow experiment
    tracking. The MLflow tracking configuration (tracking URI, experiment name,
    run name) will be automatically configured before the step code is executed,
    so the step can simply use the `mlflow` module to log metrics and artifacts,
    like so:

    ```python
    @enable_mlflow
    @step
    def tf_evaluator(
        x_test: np.ndarray,
        y_test: np.ndarray,
        model: tf.keras.Model,
    ) -> float:
        _, test_acc = model.evaluate(x_test, y_test, verbose=2)
        mlflow.log_metric("val_accuracy", test_acc)
        return test_acc
    ```

    All MLflow artifacts and metrics logged from all the steps in a pipeline
    run are by default grouped under a single experiment named after the
    pipeline. To log MLflow artifacts and metrics from a step in a separate
    MLflow experiment, pass a custom `experiment_name` argument value to the
    decorator.

    Args:
        _step: The decorated step class.

    Returns:
        The inner decorator which enhaces the input step class with mlflow
        tracking functionality
    """

    def inner_decorator(_step: S) -> S:

        logger.debug(
            "Applying 'enable_mlflow' decorator to step %s", _step.__name__
        )
        if not issubclass(_step, BaseStep):
            raise RuntimeError(
                "The `enable_mlflow` decorator can only be applied to a ZenML "
                "`step` decorated function or a BaseStep subclass."
            )
        source_fn = getattr(_step, STEP_INNER_FUNC_NAME)
        return cast(
            S,
            type(  # noqa
                _step.__name__,
                (_step,),
                {
                    STEP_INNER_FUNC_NAME: staticmethod(
                        mlflow_step_entrypoint()(source_fn)
                    ),
                    "__module__": _step.__module__,
                },
            ),
        )

    if _step is None:
        return inner_decorator
    else:
        return inner_decorator(_step)


def mlflow_step_entrypoint() -> Callable[[F], F]:
    """Decorator for a step entrypoint to enable mlflow.

    Returns:
        the input function enhanced with mlflow profiling functionality
    """

    def inner_decorator(func: F) -> F:

        logger.debug(
            "Applying 'mlflow_step_entrypoint' decorator to step entrypoint %s",
            func.__name__,
        )

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa
            logger.debug(
                "Setting up MLflow backend before running step entrypoint %s",
                func.__name__,
            )
            experiment_tracker = Repository(  # type: ignore[call-arg]
                skip_repository_check=True
            ).active_stack.experiment_tracker

            if not isinstance(experiment_tracker, MLFlowExperimentTracker):
                raise get_missing_mlflow_experiment_tracker_error()

            active_run = experiment_tracker.active_run
            if not active_run:
                raise RuntimeError("No active mlflow run configured.")

            with active_run:
                return func(*args, **kwargs)

        return cast(F, wrapper)

    return inner_decorator
