# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Step function to run any ZenML step using Accelerate."""

import functools
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast

import cloudpickle as pickle
from accelerate.commands.launch import (  # type: ignore[import-untyped]
    launch_command,
    launch_command_parser,
)

from zenml import get_pipeline_context
from zenml.logger import get_logger
from zenml.steps import BaseStep
from zenml.utils.function_utils import _cli_arg_name, create_cli_wrapped_script

logger = get_logger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


def run_with_accelerate(
    step_function_top_level: Optional[BaseStep] = None,
    **accelerate_launch_kwargs: Any,
) -> Union[Callable[[BaseStep], BaseStep], BaseStep]:
    """Run a function with accelerate.

    Accelerate package: https://huggingface.co/docs/accelerate/en/index
    Example:
        ```python
        from zenml import step, pipeline
        from zenml.integrations.hugginface.steps import run_with_accelerate
        @step
        def training_step(some_param: int, ...):
            # your training code is below
            ...

        @pipeline
        def training_pipeline(some_param: int, ...):
            run_with_accelerate(training_step, num_processes=4)(some_param, ...)
        ```

    Args:
        step_function_top_level: The step function to run with accelerate [optional].
            Used in functional calls like `run_with_accelerate(some_func,foo=bar)()`.
        accelerate_launch_kwargs: A dictionary of arguments to pass along to the
            `accelerate launch` command, including hardware selection, resource
            allocation, and training paradigm options. Visit
            https://huggingface.co/docs/accelerate/en/package_reference/cli#accelerate-launch
            for more details.

    Returns:
        The accelerate-enabled version of the step.
    """

    def _decorator(step_function: BaseStep) -> BaseStep:
        def _wrapper(
            entrypoint: F, accelerate_launch_kwargs: Dict[str, Any]
        ) -> F:
            @functools.wraps(entrypoint)
            def inner(*args: Any, **kwargs: Any) -> Any:
                if args:
                    raise ValueError(
                        "Accelerated steps do not support positional arguments."
                    )

                with create_cli_wrapped_script(
                    entrypoint, flavour="accelerate"
                ) as (
                    script_path,
                    output_path,
                ):
                    commands = [str(script_path.absolute())]
                    for k, v in kwargs.items():
                        k = _cli_arg_name(k)
                        if isinstance(v, bool):
                            if v:
                                commands.append(f"--{k}")
                        elif type(v) in (list, tuple, set):
                            for each in v:
                                commands += [f"--{k}", f"{each}"]
                        else:
                            commands += [f"--{k}", f"{v}"]
                    logger.debug(commands)

                    parser = launch_command_parser()
                    args = parser.parse_args(commands)
                    for k, v in accelerate_launch_kwargs.items():
                        if k in args:
                            setattr(args, k, v)
                        else:
                            logger.warning(
                                f"You passed in `{k}` as an `accelerate launch` argument, but it was not accepted. "
                                "Please check https://huggingface.co/docs/accelerate/en/package_reference/cli#accelerate-launch "
                                "to find out more about supported arguments and retry."
                            )
                    try:
                        launch_command(args)
                    except Exception as e:
                        logger.error(
                            "Accelerate training job failed... See error message for details."
                        )
                        raise RuntimeError(
                            "Accelerate training job failed."
                        ) from e
                    else:
                        logger.info(
                            "Accelerate training job finished successfully."
                        )
                        return pickle.load(open(output_path, "rb"))

            return cast(F, inner)

        try:
            get_pipeline_context()
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                f"`{run_with_accelerate.__name__}` decorator cannot be used "
                "in a functional way with steps, please apply decoration "
                "directly to a step instead. This behavior will be also "
                "allowed in future, but now it faces technical limitations.\n"
                "Example (allowed):\n"
                f"@{run_with_accelerate.__name__}(...)\n"
                f"def {step_function.name}(...):\n"
                "    ...\n"
                "Example (not allowed):\n"
                "def my_pipeline(...):\n"
                f"    run_with_accelerate({step_function.name},...)(...)\n"
            )

        setattr(
            step_function, "unwrapped_entrypoint", step_function.entrypoint
        )
        setattr(
            step_function,
            "entrypoint",
            _wrapper(
                step_function.entrypoint,
                accelerate_launch_kwargs=accelerate_launch_kwargs,
            ),
        )

        return step_function

    if step_function_top_level:
        return _decorator(step_function_top_level)
    return _decorator
