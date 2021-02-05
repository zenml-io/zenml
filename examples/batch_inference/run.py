from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.pipelines.infer_pipeline import BatchInferencePipeline
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.repo.repo import Repository
from zenml.core.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import \
    StandardPreprocesser
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.steps.trainer.tensorflow_trainers.tf_ff_trainer import \
    FeedForwardTrainer
from zenml.utils.exceptions import AlreadyExistsException
from zenml.core.steps.inferrer.tensorflow_inferrer_step import TensorflowInferrer

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

# Run the pipeline locally
training_pipeline.run()

# Run inference
model_uri = training_pipeline.get_model_uri()
infer_pipeline = BatchInferencePipeline(
    model_uri=model_uri,
)
infer_pipeline.add_datasource(ds)
infer_pipeline.add_infer_step(
    TensorflowInferrer(
        labels=['has_diabetes'])
)
infer_pipeline.run()
df = infer_pipeline.get_predictions()
print(df.head())
