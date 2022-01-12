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

import mlflow  # type: ignore
from mlflow import set_experiment
from mlflow.tracking import set_tracking_uri  # type: ignore

from zenml.io.utils import get_global_config_directory
from zenml.pipelines.base_pipeline import BasePipeline
from zenml.steps import BaseStep


def local_mlflow_backend() -> str:
    """Returns the local mlflow backend inside the global zenml directory"""
    local_mlflow_backend_uri = os.path.join(
        get_global_config_directory(), "local_stores", "mlruns"
    )
    if not os.path.exists(local_mlflow_backend_uri):
        os.makedirs(local_mlflow_backend_uri)
        # TODO [medium]: safely access (possibly non-existent) artifact stores
    return "file:" + local_mlflow_backend_uri


def setup_mlflow(
    backend_store_uri: Optional[str] = None, experiment_name: str = "default"
) -> None:
    """Setup all mlflow related configurations. This includes specifying which
    mlflow tracking uri should b e used and which experiment the tracking
    will be associated with.

    Args:
        backend_store_uri: The mlflow backend to log to
        experiment_name: The experiment name under which all runs will be
                         tracked

    """
    # TODO [ENG-316]: Implement a way to get the mlflow token and set
    #  it as env variable at MLFLOW_TRACKING_TOKEN
    if not backend_store_uri:
        backend_store_uri = local_mlflow_backend()

    set_tracking_uri(backend_store_uri)
    # Set which experiment is used within mlflow
    set_experiment(experiment_name)


def enable_mlflow_init(
    original_init: Callable[[BasePipeline, BaseStep, Any], None],
    experiment: Optional[str] = None,
) -> Callable[..., None]:
    """Outer decorator function for extending the __init__ method for pipelines
    that should be run using mlflow

    Args:
        original_init: The __init__ method that should be extended
        experiment: The users chosen experiment name to use for mlflow

    Returns:
        the inner decorator which extends the __init__ method
    """

    def inner_decorator(
        self: BasePipeline, *args: BaseStep, **kwargs: Any
    ) -> None:
        """Inner decorator overwriting the pipeline __init__
        Makes sure mlflow is properly set up and all mlflow logging takes place
        within one mlflow experiment that is associated with the pipeline
        """
        original_init(self, *args, **kwargs)
        setup_mlflow(
            backend_store_uri=local_mlflow_backend(),
            experiment_name=experiment if experiment else self.name,
        )

    return inner_decorator


def enable_mlflow_run(run: Callable[..., Any]) -> Callable[..., Any]:
    """Outer decorator function for extending the run method for pipelines
    that should be run using mlflow

    Args:
        run: The run method that should be extended

    Returns:
        the inner decorator which extends the run method
    """

    def inner_decorator(
        self: BasePipeline, run_name: Optional[str] = None
    ) -> Any:
        """Inner decorator used to extend the run method of a pipeline.
        This ensures each pipeline run is run within a different mlflow context.

        Args:
            self: self of the original pipeline class
            run_name: Optional name for the run.
        """
        with mlflow.start_run(run_name=run_name):
            run(self, run_name)

    return inner_decorator


def enable_mlflow(
    _pipeline: Type[BasePipeline], experiment_name: Optional[str] = None
) -> Type[BasePipeline]:
    """Outer decorator function for the creation of a ZenML pipeline with mlflow
    tracking enabled.

    In order for a pipeline to run within the context of mlflow, the mlflow
    experiment should be associated with the pipeline directly. Each separate
    pipeline run needs to be associated directly with a pipeline run. For this,
    the __init__ and run method need to be extended accordingly.

    Args:
        _pipeline: The decorated pipeline
        experiment_name: Experiment name to use for mlflow

    Returns:
        the inner decorator which has a pipeline with the two methods extended
    """

    def inner_decorator(pipeline: Type[BasePipeline]) -> Type[BasePipeline]:
        """Inner decorator function for the creation of a ZenML Pipeline with
        mlflow

        The __init__ and run method are both extended.

        Args:
          pipeline: BasePipeline which will be extended

        Returns:
            the class of a newly generated ZenML Pipeline with mlflow

        """
        return type(  # noqa
            pipeline.__name__,
            (pipeline,),
            {
                "__init__": enable_mlflow_init(
                    pipeline.__init__, experiment_name
                ),
                "run": enable_mlflow_run(pipeline.run),
            },
        )

    return inner_decorator(_pipeline)
