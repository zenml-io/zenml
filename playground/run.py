from playground.annotations import Input, Output, Param, Step
from playground.artifacts import CSVArtifact
from playground.pipelines.simple_pipeline import SimplePipeline
from playground.steps.simple_step import SimpleStep


# A basic Pipeline, which runs all steps locally

@SimpleStep
def SplitStep(input_data: Input[CSVArtifact],
              output_data: Output[CSVArtifact],
              split_map: Param[float]):
    data = input_data.read()
    split_map = None
    output_data.write(data)


@SimpleStep
def PreprocesserStep(input_data: Input[CSVArtifact],
                     output_data: Output[CSVArtifact],
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

@SimpleStep
def DistSplitStep(input_data: Input[CSVArtifact],
                  output_data: Output[CSVArtifact],
                  split_map: Param[float]):
    import apache_beam as beam

    with beam.Pipeline() as p:
        result = (p
                  | 'ReadData' >> input_data.read()
                  | 'Split' >> beam.Map(lambda x: x)
                  | 'WriteData' >> output_data.write())


@SimpleStep
def DistPreprocesserStep(input_data: Input[CSVArtifact],
                         output_data: Output[CSVArtifact],
                         param: Param[float]):
    import apache_beam as beam

    with beam.Pipeline() as p:
        result = (p
                  | 'ReadData' >> input_data.read()
                  | 'Split' >> beam.Map(lambda x: x)
                  | 'WriteData' >> output_data.write())


@SimplePipeline
def DistSplitPipeline(input_artifact: Input[CSVArtifact],
                      split_step: Step[SplitStep],
                      preprocesser_step: Step[PreprocesserStep]):
    split_step(input_data=input_artifact)
    preprocesser_step(input_data=split_step.outputs.output_data)


# Pipeline
dist_split_pipeline = DistSplitPipeline(
    # TODO: implement the with backend
    input_artifact=CSVArtifact(),
    split_step=SplitStep(split_map=0.6).with_backend({"some_params"}),
    preprocesser_step=PreprocesserStep(param=1.0).with_backend({"some_params"})
)

dist_split_pipeline.run()
