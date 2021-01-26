import os

from zenml.core.backends.orchestrator.kubernetes \
    .orchestrator_kubernetes_backend import \
    OrchestratorKubernetesBackend
from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.metadata.mysql_metadata_wrapper import MySQLMetadataStore
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.repo.artifact_store import ArtifactStore
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import \
    StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.tensorflow_trainers.tf_ff_trainer import \
    FeedForwardTrainer

training_pipeline = TrainingPipeline(name='kubernetes')

# Add a datasource. This will automatically track and version it.
try:
    ds = CSVDatasource(name='Pima Indians Diabetes',
                       path='gs://zenml_quickstart/diabetes.csv')
except:
    # A small nicety for people that have ran a quickstart before :)
    from zenml.core.repo.repo import Repository

    repo: Repository = Repository.get_instance()
    ds = repo.get_datasource_by_name("Pima Indians Diabetes")

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

# Important details:
artifact_store_bucket = 'gs://rndm-strg/zenml-k8s-test/'

mysql_host = 'cloudsql'
mysql_port = 3306
mysql_db = 'zenml'
mysql_user = USERNAME
mysql_pw = PASSWORD

# Path to your kubernetes config:
k8s_config_path = os.path.join(os.environ["HOME"], '.kube/config')

# Run the pipeline on a Kubernetes Cluster
training_pipeline.run(
    backends=[
        OrchestratorKubernetesBackend(kubernetes_config_path=k8s_config_path,
                                      image_pull_policy="Always")],
    metadata_store=MySQLMetadataStore(
        host=mysql_host,
        port=mysql_port,
        database=mysql_db,
        username=mysql_user,
        password=mysql_pw,
    ),
    artifact_store=ArtifactStore(artifact_store_bucket)
)
