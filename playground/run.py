from playground.pipelines.split_pipeline import ClassSplitPipeline, FunctionSplitPipeline
from playground.steps.split_step import ClassSplitStep, FunctionSplitStep
from playground.steps.preprocesser_step import ClassPreprocesserStep, FunctionPreprocesserStep
from playground.datasources.csv_datasource import CSVDatasource

# Parameters
param = 1.0
split_map = 0.6

# Steps
datasource = CSVDatasource("local_test/data/data.csv")
split_step = ClassSplitStep(split_map=split_map)
preprocesser_step = ClassPreprocesserStep(param=param)

# Pipeline
split_pipeline = ClassSplitPipeline(datasource=datasource,
                                    split_step=split_step,
                                    preprocesser_step=preprocesser_step)

split_pipeline.run()
