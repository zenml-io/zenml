import os

from zenml.core.backends.processing.processing_dataflow_backend import \
    ProcessingDataFlowBackend
from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.repo.artifact_store import ArtifactStore
from zenml.core.repo.repo import Repository
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import \
    StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.tensorflow_trainers.tf_ff_trainer import \
    FeedForwardTrainer
from zenml.utils.exceptions import AlreadyExistsException

GCP_PROJECT = os.getenv('GCP_PROJECT')
GCP_BUCKET = os.getenv('GCP_BUCKET')
assert GCP_BUCKET
assert GCP_PROJECT

# Run the pipeline locally but distribute the beam-compatible steps, i.e.,
# the Data, Statistics, Preprocessing and Evaluator Steps.
# Note: If any of these steps are non-standard, custom steps, then you need
# to build a new Docker image based on the ZenML Dataflow image, and pass that
# into the `image` parameter in the ProcessingDataFlowBackend

# Define the processing backend
processing_backend = ProcessingDataFlowBackend(
    project=GCP_PROJECT,
    staging_location=os.path.join(GCP_BUCKET, 'dataflow_processing/staging'),
)

# Define the training pipeline
training_pipeline = TrainingPipeline()

# Add a datasource. This will automatically track and version it.
try:
    ds = CSVDatasource(name='Pima Indians Diabetes',
                       path='gs://zenml_quickstart/diabetes.csv')
except AlreadyExistsException:
    ds = Repository.get_instance().get_datasource_by_name(
        'Pima Indians Diabetes')
training_pipeline.add_datasource(ds)

# Add a split
training_pipeline.add_split(
    RandomSplit(split_map={'train': 0.7, 'eval': 0.3}).with_backend(
        processing_backend)
)

# Add a preprocessing unit
training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=['times_pregnant', 'pgc', 'dbp', 'tst', 'insulin', 'bmi',
                  'pedigree', 'age'],
        labels=['has_diabetes'],
        overwrite={'has_diabetes': {
            'transform': [{'method': 'no_transform', 'parameters': {}}]}}
    ).with_backend(processing_backend)
)

# Add a trainer
training_pipeline.add_trainer(FeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=20))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(
        slices=[['has_diabetes']],
        metrics={'has_diabetes': ['binary_crossentropy', 'binary_accuracy']}
    ).with_backend(processing_backend)
)

# Define the artifact store
artifact_store = ArtifactStore(
    os.path.join(GCP_BUCKET, 'dataflow_processing/artifact_store'))

# Run the pipeline
training_pipeline.run(artifact_store=artifact_store)
