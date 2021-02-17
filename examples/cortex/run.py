import os

from examples.cortex.predictor.tf import TensorFlowPredictor
from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.repo.artifact_store import ArtifactStore
from zenml.core.steps.deployer.cortex_deployer import CortexDeployer
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import \
    StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.tensorflow_trainers.tf_ff_trainer import \
    FeedForwardTrainer
from zenml.utils.exceptions import AlreadyExistsException

GCP_BUCKET = os.getenv('GCP_BUCKET')
assert GCP_BUCKET
CORTEX_ENV = os.getenv('CORTEX_ENV', 'env')
CORTEX_MODEL_NAME = os.getenv('CORTEX_MODEL_NAME', 'zenml-classifier')

# For this example, the ArtifactStore must be a GCP bucket, as the
# CortexDeployer step is using the GCP env.

from zenml.core.repo.repo import Repository

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
    "name": CORTEX_MODEL_NAME,
    "kind": "RealtimeAPI",
    "predictor": {
        "type": "tensorflow",
        # Set signature key of the model as we are using Tensorflow Trainer
        "models": {"signature_key": "serving_default"}}
}
training_pipeline.add_deployment(
    CortexDeployer(
        env=CORTEX_ENV,
        api_config=api_config,
        predictor=TensorFlowPredictor,
    )
)

# Define the artifact store
artifact_store = ArtifactStore(
    os.path.join(GCP_BUCKET, 'cortex/artifact_store'))

# Run the pipeline
training_pipeline.run(artifact_store=artifact_store)
