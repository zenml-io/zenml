from pipelines.training_pipeline.training_pipeline import (
    neptune_example_pipeline,
)
from steps.evaluator.evaluator_step import tf_evaluator
from steps.loader.loader_step import loader_mnist
from steps.normalizer.normalizer_step import normalizer
from steps.trainer.trainer_step import TrainerParameters, tf_trainer

if __name__ == "__main__":
    # Initialize a pipeline run
    run = neptune_example_pipeline(
        importer=loader_mnist(),
        normalizer=normalizer(),
        trainer=tf_trainer(params=TrainerParameters(epochs=5, lr=0.0003)),
        evaluator=tf_evaluator(),
    )

    run.run()
