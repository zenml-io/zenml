from zenml.core.backends.orchestrator.gcp.orchestrator_gcp_backend import \
    OrchestratorGCPBackend
from zenml.core.backends.training.training_gcaip_backend import \
    SingleGPUTrainingGCAIPBackend
from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.metadata.mysql_metadata_wrapper import MySQLMetadataStore
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.repo.artifact_store import ArtifactStore
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import \
    StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.feedforward_trainer import FeedForwardTrainer

artifact_store_path = 'gs://your-bucket-name/optional-subfolder'
project = 'PROJECT'  # the project to launch the VM in
cloudsql_connection_name = f'{project}:REGION:INSTANCE'
mysql_db = 'DATABASE'
mysql_user = 'USERNAME'
mysql_pw = 'PASSWORD'
training_job_dir = artifact_store_path + '/gcaiptrainer/'

training_pipeline = TrainingPipeline(name='GCP Orchestrated')

# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name='Pima Indians Diabetes',
                   path='gs://zenml_quickstart/diabetes.csv')
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

# Add a trainer
training_pipeline.add_trainer(FeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=20))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))

# Run the pipeline on a Google Cloud VM and train on GCP as well
# In order for this to work, the orchestrator and the backend should be in the
# same GCP project. Also, the metadata store and artifact store should be
# accessible by the orchestrator VM and the GCAIP worker VM.

# Note: If you are using a custom Trainer, then you need
# to build a new Docker image based on the ZenML Trainer image, and pass that
# into the `image` parameter in the SingleGPUTrainingGCAIPBackend.


# Define the orchestrator backend
orchestrator_backend = OrchestratorGCPBackend(
    cloudsql_connection_name=cloudsql_connection_name,
    project=project)

# Define the training backend
training_backend = SingleGPUTrainingGCAIPBackend(
    project=project,
    job_dir=training_job_dir)

# Define the metadata store
metadata_store = MySQLMetadataStore(
    host='127.0.0.1',
    port=3306,
    database=mysql_db,
    username=mysql_user,
    password=mysql_pw,
)

# Define the artifact store
artifact_store = ArtifactStore(artifact_store_path)

# Run the pipeline
training_pipeline.run(
    backends=[orchestrator_backend, training_backend],
    metadata_store=metadata_store,
    artifact_store=artifact_store,
)
