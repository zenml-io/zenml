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

from zenml import pipeline, step
from zenml.annotations import Input, Param, Step, Output
from zenml.artifacts.data_artifacts.text_artifact import TextArtifact


@step(name="data_ingest")
def DataIngestionStep(uri: Param[str],
                      output_artifact: Output[TextArtifact]):
    import pandas as pd
    df = pd.read_csv(uri)
    output_artifact.write_with_pandas(df)


@step(name="split")
def DistSplitStep(input_artifact: Input[TextArtifact],
                  output_artifact: Output[TextArtifact]):
    import apache_beam as beam

    with beam.Pipeline() as p:
        _ = (p
             | input_artifact.read_with_beam()
             | output_artifact.write_with_beam())


@step(name="preprocessing")
def InMemPreprocesserStep(input_artifact: Input[TextArtifact],
                          output_artifact: Output[TextArtifact]):
    data = input_artifact.read_with_pandas()
    output_artifact.write_with_pandas(data)


@pipeline(name="my_pipeline")
def SplitPipeline(
        data_step: Step[DataIngestionStep],
        split_step: Step[DistSplitStep],
        preprocesser_step: Step[InMemPreprocesserStep],
):
    split_step.connect_inputs(
        text_artifact=data_step.outputs.output_artifact,
    )

    preprocesser_step.connect_inputs(
        text_artifact=split_step.outputs.output_artifact,
    )


# Pipeline
split_pipeline = SplitPipeline(
    data_step=DataIngestionStep(uri=os.getenv("ZENML_DATA")),
    split_step=DistSplitStep(),
    preprocesser_step=InMemPreprocesserStep(),
)

DAG = split_pipeline.run()
