from playground.datasources.base_datasource import BaseDatasource
from playground.pipelines.base_pipeline import Step, Datasource
from playground.pipelines.simple_pipeline import SimplePipeline
from playground.steps.deployer_step import DeployerStep
from playground.steps.evaluator_step import EvaluatorStep
from playground.steps.preprocesser_step import PreprocesserStep
from playground.steps.schema_step import SchemaStep
from playground.steps.split_step import SplitStep
from playground.steps.statistics_step import StatisticsStep
from playground.steps.trainer_step import TrainerStep


@SimplePipeline
def TrainingPipeline(datasource: Datasource[BaseDatasource],
                     split: Step[SplitStep],
                     raw_statistics: Step[StatisticsStep],
                     raw_schema: Step[SchemaStep],
                     preprocesser: Step[PreprocesserStep],
                     xf_statistics: Step[StatisticsStep],
                     xf_schema: Step[SchemaStep],
                     trainer: Step[TrainerStep],
                     evaluator: Step[EvaluatorStep],
                     deployer: Step[DeployerStep]):
    # Handle the raw data
    split(input_data=datasource)
    raw_statistics(input_data=split.outputs.data)
    raw_schema(input_statitics=raw_statistics.outputs.statistics)

    # Handle the preprocessing
    preprocesser(input_data=split.outputs.data)
    xf_statistics(input_data=preprocesser.outputs.data)
    xf_schema(input_statitics=xf_statistics.outputs.statistics)

    # Handle the training and evaluation
    trainer(input_data=preprocesser.outputs.data)
    evaluator(input_data=preprocesser.outputs.data,
              input_model=trainer.outputs.model)

    # Handle the serving
    deployer(input_model=trainer.outputs.model)
