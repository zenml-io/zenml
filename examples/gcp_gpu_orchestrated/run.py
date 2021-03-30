import os

from zenml.backends.orchestrator import OrchestratorGCPBackend
from zenml.datasources import CSVDatasource
from zenml.exceptions import AlreadyExistsException
from zenml.metadata import MySQLMetadataStore
from zenml.pipelines import TrainingPipeline
from zenml.repo import Repository, ArtifactStore
from zenml.steps.evaluator import TFMAEvaluator
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.split import RandomSplit
from zenml.steps.trainer import TFFeedForwardTrainer
from zenml.utils.naming_utils import transformed_label_name

GCP_PROJECT = os.getenv('GCP_PROJECT')
GCP_BUCKET = os.getenv('GCP_BUCKET')
GCP_REGION = os.getenv('GCP_REGION')
MYSQL_DB = os.getenv('MYSQL_DB')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PWD = os.getenv('MYSQL_PWD')
MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = os.getenv('MYSQL_PORT', 3306)
GCP_CLOUD_SQL_INSTANCE_NAME = os.getenv('GCP_CLOUD_SQL_INSTANCE_NAME',
                                        MYSQL_DB)
CONNECTION_NAME = f'{GCP_PROJECT}:{GCP_REGION}:{GCP_CLOUD_SQL_INSTANCE_NAME}'

assert GCP_BUCKET
assert GCP_PROJECT
assert GCP_REGION
assert MYSQL_DB
assert MYSQL_USER
assert MYSQL_PWD

# Run the pipeline on a Google Cloud VM.
# The metadata store and artifact store should be accessible by the
# orchestrator VM.

# Define the training pipeline
training_pipeline = TrainingPipeline(enable_cache=False)

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
    split_map={'train': 0.7, 'eval': 0.2, 'test': 0.1}))

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
training_pipeline.add_trainer(TFFeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=2000))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={transformed_label_name('has_diabetes'):
                               ['binary_crossentropy', 'binary_accuracy']}))

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
    os.path.join(GCP_BUCKET, 'gcp_gpu_orchestrated/artifact_store'))

# Define the orchestrator backend
orchestrator_backend = OrchestratorGCPBackend(
    cloudsql_connection_name=CONNECTION_NAME,
    project=GCP_PROJECT,
    preemptible=True,  # reduce costs by using preemptible instances
    machine_type='n1-standard-4',
    gpu='nvidia-tesla-k80',
    gpu_count=1,
)

# Run the pipeline
training_pipeline.run(
    backend=orchestrator_backend,
    metadata_store=metadata_store,
    artifact_store=artifact_store,
)
