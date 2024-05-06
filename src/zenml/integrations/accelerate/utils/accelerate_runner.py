import subprocess
from typing import Callable, Optional, TypeVar

from zenml.logger import get_logger
from zenml.utils.function_utils import _cli_arg_name, create_cli_wrapped_script

logger = get_logger(__name__)
F = TypeVar("F", bound=Callable[..., None])


def run_with_accelerate(
    function: F, num_processes: Optional[int] = None, **function_kwargs
) -> None:
    logger.info("Starting accelerate job...")
    if num_processes is None:
        import torch

        num_processes = torch.cuda.device_count()

    script_path = create_cli_wrapped_script(function)

    command = f"accelerate launch --num_processes {num_processes} "
    command += script_path + " "
    for k, v in function_kwargs.items():
        k = _cli_arg_name(k)
        if type(v) == bool:
            if v:
                command += f"--{k} "
        elif type(v) == str:
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
