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
from typing import Any, Callable, Optional, TypeVar, cast

import cloudpickle as pickle
from accelerate.commands.launch import (  # type: ignore[import-untyped]
    launch_command,
    launch_command_parser,
)

from zenml.logger import get_logger
from zenml.steps import BaseStep
from zenml.utils.function_utils import _cli_arg_name, create_cli_wrapped_script

logger = get_logger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


def run_with_accelerate(
    step_function: BaseStep,
    num_processes: Optional[int] = None,
    use_cpu: bool = False,
) -> BaseStep:
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
        step_function: The step function to run.
        num_processes: The number of processes to use.
        use_cpu: Whether to use the CPU.

    Returns:
        The accelerate-enabled version of the step.
    """

    def _decorator(entrypoint: F) -> F:
        @functools.wraps(entrypoint)
        def inner(*args: Any, **kwargs: Any) -> Any:
            if args:
                raise ValueError(
                    "Accelerated steps do not support positional arguments."
                )

            if not use_cpu:
                import torch

                logger.info("Starting accelerate job...")

                device_count = torch.cuda.device_count()
                if num_processes is None:
                    _num_processes = device_count
                else:
                    if num_processes > device_count:
                        logger.warning(
                            f"Number of processes ({num_processes}) is greater than "
                            f"the number of available GPUs ({device_count}). Using all GPUs."
                        )
                        _num_processes = device_count
                    else:
                        _num_processes = num_processes
            else:
                _num_processes = num_processes or 1

            with create_cli_wrapped_script(
                entrypoint, flavour="accelerate"
            ) as (
                script_path,
                output_path,
            ):
                commands = ["--num_processes", str(_num_processes)]
                if use_cpu:
                    commands += [
                        "--cpu",
                        "--num_cpu_threads_per_process",
                        "10",
                    ]
                commands.append(str(script_path.absolute()))
                for k, v in kwargs.items():
                    k = _cli_arg_name(k)
                    if isinstance(v, bool):
                        if v:
                            commands.append(f"--{k}")
                    elif isinstance(v, str):
                        commands += [f"--{k}", f'"{v}"']
                    elif type(v) in (list, tuple, set):
                        for each in v:
                            commands.append(f"--{k}")
                            if isinstance(each, str):
                                commands.append(f'"{each}"')
                            else:
                                commands.append(f"{each}")
                    else:
                        commands += [f"--{k}", f"{v}"]

                logger.debug(commands)

                parser = launch_command_parser()
                args = parser.parse_args(commands)
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

    setattr(step_function, "entrypoint", _decorator(step_function.entrypoint))

    return step_function
