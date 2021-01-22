from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.pytorch_trainers.torch_ff_trainer import \
    FeedForwardTrainer

training_pipeline = TrainingPipeline(name='ZenML with a Pytorch Trainer')

# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name='Pima Indians Diabetes',
                   path='gs://zenml_quickstart/diabetes.csv')
training_pipeline.add_datasource(ds)

# Add a split
training_pipeline.add_split(RandomSplit(
    split_map={'eval': 0.3, 'train': 0.7}))

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
    epoch=100))

# Run the pipeline locally
training_pipeline.run()
