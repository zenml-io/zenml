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

import wandb

from zenml.environment import Environment
from zenml.integrations.wandb.experiment_trackers.wandb_experiment_tracker import (
    WandbExperimentTracker,
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
def enable_wandb(
    _step: S,
) -> S:
    """Type annotations for wandb step decorator in case of no arguments."""
    ...


@overload
def enable_wandb(
    *, settings: Optional[wandb.Settings] = None
) -> Callable[[S], S]:
    """Type annotations for wandb step decorator in case of arguments."""
    ...


def enable_wandb(
    _step: Optional[S] = None, *, settings: Optional[wandb.Settings] = None
) -> Union[S, Callable[[S], S]]:
    """Decorator to enable wandb for a step function.

    Apply this decorator to a ZenML pipeline step to enable wandb experiment
    tracking. The wandb tracking configuration (project name, experiment name,
    entity) will be automatically configured before the step code is executed,
    so the step can simply use the `wandb` module to log metrics and artifacts,
    like so:

    ```python
    @enable_wandb
    @step
    def tf_evaluator(
        x_test: np.ndarray,
        y_test: np.ndarray,
        model: tf.keras.Model,
    ) -> float:
        _, test_acc = model.evaluate(x_test, y_test, verbose=2)
        wandb.log_metric("val_accuracy", test_acc)
        return test_acc
    ```

    All wandb artifacts and metrics logged from all the steps in a pipeline
    run are by default grouped under a single experiment named after the
    pipeline. To log wandb artifacts and metrics from a step in a separate
    wandb experiment, pass a custom `experiment_name` argument value to the
    decorator.

    Args:
        _step: The decorated step class.
        project_name: Name of project.
        experiment_name: optional wandb experiment name to use for the step.
            If not provided, the name of the pipeline in the context of which
            the step is executed will be used as experiment name.

    Returns:
        The inner decorator which enhances the input step class with wandb
        tracking functionality
    """

    def inner_decorator(_step: S) -> S:
        """Inner decorator for step enable_wandb."""

        logger.debug(
            "Applying 'enable_wandb' decorator to step %s", _step.__name__
        )
        if not issubclass(_step, BaseStep):
            raise RuntimeError(
                "The `enable_wandb` decorator can only be applied to a ZenML "
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
                        wandb_step_entrypoint(
                            settings=settings,
                        )(source_fn)
                    ),
                    "__module__": _step.__module__,
                },
            ),
        )

    if _step is None:
        return inner_decorator
    else:
        return inner_decorator(_step)


def wandb_step_entrypoint(
    settings: Optional[wandb.Settings] = None,
) -> Callable[[F], F]:
    """Decorator for a step entrypoint to enable wandb.

    Args:
        project_name: Name of wandb project.
        experiment_name: optional wandb experiment name to use for the step.
            If not provided, the name of the pipeline in the context of which
            the step is executed will be used as experiment name.

    Returns:
        the input function enhanced with wandb profiling functionality
    """

    def inner_decorator(func: F) -> F:
        """Inner decorator for step entrypoint."""
        logger.debug(
            "Applying 'wandb_step_entrypoint' decorator to step entrypoint %s",
            func.__name__,
        )

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa
            """Wrapper function for decorator"""
            logger.debug(
                "Setting up wandb backend before running step entrypoint %s",
                func.__name__,
            )
            step_env = Environment().step_environment
            run_name = f"{step_env.pipeline_run_id}_{step_env.step_name}"
            tags = (step_env.pipeline_name, step_env.pipeline_run_id)

            experiment_tracker = Repository(  # type: ignore[call-arg]
                skip_repository_check=True
            ).active_stack.experiment_tracker

            if not isinstance(experiment_tracker, WandbExperimentTracker):
                raise ValueError(
                    "The active stack needs to have a wandb experiment tracker "
                    "component registered to be able to track experiments "
                    "using wandb. You can create a new stack with a wandb "
                    "experiment tracker component or update your existing "
                    "stack to add this component, e.g.:\n\n"
                    "  'zenml experiment-tracker register wandb_tracker "
                    "--type=wandb --entity=<WANDB_ENTITY> --project_name="
                    "<WANDB_PROJECT_NAME> --api_key=<WANDB_API_KEY>'\n"
                    "  'zenml stack register stack-name -e wandb_tracker ...'\n"
                )

            with experiment_tracker.activate_wandb_run(
                run_name=run_name,
                tags=tags,
                settings=settings,
            ):
                return func(*args, **kwargs)

        return cast(F, wrapper)

    return inner_decorator
