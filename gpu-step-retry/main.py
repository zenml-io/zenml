from zenml import pipeline, step
import pandas as pd
import torch
from zenml.config.docker_settings import DockerSettings
from zenml.config.retry_config import StepRetryConfig
from zenml.logger import get_logger
logger = get_logger(__name__)
from zenml.types import CSVString

import os



################## Steps ####################

@step(
        retry=StepRetryConfig(
            max_retries=3,
            delay=10,
            backoff=2,
        )
)
def my_step() -> CSVString:
    some_csv = "a,b,c\n1,2,3"
    return CSVString(some_csv)

@step
def step_1() -> str:
    logger.info("My logs from step_1")
    if torch.cuda.is_available():
        return "gpu"
    else:
        return "cpu"

@step
def step_2(input_one: str, input_two: str) -> None:
    logger.info(f"{torch.cuda.device_count()}")
    logger.info(f"{input_one} {input_two}")
    logger.info("My logs from step_2")

    
@step(
        retry=StepRetryConfig(
            max_retries=3,
            delay=10,
            backoff=2,
        )
)
def step_3() -> None:
    raise Exception("This is a test exception")
    logger.info("THANK YOU. BYE2")
    
################## Piepline ##################


@pipeline(
    settings={
        "docker": DockerSettings(
            requirements="requirements.txt"
        )
    }
)
def my_pipeline():
    my_step()
    output_step_one = step_1()
    _ = step_2(input_one="hello", input_two=output_step_one)
    step_3()

##############################################


if __name__ == "__main__":
    config_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'configs')
    pipeline_args = {"config_path": os.path.join(config_folder, "run_config.yaml")}
    my_pipeline.with_options(**pipeline_args)()