from zenml.datasources import CSVDatasource
from zenml.exceptions import AlreadyExistsException
from zenml.pipelines import TrainingPipeline, BatchInferencePipeline
from zenml.repo import Repository
from zenml.steps.evaluator import TFMAEvaluator
from zenml.steps.inferrer import TensorflowInferrer
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.split import RandomSplit
from zenml.steps.trainer import TFFeedForwardTrainer
from zenml.utils.naming_utils import transformed_label_name

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
training_pipeline.add_trainer(TFFeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=20))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['has_diabetes']],
                  metrics={transformed_label_name('has_diabetes'): [
                      'binary_crossentropy',
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
        labels=[transformed_label_name('has_diabetes')])
)
infer_pipeline.run()
df = infer_pipeline.get_predictions()
print(df.head())
