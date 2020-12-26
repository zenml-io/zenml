from zenml.core.backends.processing.processing_dataflow_backend import \
    ProcessingDataFlowBackend
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

# Run the pipeline locally but distribute the beam-compatible steps, i.e.,
# the Data, Statistics, Preprocessing and Evaluator Steps.
# Note: If any of these steps are non-standard, custom steps, then you need
# to build a new Docker image based on the ZenML Dataflow image, and pass that
# into the `image` parameter in the ProcessingDataFlowBackend


# Define the processing backend
processing_backend = ProcessingDataFlowBackend(project=project)

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
    backends=[processing_backend],
    metadata_store=metadata_store,
    artifact_store=artifact_store,
)
