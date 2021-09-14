import os

from zenml.backends.orchestrator import OrchestratorCommonKubernetesBackend
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

training_pipeline = TrainingPipeline()
# Add a datasource. This will automatically track and version it.
try:
    ds = CSVDatasource(name='Pima Indians Diabetes',
                       path='/home/data/diabetes.csv')
except AlreadyExistsException:
    ds = Repository.get_instance().get_datasource_by_name(
        'Pima Indians Diabetes')
training_pipeline.add_datasource(ds)
# Add a split
training_pipeline.add_split(RandomSplit(
    split_map={'train': 0.8, 'eval': 0.1, 'test': 0.1}))
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
                  metrics={transformed_label_name('has_diabetes'):
                               ['binary_crossentropy', 'binary_accuracy']}))

# Define the orchestrator backend
orchestrator_backend = OrchestratorCommonKubernetesBackend(
    image="XXX/zenml/zenml-jupyter-common-k8s:v0.3.8",
    kubernetes_config_path="/home/k8s_config/k8s_config_dev",
    image_pull_policy="Always",
    volumes = {'name':'zenml-jupyter', 'persistent_volume_claim': {'claim_name': 'zenml-jupyter'}},
    volume_mounts={'name':'zenml-jupyter', 'sub_path': './experiment/experiment2', 'mount_path':'/home'}, # lambda存储卷实验地址
    # volume_mounts={'name':'zenml-jupyter', 'mount_path':'/home'}, # lambda存储卷实验地址
    namespace='f8qc7msyognylu9ukc04',
    resource_limits={'memory': '2Gi', 'cpu': '1'},
    resource_requests={'memory': '2Gi', 'cpu': '1'}
)

# Run the pipeline on a Kubernetes Cluster
training_pipeline.run(backend=orchestrator_backend)