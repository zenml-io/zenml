# 


import pandas as pd
from sklearn.pipeline import Pipeline
from typing_extensions import Annotated
from zenml import step, ArtifactConfig

from constants import DATA_CLASSIFICATION


@step
def inference_data_preprocessor(
    dataset_inf: pd.DataFrame,
    preprocess_pipeline: Pipeline,
    target: str,
) -> Annotated[pd.DataFrame, ArtifactConfig(name="inference_dataset", tags=[DATA_CLASSIFICATION])]:
    """Data preprocessor step.

    This is an example of a data processor step that prepares the data so that
    it is suitable for model inference. It takes in a dataset as an input step
    artifact and performs any necessary preprocessing steps based on pretrained
    preprocessing pipeline.

    Args:
        dataset_inf: The inference dataset.
        preprocess_pipeline: Pretrained `Pipeline` to process dataset.
        target: Name of target columns in dataset.

    Returns:
        The processed dataframe: dataset_inf.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # artificially adding `target` column to avoid Pipeline issues
    dataset_inf[target] = pd.Series([1] * dataset_inf.shape[0])
    dataset_inf = preprocess_pipeline.transform(dataset_inf)
    dataset_inf.drop(columns=["target"], inplace=True)
    ### YOUR CODE ENDS HERE ###

    return dataset_inf
