import os

from zenml.datasources import CSVDatasource
from zenml.exceptions import AlreadyExistsException
from zenml.pipelines import TrainingPipeline
from zenml.repo import Repository, ArtifactStore
from zenml.steps.deployer import GCAIPDeployer
from zenml.steps.evaluator import TFMAEvaluator
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.split import RandomSplit
from zenml.steps.trainer import TFFeedForwardTrainer
from zenml.utils.naming_utils import transformed_label_name

GCP_PROJECT = os.getenv('GCP_PROJECT')
GCP_BUCKET = os.getenv('GCP_BUCKET')
MODEL_NAME = os.getenv('MODEL_NAME')

assert GCP_PROJECT
assert GCP_BUCKET
assert MODEL_NAME

# Deploy a tensorflow model on GCAIP. Note that no other trainer type
# works with this deployer except for the one shown here.

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

# Add the deployer
training_pipeline.add_deployment(
    GCAIPDeployer(
        project_id=GCP_PROJECT,
        model_name=MODEL_NAME,
    )
)

# Define the artifact store
artifact_store = ArtifactStore(
    os.path.join(GCP_BUCKET, 'gcp_gcaip_deployment/artifact_store'))

# Run the pipeline
training_pipeline.run(artifact_store=artifact_store)

# Another way to do is is to create a DeploymentPipeline.
# Uncomment to create the model via this pipeline
# from zenml.core.pipelines.deploy_pipeline import DeploymentPipeline
# model_uri = training_pipeline.get_model_uri()
# deploy_pipeline = DeploymentPipeline(model_uri=model_uri)
# deploy_pipeline.add_deployment(
#     GCAIPDeployer(
#         model_name=MODEL_NAME + '_v2',
#         project_id=GCP_PROJECT
#     )
# )
# deploy_pipeline.run(artifact_store=artifact_store)
