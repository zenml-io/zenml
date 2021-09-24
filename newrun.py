import pandas as pd

from zenml import pipelines
from zenml import steps
from zenml.annotations import External, Input, Step, Param
from zenml.annotations.artifact_annotations import BeamOutput
from zenml.artifacts.data_artifacts.text_artifact import TextArtifact

from zenml.io import gcs_plugin


# TODO: [MEDIUM] change the naming of the decorator
# TODO: [MEDIUM] change the naming of the external to input

@steps.SimpleStep
def DistSplitStep(text_artifact: Input[TextArtifact],
                  param: Param[float] = 3.0,
                  ) -> BeamOutput[TextArtifact]:
    import apache_beam as beam

    pipeline = beam.Pipeline()
    data = text_artifact.read_with_beam(pipeline)
    result = data | beam.Map(lambda x: x)

    return (result, pipeline)


@steps.SimpleStep
def InMemPreprocessorStep(text_artifact: Input[TextArtifact]
                          ) -> pd.DataFrame:
    data = text_artifact.read_with_pandas()
    return data


@pipelines.SimplePipeline
def SplitPipeline(text_artifact: External[TextArtifact],
                  split_step: Step[DistSplitStep],
                  preprocessor_step: Step[InMemPreprocessorStep]):
    split_artifact = split_step(text_artifact=text_artifact)
    _ = preprocessor_step(text_artifact=split_artifact)


# Pipeline
example_text_artifact = TextArtifact()
example_text_artifact.uri = "PLACEHOLDER"

dist_split_pipeline = SplitPipeline(
    text_artifact=example_text_artifact,
    split_step=DistSplitStep(param=0.1),
    preprocessor_step=InMemPreprocessorStep()
)

dist_split_pipeline.run()
