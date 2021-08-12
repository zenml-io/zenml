from playground.artifacts.data_artifacts import CSVArtifact
from playground.datasources.csv_datasource import CSVDatasource
from playground.pipelines.base_pipeline import Step, Datasource
from playground.pipelines.simple_pipeline import SimplePipeline
from playground.steps.base_step import Input, Output, Param
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
def SplitPipeline(datasource: Datasource[CSVDatasource],
                  split_step: Step[SplitStep],
                  preprocesser_step: Step[PreprocesserStep]):
    split_step(input_data=datasource)
    preprocesser_step(input_data=split_step.outputs.output_data)


# Pipeline
split_pipeline = SplitPipeline(
    datasource=CSVDatasource("local_test/data/data.csv"),
    split_step=SplitStep(split_map=0.6),
    preprocesser_step=PreprocesserStep(param=1.0)
)

split_pipeline.run()
