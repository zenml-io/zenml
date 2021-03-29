from zenml.datasources import CSVDatasource
from zenml.exceptions import AlreadyExistsException
from zenml.pipelines import TrainingPipeline
from zenml.repo import Repository
from zenml.steps.evaluator import AgnosticEvaluator
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.split import RandomSplit
from zenml.steps.trainer import TorchFeedForwardTrainer
from zenml.utils import naming_utils

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

# Add a trainer
training_pipeline.add_trainer(TorchFeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=100))

# Add an evaluator
label_name = naming_utils.transformed_label_name('has_diabetes')
training_pipeline.add_evaluator(
    AgnosticEvaluator(
        prediction_key='output',
        label_key=label_name,
        slices=[['has_diabetes']],
        metrics=['mean_squared_error']))

# Run the pipeline locally
training_pipeline.run()
