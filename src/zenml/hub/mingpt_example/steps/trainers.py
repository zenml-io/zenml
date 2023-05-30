import mlflow
from torch.nn import Module
from torch.utils.data import Dataset

from zenml import step

from ..mingpt.trainer import Trainer


@step(experiment_tracker="mlflow_tracker")
def mingpt_trainer_step(
    dataset: Dataset,
    model: Module,
    max_iters=2000,
    learning_rate=5e-4,
) -> Module:

    train_config = Trainer.get_default_config()
    train_config.learning_rate = learning_rate
    train_config.max_iters = max_iters
    trainer = Trainer(train_config, model, dataset)

    def batch_end_callback(trainer):
        if trainer.iter_num % 100 == 0:
            mlflow.log_metric(
                "train_loss", trainer.loss.item(), step=trainer.iter_num
            )
            print(
                f"iter_dt {trainer.iter_dt * 1000:.2f}ms; "
                f"iter {trainer.iter_num}: train loss {trainer.loss.item():.5f}"
            )

    trainer.set_callback("on_batch_end", batch_end_callback)

    trainer.run()

    mlflow.pytorch.log_model(model, "model")

    return model
