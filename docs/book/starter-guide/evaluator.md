# Choosing the evaluation metrics

## Overview



{% hint style="danger" %}
As of **0.3.6**, the mechanism to create custom evaluators is not supported. We are working hard to bring you this feature and if you would like to learn more about our progress you can check our [roadmap](../support/roadmap.md).  Meanwhile, you can use our built-in **TFMAEvaluator** or **AgnosticEvaluator**.
{% endhint %}

## The built-in `TFMAEvaluator`

```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.evaluator import AgnosticEvaluator


training_pipeline = TrainingPipeline()
 
...

training_pipeline.add_evaluator(
    TFMAEvaluator(slices=[['slice_feature']],
                  metrics={'output': ['binary_crossentropy', 
                                      'binary_accuracy']}))
   
...                            
```

### Configuring the `TFMAEvaluator`

## The built-in `AgnosticEvaluator`

```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.evaluator import AgnosticEvaluator

training_pipeline = TrainingPipeline()
 
...
 
training_pipeline.add_evaluator(
    AgnosticEvaluator(
        slices=[['slice_feature']],
        metrics=['mean_squared_error']
        prediction_key='output',
        label_key=label_name,))

...
```

### Configuring the `AgnosticEvaluator`

{% hint style="warning" %}

{% endhint %}

## What's next?

* 
