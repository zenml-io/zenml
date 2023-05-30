import mlflow
from torch.nn import Module
from torch.utils.data import Dataset

from zenml.steps import step

from ..mingpt.trainer import Trainer


@step()
def mingpt_trainer_step(dataset: Dataset, model: Module) -> Module:
    train_config = Trainer.get_default_config()
    train_config.learning_rate = 5e-4
    train_config.max_iters = 100  # TODO: 2000; make this configurable
    train_config.num_workers = 0
    train_config.device = "mps"  # TODO: make this configurable
    trainer = Trainer(train_config, model, dataset)

    def batch_end_callback(trainer):
        if trainer.iter_num % 100 == 0:
            # TODO: log to mlflow
            print(
                f"iter_dt {trainer.iter_dt * 1000:.2f}ms; iter {trainer.iter_num}: train loss {trainer.loss.item():.5f}"
            )

    trainer.set_callback("on_batch_end", batch_end_callback)
    trainer.run()
    model.__call__ = lambda *args, **kwargs: model.forward(*args, **kwargs)[0]
    mlflow.pytorch.log_model(model, "model")
    return model
