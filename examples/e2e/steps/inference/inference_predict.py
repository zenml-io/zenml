# 


from typing import Optional

import pandas as pd
from typing_extensions import Annotated
from zenml import get_step_context, step, ArtifactConfig
from zenml.integrations.mlflow.services.mlflow_deployment import MLFlowDeploymentService
from zenml.logger import get_logger

from constants import DATA_CLASSIFICATION

logger = get_logger(__name__)


@step
def inference_predict(
    dataset_inf: pd.DataFrame,
) -> Annotated[pd.Series, ArtifactConfig(name="predictions", tags=[DATA_CLASSIFICATION])]:
    """Predictions step.

    This is an example of a predictions step that takes the data in and returns
    predicted values.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured to use different input data.
    See the documentation for more information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        dataset_inf: The inference dataset.

    Returns:
        The predictions as pandas series
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    model = get_step_context().model

    # run prediction from memory
    predictor = model.load_artifact("model")
    predictions = predictor.predict(dataset_inf)

    predictions = pd.Series(predictions, name="predicted")
    ### YOUR CODE ENDS HERE ###

    return predictions
