# Trainer
The Trainer defines the model and training loop within the [TrainingPipeline](../pipelines/training-pipeline.md).

## Standard trainers
A standard `TFFeedForwardTrainer` step is provided in the source code, which defines a simple feed-forward neural 
network in Tensorflow.

## Create custom trainers
In the case of the Trainer, the built-in methods are just convenience to access popular model types. Most of the 
times, custom model code is required. This is how to create custom trainer steps:

### Base Trainer
ZenML comes equipped with a `BaseTrainer` that all trainers should inherit from. This is how the interface 
looks like:

```python

    def run_fn(self):
        pass

    def input_fn(self,
                 file_pattern: List[Text],
                 tf_transform_output: tft.TFTransformOutput):
        pass

    def model_fn(train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset):
        pass
```
This doc section is incomplete. Please refer to the docstrings in source code while you wait to complete this section.

### Tensorflow-based Trainers

### PyTorch-based Trainers
Coming soon.

### Other libraries
Coming soon.

If you need the above functionalities earlier, then ping us on our [Slack](https://zenml.io/slack-invite) or [create an issue on GitHub](https://https://github.com/maiot-io/zenml) 
so that we know about it!