from zenml.datasources.base_datasource import BaseDatasource
from zenml.pipelines.base_pipeline import Datasource, Step
from zenml.pipelines.simple_pipeline import SimplePipeline
from zenml.steps.deployer_step import DeployerStep
from zenml.steps.evaluator_step import EvaluatorStep
from zenml.steps.preprocesser_step import PreprocesserStep
from zenml.steps.schema_step import SchemaStep
from zenml.steps.split_step import SplitStep
from zenml.steps.statistics_step import StatisticsStep
from zenml.steps.trainer_step import TrainerStep


@SimplePipeline
def TrainingPipeline(
    datasource: Datasource[BaseDatasource],
    split: Step[SplitStep],
    raw_statistics: Step[StatisticsStep],
    raw_schema: Step[SchemaStep],
    preprocesser: Step[PreprocesserStep],
    xf_statistics: Step[StatisticsStep],
    xf_schema: Step[SchemaStep],
    trainer: Step[TrainerStep],
    evaluator: Step[EvaluatorStep],
    deployer: Step[DeployerStep],
):
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
    evaluator(
        input_data=preprocesser.outputs.data, input_model=trainer.outputs.model
    )

    # Handle the serving
    deployer(input_model=trainer.outputs.model)
