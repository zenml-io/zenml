from zenml.datasources.csv_datasource import CSVDatasource
from zenml.pipelines import TrainingPipeline
from zenml.repo.repo import Repository
from zenml.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.split.random_split import RandomSplit
from zenml.steps.trainer import TFFeedForwardTrainer

#########################
# CREATE FIRST PIPELINE #
#########################
training_pipeline = TrainingPipeline(name='Experiment 1')

# Add a datasource. This will automatically track and version it.
ds = CSVDatasource(name='Pima Diabetes',
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
training_pipeline.add_trainer(TFFeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=11))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={'has_diabetes': ['binary_crossentropy',
                                            'binary_accuracy']}))

# Run the pipeline locally
training_pipeline.run()

######################
# DO SOME EVALUATION #
######################
# Sample data
df = training_pipeline.sample_transformed_data()
print(df.shape)
print(df.describe())

# See schema of data and detect drift
print(training_pipeline.view_schema())

##########################
# CREATE SECOND PIPELINE #
##########################
training_pipeline_2 = training_pipeline.copy('Experiment 2')
training_pipeline_2.add_trainer(TFFeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=15))
training_pipeline_2.run()

############################
# DO SOME REPOSITORY STUFF #
############################

repo: Repository = Repository.get_instance()

# Check pipeline
pipelines = repo.get_pipelines()
assert len(pipelines) == 2

datasources = repo.get_datasources()
assert len(datasources) == 1

datasource: CSVDatasource = repo.get_datasource_by_name('Pima Diabetes')
print(datasource.view_schema())
