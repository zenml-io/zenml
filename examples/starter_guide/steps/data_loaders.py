# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2023. All rights reserved.
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
from typing import List

import pandas as pd
from sklearn.datasets import (
    load_breast_cancer,
    load_iris,
    load_wine,
)
from sklearn.model_selection import train_test_split

from zenml.enums import StrEnum
from zenml.logger import get_logger
from zenml.steps import (
    BaseParameters,
    Output,
    step,
)

logger = get_logger(__name__)


class SklearnDataset(StrEnum):
    """Built-in scikit-learn datasets."""

    wine = "wine"
    iris = "iris"
    breast_cancer = "breast_cancer"


class DataLoaderStepParameters(BaseParameters):
    """Parameters for the data loader step.

    This is an example of how to use step parameters to make your data loader
    step configurable independently of the step code. This is useful for example
    if you want to load different datasets or different versions of the same
    dataset in your pipeline without having to change the step code.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # The name of the built-in scikit-learn dataset to load.
    dataset: SklearnDataset = SklearnDataset.wine
    ### YOUR CODE ENDS HERE ###

    class Config:
        """Pydantic config class.

        This is used to configure the behavior of Pydantic, the library used to
        parse and validate step parameters. See the documentation for more
        information:

            https://pydantic-docs.helpmanual.io/usage/model_config/

        It is recommended to explicitly forbid extra parameters here to ensure
        that the step parameters are always valid.
        """

        extra = "forbid"


@step
def data_loader(
    params: DataLoaderStepParameters,
) -> pd.DataFrame:
    """Data loader step.

    This is an example of a data loader step that is usually the first step
    in your pipeline. It reads data from an external source like a file,
    database or 3rd party library, then formats it and returns it as an step
    output artifact.

    This step is parameterized using the `DataLoaderStepParameters` class, which
    allows you to configure the step independently of the step code, before
    running it in a pipeline. In this example, the step can be configured to
    load different built-in scikit-learn datasets. See the documentation for
    more information:

        https://docs.zenml.io/starter-guide/pipelines/parameters-and-caching

    Data loader steps should have caching disabled if they are not deterministic
    (i.e. if they data they load from the external source can be different when
    they are subsequently called, even if the step code and parameter values
    don't change).

    Args:
        params: Parameters for the data loader step.

    Returns:
        The loaded dataset artifact.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Load the dataset indicated in the step parameters and format it as a
    # pandas DataFrame
    if params.dataset == SklearnDataset.wine:
        dataset = load_wine(as_frame=True).frame
    elif params.dataset == SklearnDataset.iris:
        dataset = load_iris(as_frame=True).frame
    elif params.dataset == SklearnDataset.breast_cancer:
        dataset = load_breast_cancer(as_frame=True).frame
    elif params.dataset == SklearnDataset.diabetes:
        dataset = load_diabetes(as_frame=True).frame
    logger.info(f"Loaded dataset {params.dataset.value}: %s", dataset.info())
    logger.info(dataset.head())
    ### YOUR CODE ENDS HERE ###

    return dataset


class DataProcessorStepParameters(BaseParameters):
    """Parameters for the data processor step.

    This is an example of how to use step parameters to make your data processor
    step configurable independently of the step code. This is useful for example
    if you want to change the way your process data in your pipeline without
    having to change the step code.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Whether to drop rows with missing values.
    drop_na: bool = True
    # Columns to drop from the dataset.
    drop_columns: List[str] = []
    # Whether to normalize the data.
    normalize: bool = True
    ### YOUR CODE ENDS HERE ###

    class Config:
        """Pydantic config class.

        This is used to configure the behavior of Pydantic, the library used to
        parse and validate step parameters. See the documentation for more
        information:

            https://pydantic-docs.helpmanual.io/usage/model_config/

        It is recommended to explicitly forbid extra parameters here to ensure
        that the step parameters are always valid.
        """

        extra = "forbid"


@step
def data_processor(
    params: DataProcessorStepParameters,
    dataset: pd.DataFrame,
) -> pd.DataFrame:
    """Data processor step.

    This is an example of a data processor step that prepares the data so that
    it is suitable for model training. It takes in a dataset as an input step
    artifact and performs any necessary preprocessing steps like cleaning,
    feature engineering, feature selection, etc. It then returns the processed
    dataset as an step output artifact.

    This step is parameterized using the `DataProcessorStepParameters` class,
    which allows you to configure the step independently of the step code,
    before running it in a pipeline. In this example, the step can be configured
    to perform or skip different preprocessing steps (e.g. dropping rows with
    missing values, dropping columns, normalizing the data, etc.). See the
    documentation for more information:

        https://docs.zenml.io/starter-guide/pipelines/parameters-and-caching

    Args:
        params: Parameters for the data processor step.
        dataset: The dataset artifact to process.

    Returns:
        The processed dataset artifact.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    if params.drop_na:
        # Drop rows with missing values
        dataset = dataset.dropna()
    if params.drop_columns:
        # Drop columns
        dataset = dataset.drop(columns=params.drop_columns)
    if params.normalize:
        # Normalize the data
        target = dataset.pop("target")
        dataset = (dataset - dataset.mean()) / dataset.std()
        dataset["target"] = target
    ### YOUR CODE ENDS HERE ###

    return dataset


class DataSplitterStepParameters(BaseParameters):
    """Parameters for the data splitter step.

    This is an example of how to use step parameters to make your data splitter
    step configurable independently of the step code. This is useful for example
    if you want to change the ratio for the data split or if you want to
    control the random seed used for the split without having to change the step
    code.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # The proportion of the dataset to include in the test split.
    test_size: float = 0.2
    # The random seed to use for the split.
    random_state: int = 42
    # Whether to shuffle the dataset before splitting.
    shuffle: bool = True
    # Whether to stratify the split.
    stratify: bool = True
    ### YOUR CODE ENDS HERE ###

    class Config:
        """Pydantic config class.

        This is used to configure the behavior of Pydantic, the library used to
        parse and validate step parameters. See the documentation for more
        information:

            https://pydantic-docs.helpmanual.io/usage/model_config/

        It is recommended to explicitly forbid extra parameters here to ensure
        that the step parameters are always valid.
        """

        extra = "forbid"


@step
def data_splitter(
    params: DataSplitterStepParameters,
    dataset: pd.DataFrame,
) -> Output(train_set=pd.DataFrame, test_set=pd.DataFrame,):
    """Data splitter step.

    This is an example of a data splitter step that splits the dataset into
    training and dev subsets to be used for model training and evaluation. It
    takes in a dataset as an step input artifact and returns the training and
    dev subsets as two separate step output artifacts.

    Data splitter steps should have a deterministic behavior, i.e. they should
    use a fixed random seed and always return the same split when called with
    the same input dataset. This is to ensure reproducibility of your pipeline
    runs.

    This step is parameterized using the `DataSplitterStepParameters` class,
    which allows you to configure the step independently of the step code,
    before running it in a pipeline. In this example, the step can be configured
    to use a different random seed, change the split ratio, or control whether
    to shuffle or stratify the split. See the documentation for more
    information:

        https://docs.zenml.io/starter-guide/pipelines/parameters-and-caching

    Args:
        params: Parameters for the data splitter step.
        dataset: The dataset to split.

    Returns:
        The resulting training and dev subsets.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Split the dataset into training and dev subsets
    train_set, test_set = train_test_split(
        dataset,
        test_size=params.test_size,
        shuffle=params.shuffle,
        stratify=dataset["target"] if params.stratify else None,
        random_state=params.random_state,
    )
    ### YOUR CODE ENDS HERE ###

    return train_set, test_set


@step
def simple_data_splitter(
    dataset: pd.DataFrame,
) -> Output(train_set=pd.DataFrame, test_set=pd.DataFrame):
    """Load and split a dataset."""
    # Load the wine dataset
    dataset = load_wine(as_frame=True).frame

    # Split the dataset into training and dev subsets
    train_set, test_set = train_test_split(
        dataset,
    )
    return train_set, test_set
