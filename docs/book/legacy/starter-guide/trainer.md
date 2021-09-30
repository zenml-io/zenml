# Creating your trainer

## Overview

In **ZenML**, the model training is achieved through an interface called the `BaseTrainerStep`. This specific step interface features **one main abstract method** \(run\_fn\) and **three helper methods** \(input\_fn, model\_fn, test\_fn\) _\*\*_that handle different processes within the model training workflow.

{% code title="\# Overview of the BaseTrainerStep" %}
```python
class BaseTrainerStep(BaseStep):

    def input_fn(self, *args, **kwargs):
        ...

    def model_fn(self, *args, **kwargs):
        ...

    def test_fn(self, *args, **kwargs):
        ...

    @abstractmethod    
    def run_fn(self):
        ...
```
{% endcode %}

### input\_fn

The `input_fn` is one of the aforementioned helper methods. As the name suggests, the motivation when using this function is to separate the flow of data preparation from the training. For instance, in the built-in `TrainerStep`s, it is designed to read the data using the parameter `file_pattern` which is a list containing the uris to the data and prepare a dataset that can be used with the implemented model architecture.

```python
def input_fn(self, *args, **kwargs)
```

### model\_fn

The next helper method in line is the `model_fn`. Similar to the `input_fn`, the aim of this method is to separate the model preparation from the training. The built-in `TrainerStep`s utilize this method to create an instance of the model architecture and return it.

```python
def model_fn(self, *args, **kwargs)
```

### test\_fn

The last helper method when designing a `BaseTrainerStep` is the `test_fn`. The goal here is to separate the computation of the test results once the training is completed. In the implementation of the built-in `TrainerStep`s, this method is using the trained model to compute the model output on the test splits and stores the results as an artifact.

{% hint style="warning" %}
Storing the test results within the context of a TrainerStep will be especially crucial in terms of post-training evaluation, because, it will allow us to utilize a model agnostic evaluator in the next step.
{% endhint %}

```python
  def test_fn(self, *args, **kwargs)
```

### run\_fn

The `run_fn` is the only abstract method and it is where everything related to the training comes together. Within the context of this method, the required datasets will be created, training will be conducted and the evaluation and tests will follow.

```python
@abstractmethod 
def run_fn(self)
```

## A quick example: the built-in `TorchFeedForwardTrainer` step

{% hint style="info" %}
The following is an overview of the complete **step**. You can find the full code right [here](https://github.com/zenml-io/zenml/blob/main/zenml/steps/trainer/pytorch_trainers/torch_ff_trainer.py,).
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
        Method which creates the datasets for model training
        """
        dataset = torch_utils.TFRecordTorchDataset(file_patterns,
                                                   self.schema)
        loader = torch.utils.data.DataLoader(dataset,
                                             batch_size=self.batch_size,
                                             drop_last=True)
        return loader

    def model_fn(self, train_dataset, eval_dataset):
        """
        Method which prepares the model instance
        """
        return BinaryClassifier()

    def test_fn(self, model, dataset):
        """
        Method which computes and stores the test results
        """
        model.eval()

        batch_list = []
        for x, y, raw in dataset:
            # start with an empty batch
            batch = {}

            # add the raw features with the transformed features and labels
            batch.update(x)
            batch.update(y)
            batch.update(raw)

            # finally, add the output of the model
            x_batch = torch.cat([v for v in x.values()], dim=-1)
            p = model(x_batch)

            if isinstance(p, torch.Tensor):
                batch.update({'output': p})
            elif isinstance(p, dict):
                batch.update(p)
            elif isinstance(p, list):
                batch.update(
                    {'output_{}'.format(i): v for i, v in enumerate(p)})
            else:
                raise TypeError('Unknown output format!')

            batch_list.append(batch)

        combined_batch = utils.combine_batch_results(batch_list)

        return combined_batch

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

We can now go ahead and use this **step** in our **pipeline**:

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

* You can learn more about how the instance variables work in any **step** here. \[WIP\]
* The next **step** within the `TrainingPipeline` is the [`Evaluator` **step**](evaluator.md).

