from random import randint

from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.feedforward_trainer.trainer import \
    FeedForwardTrainer
from zenml.core.steps.deployer.cortex_deployer import CortexDeployer
from zenml.core.repo.repo import ArtifactStore


training_pipeline = TrainingPipeline(
    name=f'Experiment {randint(0, 10000)}',
    enable_cache=True
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
    epochs=13))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))

# Pusher
training_pipeline.add_deployment(
    CortexDeployer(
        api_spec="diabetes_1",
        predictor=Predictor,
    )
)

# Run the pipeline locally
training_pipeline.run(
    artifact_store=ArtifactStore(path="gs://zenmlartifactstore/artifact_store_4/")
)

# Sample data
df = training_pipeline.sample_transformed_data()
print(df.shape)
print(df.describe())

# Evaluate
# training_pipeline.evaluate()

# See schema of data and detect drift
# training_pipeline.view_schema()

# See statistics of train and eval
# training_pipeline.view_statistics()
