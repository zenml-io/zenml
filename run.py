import pandas as pd

from zenml import pipelines
from zenml import steps
from zenml.annotations import External, Input, Step
from zenml.artifacts import TextArtifact
from zenml.distributed.beam import BeamOutput


@steps.SimpleStep
def DistSplitStep(input_data: Input[TextArtifact]
                  ) -> BeamOutput[TextArtifact]:
    import apache_beam as beam

    with beam.Pipeline() as pipeline:
        data = input_data.read_with_beam(pipeline)
        result = data | beam.Map(lambda x: x)

    return result


@steps.SimpleStep
def InMemPreprocesserStep(input_data: Input[TextArtifact]) -> pd.DataFrame:
    data = input_data.read_with_pandas()
    return data


@pipelines.SimplePipeline
def SplitPipeline(
        input_artifact: External[TextArtifact],
        split_step: Step[DistSplitStep],
        preprocesser_step: Step[InMemPreprocesserStep],
):
    split_data = split_step(input_data=input_artifact)
    processed_data = preprocesser_step(input_data=split_data)


# Pipeline
test_artifact = TextArtifact()
test_artifact.uri = "/home/baris/zenml/zenml/zenml/local_test/data/data.csv"

dist_split_pipeline = SplitPipeline(
    input_artifact=test_artifact,
    split_step=DistSplitStep(),
    preprocesser_step=InMemPreprocesserStep()
)

dist_split_pipeline.run()
