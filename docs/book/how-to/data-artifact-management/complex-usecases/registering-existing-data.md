---
description: Learn how to register an external data as a ZenML artifact for future use.
---

# Register Existing Data as a ZenML Artifact

Many modern Machine Learning framework create their own data as a byproduct of model training or other processes. In such cases there is no need to read and materialize those data assets to pack them into a ZenML Artifact, instead it is beneficial registering those data assets as-is in ZenML for future use.

## Register Existing Folder as a ZenML Artifact

If the data created externally is a folder you can register the whole folder as a ZenML Artifact and later make use of it in subsequent steps or other pipelines.

```python
import os
from uuid import uuid4
from pathlib import Path

from zenml.client import Client
from zenml import register_artifact

prefix = Client().active_stack.artifact_store.path
test_file_name = "test_file.txt"
preexisting_folder = os.path.join(prefix,f"my_test_folder_{uuid4()}")
preexisting_file = os.path.join(preexisting_folder,test_file_name)

# produce a folder with a file inside artifact store boundaries
os.mkdir(preexisting_folder)
with open(preexisting_file,"w") as f:
    f.write("test")

# create artifact from the preexisting folder
register_artifact(
    folder_or_file_uri=preexisting_folder,
    name="my_folder_artifact"
)

# consume artifact as a folder
temp_artifact_folder_path = Client().get_artifact_version(name_id_or_prefix="my_folder_artifact").load()
assert isinstance(temp_artifact_folder_path, Path)
assert os.path.isdir(temp_artifact_folder_path)
with open(os.path.join(temp_artifact_folder_path,test_file_name),"r") as f:
    assert f.read() == "test"
```

{% hint style="info" %}
The artifact produced from the preexisting data will have a `pathlib.Path` type, once loaded or passed as input to another step. The path will be pointing to a temporary location in the executing environment and ready for use as a normal local `Path` (passed into `from_pretrained` or `open` functions to name a few examples).
{% endhint %}

## Register Existing File as a ZenML Artifact

If the data created externally is a file you can register it as a ZenML Artifact and later make use of it in subsequent steps or other pipelines.

```python
import os
from uuid import uuid4
from pathlib import Path

from zenml.client import Client
from zenml import register_artifact

prefix = Client().active_stack.artifact_store.path
test_file_name = "test_file.txt"
preexisting_folder = os.path.join(prefix,f"my_test_folder_{uuid4()}")
preexisting_file = os.path.join(preexisting_folder,test_file_name)

# produce a file inside artifact store boundaries
os.mkdir(preexisting_folder)
with open(preexisting_file,"w") as f:
    f.write("test")

# create artifact from the preexisting file
register_artifact(
    folder_or_file_uri=preexisting_file,
    name="my_file_artifact"
)

# consume artifact as a file
temp_artifact_file_path = Client().get_artifact_version(name_id_or_prefix="my_file_artifact").load()
assert isinstance(temp_artifact_file_path, Path)
assert not os.path.isdir(temp_artifact_file_path)
with open(temp_artifact_file_path,"r") as f:
    assert f.read() == "test"
```

## Register All Checkpoints of a Pytorch Lightning Training Run

Now let's explore the Pytorch Lightning example to fit the model and store the checkpoints in a remote location.

```python
import os
from zenml.client import Client
from zenml import register_artifact
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint
from uuid import uuid4

# Define where the model data should be saved
# use active ArtifactStore
prefix = Client().active_stack.artifact_store.path
# keep data separable for future runs with uuid4 folder
default_root_dir = os.path.join(prefix, uuid4().hex)

# Define the model and fit it
model = ...
trainer = Trainer(
    default_root_dir=default_root_dir,
    callbacks=[
        ModelCheckpoint(
            every_n_epochs=1, save_top_k=-1, filename="checkpoint-{epoch:02d}"
        )
    ],
)
try:
    trainer.fit(model)
finally:
    # We now link those checkpoints in ZenML as an artifact
    # This will create a new artifact version
    register_artifact(default_root_dir, name="all_my_model_checkpoints")
```

Even if an artifact is created and stored externally, it can be treated like any other artifact produced by ZenML steps - with all the functionalities described above!

## Register Checkpoints of a Pytorch Lightning Training Run as Separate Artifact Versions
To make checkpoints (or other intermediate artifacts) linkage better versioned you can extend the `ModelCheckpoint` callback to your needs. For example such custom implementation could look like the one below, where we extend the `on_train_epoch_end` method to register each checkpoint created during the training as a separate Artifact Version in ZenML.

{% hint style="warning" %}
To make checkpoint files last you need to set `save_top_k=-1`, otherwise older checkpoints will be deleted, making registered artifact version unusable.
{% endhint %}

```python
import os

from zenml.client import Client
from zenml import register_artifact
from zenml import get_step_context
from zenml.exceptions import StepContextError
from zenml.logger import get_logger

from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning import Trainer, LightningModule

logger = get_logger(__name__)


class ZenMLModelCheckpoint(ModelCheckpoint):
    """A ModelCheckpoint that can be used with ZenML.

    Used to store model checkpoints in ZenML as artifacts.
    Supports `default_root_dir` to pass into `Trainer`.
    """

    def __init__(
        self,
        artifact_name: str,
        every_n_epochs: int = 1,
        save_top_k: int = -1,
        *args,
        **kwargs,
    ):
        # get all needed info for the ZenML logic
        try:
            zenml_model = get_step_context().model
        except StepContextError:
            raise RuntimeError(
                "`ZenMLModelCheckpoint` can only be called from within a step."
            )
        model_name = zenml_model.name
        filename = model_name + "_{epoch:02d}"
        self.filename_format = model_name + "_epoch={epoch:02d}.ckpt"
        self.artifact_name = artifact_name

        prefix = Client().active_stack.artifact_store.path
        self.default_root_dir = os.path.join(prefix, str(zenml_model.version))
        logger.info(f"Model data will be stored in {self.default_root_dir}")

        super().__init__(
            every_n_epochs=every_n_epochs,
            save_top_k=save_top_k,
            filename=filename,
            *args,
            **kwargs,
        )

    def on_train_epoch_end(
        self, trainer: "Trainer", pl_module: "LightningModule"
    ) -> None:
        super().on_train_epoch_end(trainer, pl_module)

        # We now link those checkpoints in ZenML as an artifact
        # This will create a new artifact version
        register_artifact(
            os.path.join(
                self.dirpath, self.filename_format.format(epoch=trainer.current_epoch)
            ),
            self.artifact_name,
        )
```

Below you can find a sophisticated example of a pipeline doing a Pytorch Lightning training with the artifacts linkage for checkpoint artifacts implemented as an extended Callback.

<details>

<summary>Pytorch Lightning training with the checkpoints linkage full example</summary>

```python
import os
from typing import Annotated
from pathlib import Path

import numpy as np
from zenml.client import Client
from zenml import register_artifact
from zenml import step, pipeline, get_step_context, Model
from zenml.exceptions import StepContextError
from zenml.logger import get_logger

from torch.utils.data import DataLoader
from torch.nn import ReLU, Linear, Sequential
from torch.nn.functional import mse_loss
from torch.optim import Adam
from torch import rand
from torchvision.datasets import MNIST
from torchvision.transforms import ToTensor
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning import Trainer, LightningModule

from zenml.new.pipelines.pipeline_context import get_pipeline_context

logger = get_logger(__name__)


class ZenMLModelCheckpoint(ModelCheckpoint):
    """A ModelCheckpoint that can be used with ZenML.

    Used to store model checkpoints in ZenML as artifacts.
    Supports `default_root_dir` to pass into `Trainer`.
    """

    def __init__(
        self,
        artifact_name: str,
        every_n_epochs: int = 1,
        save_top_k: int = -1,
        *args,
        **kwargs,
    ):
        # get all needed info for the ZenML logic
        try:
            zenml_model = get_step_context().model
        except StepContextError:
            raise RuntimeError(
                "`ZenMLModelCheckpoint` can only be called from within a step."
            )
        model_name = zenml_model.name
        filename = model_name + "_{epoch:02d}"
        self.filename_format = model_name + "_epoch={epoch:02d}.ckpt"
        self.artifact_name = artifact_name

        prefix = Client().active_stack.artifact_store.path
        self.default_root_dir = os.path.join(prefix, str(zenml_model.version))
        logger.info(f"Model data will be stored in {self.default_root_dir}")

        super().__init__(
            every_n_epochs=every_n_epochs,
            save_top_k=save_top_k,
            filename=filename,
            *args,
            **kwargs,
        )

    def on_train_epoch_end(
        self, trainer: "Trainer", pl_module: "LightningModule"
    ) -> None:
        super().on_train_epoch_end(trainer, pl_module)

        # We now link those checkpoints in ZenML as an artifact
        # This will create a new artifact version
        register_artifact(
            os.path.join(
                self.dirpath, self.filename_format.format(epoch=trainer.current_epoch)
            ),
            self.artifact_name,
        )


# define the LightningModule toy model
class LitAutoEncoder(LightningModule):
    def __init__(self, encoder, decoder):
        super().__init__()
        self.encoder = encoder
        self.decoder = decoder

    def training_step(self, batch, batch_idx):
        # training_step defines the train loop.
        # it is independent of forward
        x, _ = batch
        x = x.view(x.size(0), -1)
        z = self.encoder(x)
        x_hat = self.decoder(z)
        loss = mse_loss(x_hat, x)
        # Logging to TensorBoard (if installed) by default
        self.log("train_loss", loss)
        return loss

    def configure_optimizers(self):
        optimizer = Adam(self.parameters(), lr=1e-3)
        return optimizer


@step
def get_data() -> DataLoader:
    """Get the training data."""
    dataset = MNIST(os.getcwd(), download=True, transform=ToTensor())
    train_loader = DataLoader(dataset)

    return train_loader


@step
def get_model() -> LightningModule:
    """Get the model to train."""
    encoder = Sequential(Linear(28 * 28, 64), ReLU(), Linear(64, 3))
    decoder = Sequential(Linear(3, 64), ReLU(), Linear(64, 28 * 28))
    model = LitAutoEncoder(encoder, decoder)
    return model


@step
def train_model(
    model: LightningModule,
    train_loader: DataLoader,
    epochs: int = 1,
    artifact_name: str = "my_model_ckpts",
) -> None:
    """Run the training loop."""
    # configure checkpointing
    chkpt_cb = ZenMLModelCheckpoint(artifact_name=artifact_name)

    trainer = Trainer(
        # pass default_root_dir from ZenML checkpoint to
        # ensure that the data is accessible for the artifact
        # store
        default_root_dir=chkpt_cb.default_root_dir,
        limit_train_batches=100,
        max_epochs=epochs,
        callbacks=[chkpt_cb],
    )
    trainer.fit(model, train_loader)


@step
def predict(
    checkpoint_file: Path,
) -> Annotated[np.ndarray, "predictions"]:
    # load the model from the checkpoint
    encoder = Sequential(Linear(28 * 28, 64), ReLU(), Linear(64, 3))
    decoder = Sequential(Linear(3, 64), ReLU(), Linear(64, 28 * 28))
    autoencoder = LitAutoEncoder.load_from_checkpoint(
        checkpoint_file, encoder=encoder, decoder=decoder
    )
    encoder = autoencoder.encoder
    encoder.eval()

    # predict on fake batch
    fake_image_batch = rand(4, 28 * 28, device=autoencoder.device)
    embeddings = encoder(fake_image_batch)
    if embeddings.device.type == "cpu":
        return embeddings.detach().numpy()
    else:
        return embeddings.detach().cpu().numpy()


@pipeline(model=Model(name="LightningDemo"))
def train_pipeline(artifact_name: str = "my_model_ckpts"):
    train_loader = get_data()
    model = get_model()
    train_model(model, train_loader, 10, artifact_name)
    # pass in the latest checkpoint for predictions
    predict(
        get_pipeline_context().model.get_artifact(artifact_name), after=["train_model"]
    )


if __name__ == "__main__":
    train_pipeline()
```

</details>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>