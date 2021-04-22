# Choosing the evaluation metrics

## Overview

In order to conduct a fair evaluation of your pipeline, it is critical to put your trained model to test on a separated portion of your data. In **ZenML**, achieving this evaluation is done by the `BaseEvaluator` interface.

{% hint style="danger" %}
As of **0.3.6**, the mechanism to create custom evaluators is not supported. We are working hard to bring you this feature and if you would like to learn more about our progress you can check our [roadmap](../support/roadmap.md).  Meanwhile, you can use our built-in **TFMAEvaluator** or **AgnosticEvaluator**.
{% endhint %}

## Example: the built-in `TFMAEvaluator`

The `TFMAEvaluator` is built with TensorFlow models in mind. In other words, you can work with the `TFMAEvaluator`,  when your `TrainerStep` inherits the structure of the `TFBaseTrainerStep`.

As you can see from the code snippet above, if you want to work with the `TFMAEvaluator` all you need to do is to create an instance of the class and configure it. The test results will be saved as an artifact with the selected `slices` and `metrics`.

```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.evaluator import TFMAEvaluator

training_pipeline = TrainingPipeline()
 
...

training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['slice_feature']],
                  metrics={'output': ['binary_crossentropy', 
                                      'binary_accuracy']}))
   
...                            
```

## Example: the built-in `AgnosticEvaluator`

There are different ways to create and train models than TensorFlow and it is important to be able to provide an evaluation on any model regardless of its type. That is where the `AgnosticEvaluator` comes into play. It computes the metrics with the given slices, provided that the input, output and labels are already stored in an **artifact** by your `TrainerStep`.

```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.evaluator import AgnosticEvaluator

training_pipeline = TrainingPipeline()
 
...
 
training_pipeline.add_evaluator(
    AgnosticEvaluator(slices=[['slice_feature']],
                      metrics=['mean_squared_error']
                      prediction_key='output',
                      label_key='label'))

...
```

{% hint style="warning" %}
In order to be able to work with the `AgnosticEvaluator`, you need to make sure that the required features for the computation of the metrics are stored in a specific output artifact as flat `TFRecords` in your `TrainerStep`. In our built-in `TrainerStep`s, we have achieved this with the help of the helper method `test_fn` that is a part of the `TrainerStep` interface. You can find a good example of this approach in our PyTorch [`FeedForwardTrainer`](https://github.com/maiot-io/zenml/blob/main/zenml/steps/trainer/pytorch_trainers/torch_ff_trainer.py).
{% endhint %}

When it comes to configuring the `AgnosticEvaluator`, you need to provide a list of slicing metrics under `slices` and a list of performance metrics under `metrics`. Moreover, the key which holds the output of the model \(`prediction_key`\) and the key which holds the actual label \(`label_key`\) within the flat `TFRecords` need to be provided.

## What's next?

* You can take a look at how we used: 
  * the `TFMAEvaluator` in our [quickstart](https://github.com/maiot-io/zenml/tree/main/examples/quickstart)
  * the `AgnosticEvaluator` in our [pytorch example](https://github.com/maiot-io/zenml/tree/main/examples/pytorch)
* If you want to learn more about how to use the outcome of this **step** and visualize the results, you can take a look [here](post-training.md).
* If everything is clear, we can move on to the last step in our pipeline: [**the deployer step**](deployer.md)

