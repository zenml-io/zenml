#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implements a custom model for the Seldon integration."""

import subprocess
from typing import Any, Dict, List, Optional, Union

import click
import numpy as np

from zenml.logger import get_logger
from zenml.utils import source_utils

logger = get_logger(__name__)

DEFAULT_MODEL_NAME = "model"
DEFAULT_LOCAL_MODEL_DIR = "/mnt/models"

Array_Like = Union[np.ndarray[Any, Any], List[Any], str, bytes, Dict[str, Any]]


class ZenMLCustomModel:
    """Custom model class for ZenML and Seldon.

    This class is used to implement a custom model for the Seldon Core integration,
    which is used as the main entry point for custom code execution.

    Attributes:
        name: The name of the model.
        model_uri: The URI of the model.
        predict_func: The predict function of the model.
    """

    def __init__(
        self,
        model_name: str,
        model_uri: str,
        predict_func: str,
    ):
        """Initializes a ZenMLCustomModel object.

        Args:
            model_name: The name of the model.
            model_uri: The URI of the model.
            predict_func: The predict function of the model.
        """
        self.name = model_name
        self.model_uri = model_uri
        self.predict_func = source_utils.load(predict_func)
        self.model = None
        self.ready = False

    def load(self) -> bool:
        """Load the model.

        This function loads the model into memory and sets the ready flag to True.
        The model is loaded using the materializer, by saving the information of
        the artifact to a file at the preparing time and loading it again at the
        prediction time by the materializer.

        Returns:
            True if the model was loaded successfully, False otherwise.

        """
        try:
            from zenml.artifacts.utils import load_model_from_metadata

            self.model = load_model_from_metadata(self.model_uri)
        except Exception as e:
            logger.error("Failed to load model: {}".format(e))
            return False
        self.ready = True
        return self.ready

    def predict(
        self,
        X: Array_Like,
        features_names: Optional[List[str]],
        **kwargs: Any,
    ) -> Array_Like:
        """Predict the given request.

        The main predict function of the model. This function is called by the
        Seldon Core server when a request is received. Then inside this function,
        the user-defined predict function is called.

        Args:
            X: The request to predict in a dictionary.
            features_names: The names of the features.
            **kwargs: Additional arguments.

        Returns:
            The prediction dictionary.

        Raises:
            Exception: If function could not be called.
            NotImplementedError: If the model is not ready.
            TypeError: If the request is not a dictionary.
        """
        if self.predict_func is not None:
            try:
                prediction = {"predictions": self.predict_func(self.model, X)}
            except Exception as e:
                raise Exception("Failed to predict: {}".format(e))
            if isinstance(prediction, dict):
                return prediction
            else:
                raise TypeError(
                    f"Prediction is not a dictionary. Expected dict type but got {type(prediction)}"
                )
        else:
            raise NotImplementedError("Predict function is not implemented")


@click.command()
@click.option(
    "--model_uri",
    default=DEFAULT_LOCAL_MODEL_DIR,
    type=click.STRING,
    help="The directory where the model is stored locally.",
)
@click.option(
    "--model_name",
    default=DEFAULT_MODEL_NAME,
    required=True,
    type=click.STRING,
    help="The name of the model to deploy.",
)
@click.option(
    "--predict_func",
    required=True,
    type=click.STRING,
    help="The path to the custom predict function defined by the user.",
)
def main(model_name: str, model_uri: str, predict_func: str) -> None:
    """Main function for the custom model.

    Within the deployment process, the built-in custom deployment step is used to
    to prepare the Seldon Core deployment with an entry point that calls this script,
    which then starts a subprocess to start the Seldon server and waits for requests.

    The following is an example of the entry point:
    ```
    entrypoint_command = [
        "python",
        "-m",
        "zenml.integrations.seldon.custom_deployer.zenml_custom_model",
        "--model_name",
        config.service_config.model_name,
        "--predict_func",
        config.custom_deploy_parameters.predict_function,
    ]
    ```

    Args:
        model_name: The name of the model.
        model_uri: The URI of the model.
        predict_func: The path to the predict function.
    """
    command = [
        "seldon-core-microservice",
        "zenml.integrations.seldon.custom_deployer.zenml_custom_model.ZenMLCustomModel",
        "--service-type",
        "MODEL",
        "--parameters",
        (
            f'[{{"name":"model_uri","value":"{model_uri}","type":"STRING"}},'
            f'{{"name":"model_name","value":"{model_name}","type":"STRING"}},'
            f'{{"name":"predict_func","value":"{predict_func}","type":"STRING"}}]'
        ),
    ]
    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError as ProcessError:
        logger.error(
            f"Failed to start the seldon-core-microservice process. {ProcessError}"
        )
        return


if __name__ == "__main__":
    main()
