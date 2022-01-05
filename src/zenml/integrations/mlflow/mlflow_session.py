#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import os
from typing import Any, Callable, Optional, Type

import mlflow
from mlflow import set_experiment
from mlflow.tracking import set_tracking_uri

from zenml.io.utils import get_global_config_directory
from zenml.pipelines.base_pipeline import BasePipeline
from zenml.steps import BaseStep


def setup_mlflow(experiment_name: str = "default") -> None:
    zenml_mlruns_path = os.path.join(get_global_config_directory(), "mlruns")
    if not os.path.exists(zenml_mlruns_path):
        os.mkdir(zenml_mlruns_path)
    set_tracking_uri(zenml_mlruns_path)

    set_experiment(experiment_name)


def enable_mlflow_init(f: Type[Callable]) -> Type[Callable]:
    def inner_decorator(self, *args: BaseStep, **kwargs: Any) -> None:
        f(self, *args, **kwargs)
        setup_mlflow()
        mlflow.set_experiment(self.name)

    return inner_decorator


def enable_mlflow_run(f: Type[Callable]) -> Type[Callable]:
    def inner_decorator(self, run_name: Optional[str] = None) -> Any:
        with mlflow.start_run(run_name=run_name):
            f(self, run_name)

    return inner_decorator


def enable_mlflow(_pipeline: Type[BasePipeline]) -> Type[BasePipeline]:
    def inner_decorator(pipeline: Type[BasePipeline]) -> Type[BasePipeline]:
        return type(  # noqa
            pipeline.__name__,
            (pipeline,),
            {
                "__init__": enable_mlflow_init(pipeline.__init__),
                "run": enable_mlflow_run(pipeline.run),
            },
        )

    return inner_decorator(_pipeline)
