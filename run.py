import os

import pandas as pd

from zenml import step, pipeline
from zenml.annotations import Input, Step, Param
from zenml.annotations.artifact_annotations import BeamOutput
from zenml.artifacts.data_artifacts.text_artifact import TextArtifact


@step
def DataIngestionStep(uri: Param[str]
                      ) -> Output[PandasArtifact]:
    return pd.read_csv(uri)


@step
def DistSplitStep(text_artifact: Input[TextArtifact],
                  ) -> BeamOutput[TextArtifact]:
    import apache_beam as beam

    pipeline = beam.Pipeline()
    data = text_artifact.read_with_beam(pipeline)
    result = data | beam.Map(lambda x: x)

    return (result, pipeline)


@step
def InMemPreprocesserStep(text_artifact: Input[TextArtifact]
                          ) -> pd.DataFrame:
    data = text_artifact.read_with_pandas()
    return data


@pipeline
def SplitPipeline(data_step: Step[DataIngestionStep],
                  split_step: Step[DistSplitStep],
                  preprocesser_step: Step[InMemPreprocesserStep]):
    text_artifact = data_step()
    split_artifact = split_step(text_artifact=text_artifact)
    _ = preprocesser_step(text_artifact=split_artifact)


# Pipeline
DATA_PATH = os.getenv("ZENML_DATA")

split_pipeline = SplitPipeline(
    data_step=DataIngestionStep(uri=DATA_PATH),
    split_step=DistSplitStep(),
    preprocesser_step=InMemPreprocesserStep())

split_pipeline.run()