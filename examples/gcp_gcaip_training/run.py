import os

from zenml.core.backends.orchestrator.gcp.orchestrator_gcp_backend import \
    OrchestratorGCPBackend
from zenml.core.backends.training.training_gcaip_backend import \
    SingleGPUTrainingGCAIPBackend
from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.metadata.mysql_metadata_wrapper import MySQLMetadataStore
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
GCP_REGION = os.getenv('GCP_REGION')
GCP_CLOUD_SQL_INSTANCE_NAME = os.getenv('GCP_CLOUD_SQL_INSTANCE_NAME')
MYSQL_DB = os.getenv('MYSQL_DB')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PWD = os.getenv('MYSQL_PWD')
MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = os.getenv('MYSQL_PORT', 3306)
CONNECTION_NAME = f'{GCP_PROJECT}:{GCP_REGION}:{GCP_CLOUD_SQL_INSTANCE_NAME}'
TRAINING_JOB_DIR = os.path.join(GCP_BUCKET, 'gcp_gcaip_training/staging')

assert GCP_BUCKET
assert GCP_PROJECT
assert GCP_REGION
assert MYSQL_DB
assert MYSQL_USER
assert MYSQL_PWD

# Run the pipeline on a Google Cloud VM and train on GCP as well
# In order for this to work, the orchestrator and the backend should be in the
# same GCP project. Also, the metadata store and artifact store should be
# accessible by the orchestrator VM and the GCAIP worker VM.

# Note: If you are using a custom Trainer, then you need
# to build a new Docker image based on the ZenML Trainer image, and pass that
# into the `image` parameter in the SingleGPUTrainingGCAIPBackend.

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
    split_map={'train': 0.7, 'eval': 0.3}))

# Add a preprocessing unit
training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=['times_pregnant', 'pgc', 'dbp', 'tst', 'insulin', 'bmi',
                  'pedigree', 'age'],
        labels=['has_diabetes'],
        overwrite={'has_diabetes': {
            'transform': [{'method': 'no_transform', 'parameters': {}}]}}
    ))

# Add a trainer with a GCAIP backend
training_backend = SingleGPUTrainingGCAIPBackend(
    project=GCP_PROJECT,
    job_dir=TRAINING_JOB_DIR
)

training_pipeline.add_trainer(FeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=20).with_backend(training_backend)
                              )

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))

# Define the metadata store
metadata_store = MySQLMetadataStore(
    host=MYSQL_HOST,
    port=int(MYSQL_PORT),
    database=MYSQL_DB,
    username=MYSQL_USER,
    password=MYSQL_PWD,
)

# Define the artifact store
artifact_store = ArtifactStore(
    os.path.join(GCP_BUCKET, 'gcp_gcaip_training/artifact_store'))

# Define the orchestrator backend
orchestrator_backend = OrchestratorGCPBackend(
    cloudsql_connection_name=GCP_CLOUD_SQL_INSTANCE_NAME,
    project=GCP_PROJECT)

# Run the pipeline
training_pipeline.run(
    backend=orchestrator_backend,
    metadata_store=metadata_store,
    artifact_store=artifact_store,
)
