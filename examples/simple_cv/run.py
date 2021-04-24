from preprocessing.preprocessor import ImagePreprocessor
from trainer.trainer_step import ImageTensorflowTrainer
from zenml.datasources.tfds_datasource import TFDSDatasource
from zenml.exceptions import AlreadyExistsException
from zenml.pipelines import TrainingPipeline
from zenml.repo import Repository
from zenml.steps.evaluator.tfma_evaluator import TFMAEvaluator
from zenml.steps.split.random_split import RandomSplit
from zenml.utils import naming_utils

# Define the training pipeline
training_pipeline = TrainingPipeline()

# Add a datasource. This will automatically track and version it.
try:
    ds = TFDSDatasource(name='MNIST', tfds_dataset_name='mnist')
except AlreadyExistsException:
    ds = Repository.get_instance().get_datasource_by_name('MNIST')
training_pipeline.add_datasource(ds)

# Add a split
training_pipeline.add_split(RandomSplit(
    split_map={'train': 0.7, 'eval': 0.2, 'test': 0.1}))

# Add a preprocessing unit
training_pipeline.add_preprocesser(
    ImagePreprocessor(
        image_key='image',
        labels=['label'],
        shape=[-1, 28, 28, 3]
    ))

# Add a trainer
training_pipeline.add_trainer(ImageTensorflowTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    metrics=['accuracy'],
    epochs=5))

# Add an evaluator
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[[naming_utils.transformed_label_name('label')]],
                  metrics={naming_utils.transformed_label_name('label'): [
                      'binary_accuracy']}))

# Run the pipeline locally
training_pipeline.run()
