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

from zenml.pipelines import pipeline


@pipeline()
def simple_training_pipeline(
    data_loader,
    model_trainer,
):
    """
    Model training pipeline recipe.

    This is a recipe for a pipeline that loads the data, processes it and
    splits it into train and test sets, then trains and evaluates a model
    on it. It is agnostic of the actual step implementations and just defines
    how the artifacts are circulated through the steps by calling them in the
    right order and passing the output of one step as the input of the next
    step.

    The arguments that this function takes are instances of the steps that
    are defined in the steps folder. Also note that the arguments passed to
    the steps are step artifacts. If you use step parameters to configure the
    steps, they must not be used here, but instead be used when the steps are
    instantiated, before this function is called.

    Args:
        data_loader: A data loader step instance that outputs a dataset.
        model_trainer: A model trainer step instance that takes a train set
            as input and outputs a trained model.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Link all the steps together by calling them and passing the output
    # of one step as the input of the next step.
    train_set, test_set = data_loader()
    _ = model_trainer(train_set=train_set, test_set=test_set)
    ### YOUR CODE ENDS HERE ###
