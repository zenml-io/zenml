from step.trainer import TorchRegressionTrainer
from zenml.datasources import CSVDatasource
from zenml.exceptions import AlreadyExistsException
from zenml.pipelines import TrainingPipeline
from zenml.repo import Repository
from zenml.steps.evaluator import AgnosticEvaluator
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.split import RandomSplit
from zenml.utils import naming_utils

training_pipeline = TrainingPipeline()

try:
    ds = CSVDatasource(name='boston_data', path='./data/boston_data.csv')
except AlreadyExistsException:
    ds = Repository.get_instance().get_datasource_by_name(
        'boston_data')
training_pipeline.add_datasource(ds)

# Add a split
training_pipeline.add_split(RandomSplit(
    split_map={'train': 0.7, 'eval': 0.2, 'test': 0.1}))

# Add a preprocessing unit
training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=['crim',
                  'zn',
                  'indus',
                  'chas',
                  'nox',
                  'rm',
                  'age',
                  'dis',
                  'rad',
                  'tax',
                  'ptratio',
                  'black',
                  'lstat'],
        labels=['medv'],
        overwrite={'medv': {
            'transform': [{'method': 'no_transform', 'parameters': {}}]}}
    ))

# Add a trainer

training_pipeline.add_trainer(TorchRegressionTrainer(
    loss='mse',
    optimizer="adam",
    last_activation='relu',
    metrics=['accuracy'],
    epochs=100))

# Add an evaluator
label_name = naming_utils.transformed_label_name('medv')
training_pipeline.add_evaluator(
    AgnosticEvaluator(
        prediction_key='output',
        label_key=label_name,
        slices=[['medv']],
        metrics=['mean_squared_error']))

# Run the pipeline locally
training_pipeline.run()
training_pipeline.evaluate()
