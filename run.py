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

from zenml import pipeline
from zenml.annotations import Input, Output, Param, Step
from zenml.artifacts.data_artifacts.text_artifact import TextArtifact
from zenml.steps import step


@step(name="SimplestStepEver")
def SimplestStepEver(basic_param_1: int, basic_param_2: str) -> int:
    return basic_param_1 + int(basic_param_2)


@step(name="data_ingest")
def DataIngestionStep(uri: Param[str], output_artifact: Output[TextArtifact]):
    import pandas as pd

    df = pd.read_csv(uri)
    output_artifact.write_with_pandas(df)


@step(name="split")
def DistSplitStep(
    input_artifact: Input[TextArtifact], output_artifact: Output[TextArtifact]
):
    import apache_beam as beam

    with beam.Pipeline() as p:
        _ = (
            p
            | input_artifact.read_with_beam()
            | output_artifact.write_with_beam()
        )


@step(name="preprocessing")
def InMemPreprocesserStep(
    input_artifact: Input[TextArtifact], output_artifact: Output[TextArtifact]
):
    data = input_artifact.read_with_pandas()
    output_artifact.write_with_pandas(data)


@pipeline(name="my_pipeline")
def SplitPipeline(
    simple_step: Step[SimplestStepEver],
    data_step: Step[DataIngestionStep],
    split_step: Step[DistSplitStep],
    preprocesser_step: Step[InMemPreprocesserStep],
):
    split_step.set_inputs(
        input_artifact=data_step.get_outputs()["output_artifact"],
    )

    preprocesser_step.set_inputs(
        input_artifact=split_step.get_outputs()["output_artifact"],
    )


# Pipeline
split_pipeline = SplitPipeline(
    simple_step=SimplestStepEver(basic_param_1=2, basic_param_2="3"),
    data_step=DataIngestionStep(uri=os.getenv("test_data")),
    split_step=DistSplitStep(),
    preprocesser_step=InMemPreprocesserStep(),
)

DAG = split_pipeline.run()
