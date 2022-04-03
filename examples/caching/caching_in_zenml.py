#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import argparse
import random
import time

from rich.console import Console
from rich.markdown import Markdown

from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, Output, step

console = Console()


@step
def create_data() -> Output(random_data=float):
    """Create an array of random data 0 <= elements <= 1. 
    
    Returns:
        Random float between 0 and 1
    """
    random_data = random.random()
    return random_data


class TransformerConfig(BaseStepConfig):
    """Transformer params

    Params:
        subtrahend - Amount to be subtracted from the input_data array
    """

    subtrahend: float = 0.5


@step
def transform_data(
    config: TransformerConfig,
    random_data: float
) -> Output(transformed_data=float):
    """Subtract subtrahend from random_data - we added a sleep in this function to simulate a
    complex data transformation step
    
    Args:
        config - TransformerConfig that specifies the subtrahend for the transformer
        random_data - random data to be transformed
        
    Returns:
        The random_data minus the subtrahend specified in the config
    """
    time.sleep(10)

    transformed_data = random_data - config.subtrahend
    return transformed_data


@step
def print_data(
    transformed_data: float
) -> None:
    """Print resulting data array"""
    console.print(
        f"The pipeline produced the following number: {transformed_data}",
        style="bold red")


@pipeline
def transformer_pipeline(
    create_data,
    transform_data,
    print_data
):
    # Define how data flows through the steps of the pipeline
    rand_arr = create_data()
    transformed_arr = transform_data(rand_arr)
    print_data(transformed_arr)


if __name__ == "__main__":

    config_subtrahend = random.random()

    console.print('[u]First Pipeline Run[/u] \n \n')
    # Define which step functions implement the pipeline steps and create
    #  a pipeline instance
    pipeline_instance = transformer_pipeline(
        create_data=create_data(),
        transform_data=transform_data(
            TransformerConfig(subtrahend=config_subtrahend)),
        print_data=print_data()
    )
    pipeline_instance.run()

    console.print('\n \n [u]Second Pipeline Run[/u] \n \n')
    # Define which step functions implement the pipeline steps and create
    #  a pipeline instance
    pipeline_instance_2 = transformer_pipeline(
        create_data=create_data(),
        transform_data=transform_data(
            TransformerConfig(subtrahend=config_subtrahend)),
        print_data=print_data()
    )
    pipeline_instance_2.run()

    console.print("If you ran this notebook for the first time, the first "
                  "pipeline run should have taken significantly longer than "
                  "the second run. In the second run none of the steps "
                  "were run as the cached values could be taken for every "
                  "step.")

    console.print("!!! **Note**: The last step of the second pipeline also did "
                  "not run. This means we have no printout of the resulting "
                  "value. This is one of those times were caching is not "
                  "desired. We'll have to disable cache for the last step for"
                  " the pipeline to behave as expected. Find out how to do "
                  "this and many more things below.", style="red")

    MARKDOWN = """
    ### 1. Disable caching on a step level using the **step decorator**:

    ```python
    @step(enable_cache=False)
    ```
    
    ### 2. Disable caching for the whole pipeline through the 
    **pipeline decorator**:
    
    ```python
    @pipeline(enable_cache=False)
    ```
    
    ### 3. Invalidate cache by **changing the code** within a step
    
    Make a change in any piece of code within a step and the cache for that 
    step will be invalidated.
    
    For example replace the create_data code with this one:
    
    ```python
    @step
    def create_data() -> Output(random_data=float):
        '''Create an array of random data 0 <= elements <= 1. 
    
        Returns:
            Random float between 0 and 1
        '''
        different_var_name = random.random()
        return different_var_name
    ```
    
    
    ### 4. Invalidate cache by changing a parameter within the 
    **step configuration**
    
    For example you could change the subtrahend in the TransformerConfig of the 
    second pipeline instance
    
    ```python
    pipeline_instance_2 = transformer_pipeline(
        create_data = create_data(),
        transform_data = transform_data(TransformerConfig(subtrahend=0.8)),
        print_data = print_data()
    )
    ```
    
    ### 5. Disable cache explicitly in the **runtime configuration**
    
    ```python
    pipeline_instance_2.run(enable_cache=False)
    ```
    """
    md = Markdown(MARKDOWN)

    console.print(md)
