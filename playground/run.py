from playground.annotations import Input, Output, Param, Step
from playground.artifacts.data_artifacts import CSVArtifact
from playground.pipelines.simple_pipeline import SimplePipeline
from playground.steps.simple_step import SimpleStep


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

split_pipeline.run()
