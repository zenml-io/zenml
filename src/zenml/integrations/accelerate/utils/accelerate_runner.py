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
"""Utility function to run Accelerate jobs."""

import subprocess
from typing import Any, Callable, Optional, TypeVar

from zenml.logger import get_logger
from zenml.utils.function_utils import _cli_arg_name, create_cli_wrapped_script

logger = get_logger(__name__)
F = TypeVar("F", bound=Callable[..., None])


def run_with_accelerate(
    function: F, num_processes: Optional[int] = None, **function_kwargs: Any
) -> None:
    """Run a function with accelerate.

    Accelerate package: https://huggingface.co/docs/accelerate/en/index

    Example:
        ```python
        from zenml import step
        from zenml.integrations.accelerate.utils import run_with_accelerate

        def training_function(some_param: int, ...):
            ...

        @step
        def training_step(some_param: int, ...):
            run_with_accelerate(training_function, num_processes=4, some_param=some_param, ...)
        ```

    Args:
        function: The function to run.
        num_processes: The number of processes to use.
        **function_kwargs: The keyword arguments to pass to the function.

    Raises:
        CalledProcessError: If the function fails.
    """
    logger.info("Starting accelerate job...")
    if num_processes is None:
        import torch

        num_processes = torch.cuda.device_count()

    script_path = create_cli_wrapped_script(function)

    command = f"accelerate launch --num_processes {num_processes} "
    command += script_path + " "
    for k, v in function_kwargs.items():
        k = _cli_arg_name(k)
        if isinstance(v, bool):
            if v:
                command += f"--{k} "
        elif isinstance(v, str):
            command += f'--{k} "{v}" '
        elif type(v) in (list, tuple, set):
            for each in v:
                command += f"--{k} {each} "
        else:
            command += f"--{k} {v} "

    logger.info(command)

    result = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    for stdout_line in result.stdout.split("\n"):
        logger.info(stdout_line)
    if result.returncode == 0:
        logger.info("Accelerate training job finished.")
        return
    else:
        logger.error(
            f"Accelerate training job failed. With return code {result.returncode}."
        )
        raise subprocess.CalledProcessError(result.returncode, command)
