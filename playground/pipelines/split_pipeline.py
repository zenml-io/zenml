# Option 1

from playground.datasources.csv_datasource import CSVDatasource
from playground.steps.preprocesser_step import FunctionPreprocesserStep
from playground.steps.split_step import FunctionSplitStep
from playground.utils.annotations import Step, Datasource
from playground.utils.pipeline_utils import pipeline


@pipeline
def FunctionSplitPipeline(datasource: Datasource[CSVDatasource],
                          split_step: Step[FunctionSplitStep],
                          preprocesser_step: Step[FunctionPreprocesserStep]):
    split_step(input_data=datasource)
    preprocesser_step(input_data=split_step.outputs.output_data)


# Option 2

from playground.pipelines.base_pipeline import BasePipeline


class ClassSplitPipeline(BasePipeline):
    def connect(self,
                datasource: Datasource[CSVDatasource],
                split_step: Step[FunctionSplitStep],
                preprocesser_step: Step[FunctionPreprocesserStep]):
        split_step(input_data=datasource.outputs.result)
        preprocesser_step(input_data=split_step.outputs.output_data)
