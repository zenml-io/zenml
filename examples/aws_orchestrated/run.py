"""

"""
import os

from zenml.backends.orchestrator import OrchestratorAWSBackend
from zenml.datasources import CSVDatasource
from zenml.exceptions import AlreadyExistsException
from zenml.metadata import MySQLMetadataStore
from zenml.pipelines import TrainingPipeline
from zenml.repo import ArtifactStore, Repository
from zenml.steps.evaluator import TFMAEvaluator
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.split import RandomSplit
from zenml.steps.trainer import TFFeedForwardTrainer
from zenml.utils.naming_utils import transformed_label_name

# Get the configuration for the artifact store and the metadata store which
# should be accessible from the VM
S3_BUCKET = os.getenv('S3_BUCKET')
IAM_ROLE = os.getenv('IAM_ROLE')

assert S3_BUCKET
assert IAM_ROLE

MYSQL_DB = os.getenv('MYSQL_DB')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PWD = os.getenv('MYSQL_PWD')
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')

assert MYSQL_DB
assert MYSQL_USER
assert MYSQL_PWD
assert MYSQL_HOST
assert MYSQL_PORT

# Define the training pipeline
training_pipeline = TrainingPipeline()

# Add a datasource. This will automatically track and version it.
try:
    ds = CSVDatasource(name='Pima Indians Diabetes AWS',
                       path='s3://zenml-quickstart/diabetes.csv')
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
    epochs=20))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={transformed_label_name('has_diabetes'): [
                      'binary_crossentropy',
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
    os.path.join(S3_BUCKET, 'aws_orchestrated/artifact_store'))

# Define the orchestrator backend
orchestrator_backend = OrchestratorAWSBackend(
    iam_role=IAM_ROLE
)

# Run the pipeline
training_pipeline.run(
    backend=orchestrator_backend,
    metadata_store=metadata_store,
    artifact_store=artifact_store,
)
