import os
from random import randint

from examples.cortex.predictor.tf import TensorFlowPredictor
from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.steps.deployer.cortex_deployer import CortexDeployer
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.tensorflow_trainers.tf_ff_trainer import \
    FeedForwardTrainer

CORTEX_ENDPOINT_NAME = os.getenv('CORTEX_ENDPOINT_NAME', 'zenml_classifier')

# Run the pipeline locally but deploy with zenml

training_pipeline = TrainingPipeline(
    name=f'Experiment {randint(0, 10000)}',
    enable_cache=False
)

# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name=f'My CSV Datasource {randint(0, 100000)}',
                   path='gs://zenml_quickstart/diabetes.csv')
training_pipeline.add_datasource(ds)

# Add a split
training_pipeline.add_split(RandomSplit(
    split_map={'eval': 0.3, 'train': 0.7}))

# Add a preprocessing unit
training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=['times_pregnant', 'pgc', 'dbp', 'tst', 'insulin', 'bmi',
                  'pedigree', 'age'],
        labels=['has_diabetes'],
        overwrite={'has_diabetes': {
            'transform': [{'method': 'no_transform', 'parameters': {}}]}}
    ))

# Add a trainer
training_pipeline.add_trainer(FeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=15))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))

# Add cortex deployer
api_config = {
    "name": CORTEX_ENDPOINT_NAME,
    "kind": "RealtimeAPI",
    "predictor": {"type": "tensorflow"}
}
training_pipeline.add_deployment(
    CortexDeployer(
        env='cortex-gcp',
        api_config=api_config,
        predictor=TensorFlowPredictor,
    )
)

# Run the pipeline locally
training_pipeline.run()
