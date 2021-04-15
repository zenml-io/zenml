# Creating your trainer

## Overview

**\[TODO\]**

```python
class BaseTrainerStep(BaseStep):

    @staticmethod
    def model_fn(train_dataset, 
                 eval_dataset):
        ...

    def run_fn(self):
        ...
```

### input\_fn

**\[TODO\]**

```python
def input_fn(self,
             file_pattern: List[Text],
             tf_transform_output: tft.TFTransformOutput):
```

### model\_fn

**\[TODO\]**

```python
@staticmethod
def model_fn(train_dataset, 
             eval_dataset)
```

### run\_fn

**\[TODO\]**

```python
  def run_fn(self)
```

## A quick example: the built-in `StandardPreprocesser` step

**\[TODO\]**

{% hint style="info" %}
The following is an overview of the complete step. You can find the full code right [here](https://github.com/maiot-io/zenml/blob/main/zenml/steps/split/base_split_step.py).
{% endhint %}

```python
class BinaryClassifier(nn.Module):
    ...


def binary_acc(y_pred, y_test):
    ...


class TorchFeedForwardTrainer(BaseTrainerStep):
    def input_fn(self,
                 file_patterns: List[Text]):
        """
        Function which creates the datasets for model training
        """
        dataset = torch_utils.TFRecordTorchDataset(file_patterns,
                                                   self.schema)
        loader = torch.utils.data.DataLoader(dataset,
                                             batch_size=self.batch_size,
                                             drop_last=True)
        return loader

    def model_fn(self, train_dataset, eval_dataset):
        """
        Function which prepares the model instance
        """
        return BinaryClassifier()

    def run_fn(self):
        """
        Function which handles the model training
        """
        ....
        # Prepare the datasets
        train_dataset = self.input_fn(train_split_patterns)
        eval_dataset = self.input_fn(eval_split_patterns)

        # Prepare the model
        model = self.model_fn(train_dataset, eval_dataset)
        
        # Execute the training
        criterion = nn.BCEWithLogitsLoss()
        optimizer = optim.Adam(model.parameters(), lr=self.lr)
        
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.train()

        for e in range(1, self.epochs + 1):
            for x, y, _ in train_dataset:
                x_batch = torch.cat([v.to(device) for v in x.values()], dim=-1)
                y_batch = torch.cat([v.to(device) for v in y.values()], dim=-1)
                
                optimizer.zero_grad()

                y_pred = model(x_batch)
                loss = criterion(y_pred, y_batch)
                acc = binary_acc(y_pred, y_batch)

                loss.backward()
                optimizer.step()                
                ...
```

We can now go ahead and use this step in our pipeline:

```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.split import RandomSplit

training_pipeline = TrainingPipeline()

...

training_pipeline.add_trainer(TorchFeedForwardTrainer(
    loss='binary_crossentropy',
    last_activation='sigmoid',
    output_units=1,
    metrics=['accuracy'],
    epochs=100))

...
```

{% hint style="warning" %}
**An important note here**: As you see from the code blocks that you see above, any input given to the constructor of a step will translate into an instance variable. So, when you want to use it you can use **`self`**, as we did with **`self.features`**.
{% endhint %}

## What's next?

* 
