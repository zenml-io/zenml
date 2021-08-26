from playground.annotations import Input, Output, Param, Step
from playground.artifacts.data_artifacts.csv_data_artifact import \
    BeamCSVArtifact, PandasCSVArtifact
from playground.pipelines.simple_pipeline import SimplePipeline
from playground.steps.simple_step import SimpleStep


# A basic Pipeline, which runs all steps locally

@SimpleStep
def SplitStep(input_data: Input[PandasCSVArtifact],
              output_data: Output[PandasCSVArtifact],
              split_map: Param[float]):
    data = input_data.read()
    split_map = None
    output_data.write(data)


@SimpleStep
def PreprocesserStep(input_data: Input[PandasCSVArtifact],
                     output_data: Output[PandasCSVArtifact],
                     param: Param[float]):
    data = input_data.read()
    param = None
    output_data.write(data)


@SimplePipeline
def SplitPipeline(split_step: Step[SplitStep],
                  preprocesser_step: Step[PreprocesserStep]):
    split_step()
    preprocesser_step(input_data=split_step.outputs.output_data)


# Pipeline
split_pipeline = SplitPipeline(
    split_step=SplitStep(split_map=0.6),
    preprocesser_step=PreprocesserStep(param=1.0)
)

# split_pipeline.run()

# A distributed Pipeline, which runs on Beam
import apache_beam as beam


@SimpleStep
def DistSplitStep(input_data: Input[BeamCSVArtifact],
                  output_data: Output[BeamCSVArtifact],
                  split_map: Param[float]):
    with beam.Pipeline() as p:
        result = (p
                  | 'ReadData' >> input_data.read()
                  | 'Split' >> beam.Map(lambda x: x)
                  | 'WriteData' >> output_data.write())


@SimpleStep
def DistPreprocesserStep(input_data: Input[BeamCSVArtifact],
                         output_data: Output[BeamCSVArtifact],
                         param: Param[float]):
    with beam.Pipeline() as p:
        result = (p
                  | 'ReadData' >> input_data.read()
                  | 'Split' >> beam.Map(lambda x: x)
                  | 'WriteData' >> output_data.write())


@SimplePipeline
def DistSplitPipeline(split_step: Step[SplitStep],
                      preprocesser_step: Step[PreprocesserStep]):
    split_step()
    preprocesser_step(input_data=split_step.outputs.output_data)


# Pipeline
dist_split_pipeline = DistSplitPipeline(
    # TODO: implement the with backend
    split_step=SplitStep(split_map=0.6).with_backend(),
    preprocesser_step=PreprocesserStep(param=1.0).with_backend()
)
