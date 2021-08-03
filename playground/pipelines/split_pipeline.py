from playground.annotations import Step, Datasource
from playground.steps.split_step import SplitStep
from playground.steps.preprocesser_step import PreprocesserStep
from playground.datasources.csv_datasource import CSVDatasource


@pipeline
def SplitPipeline(datasource: Datasource[CSVDatasource],
                  split_step: Step[SplitStep],
                  preprocesser_step: Step[PreprocesserStep]):
    split_step(input_data=datasource)
    preprocesser_step(input_data=split_step.outputs.output_data)
