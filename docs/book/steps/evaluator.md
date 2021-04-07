# Evaluator

The Evaluator is executed right after [Trainer](trainer.md) step in the [TrainingPipeline](../pipelines/training-pipeline.md). The purpose of the evaluator step is to calculate relevant metrics to ascertain how well a trained model performed on un-seen data. It gives the user a chance to dig a bit deeper into the trained model and grasp a better understanding of it by conducting a post-training evaluation which features configurable slices and metrics.

## Standard Evaluators

There are some built-in evaluators available for use with ZenML.

### TFMAEvaluator

The TFMAEvaluator utilizes the [Tensorflow Model Analysis \(TFMA\)](https://github.com/tensorflow/model-analysis) to evaluate a model produced by the [TrainerStep](trainer.md). Structurally, it features two main parameters, namely `slices` and `metrics`.

* `slices` represent a list of string values, which hold the slicing columns. In more detail, the data 

  will be sliced based on the columns given in this list and the post-training evaluation will be 

  conducted on each slice.

* `metrics` define which metrics will be computed during the evaluation.

```text
Currently, the TFMAEvaluator only works with Trainers fully implementing the `TFBaseTrainerStep` interface. An example is the standard `tf_ff_trainer.FeedForwardTrainer` step.
```

#### Example

Let's start with a simple example. Imagine you are dealing with a simple regression task on a single label and you want to compute the `mean_squared_error` of your trained model on the eval dataset. Moreover, you want to do this not just on a slice of the entire eval dataset, but also on each category within the `native_country` feature within your eval dataset. In order to configure your pipeline accordingly, you can add the step:

```python
training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['native_country']],
                  metrics={'native_country': ['mean_squared_error']}))
```

Taking on a bit more complicated example, let us assume that the task handles more than one label, `age` and `income_bracket` and due to the nature of these labels, you want to apply different metrics to each label. Furthermore, considering the slices, you do not just want to slice on features, `native_country` and `marital_status`, but you also want to combine them to create a multi-feature slicing which features both the `native_country` and the `marital_status`:

```python
training_pipeline.add_evaluator(
    TFMAEvaluator(
        slices=[
            ['native_country'],
            ['marital_status'],
            ['native_country', 'marital_status']
        ],
        metrics={
            'age': ['mean_squared_error'],
            'income_bracket': ['binary_crossentropy']
        }
    ))
```

## Create custom evaluator

The mechanism to create a custom Evaluator will be published in more detail soon in this space. However, the details of this are currently being worked out and will be made available in future releases.

If you need this functionality earlier, then ping us on our [Slack](https://zenml.io/slack-invite) or [create an issue on GitHub](https://https://github.com/maiot-io/zenml) so that we know about it!

