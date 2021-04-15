# Adding your preprocessing logic

## Overview

For data processing, **ZenML** uses the **`BasePreprocesserStep`** interface. Within the context of this interface, there is a **single abstract method** called `preprocessing_fn`.

```python
class BasePreprocesserStep(BaseStep):

    @abstractmethod
    def preprocessing_fn(self, inputs: Dict):
        ...
```

### preprocessing\_fn

The main purpose of the `preprocessing_fn` is to define a transformation function that will be applied to each datapoint. It takes a single input dictionary where the keys are the feature names and the values are the tensors and it outputs the transformed datapoint in the same format as the input. The signature of the function is simply as follows:

```python
def preprocessing_fn(self, element):
```

## A quick example: the built-in `StandardPreprocesser` step

We can follow up on the definition by using a simplified version of our built-in **`StandardProcesser`** as a practical example. This `PreprocesserStep` handles not just the feature and label selection but also a wide variety of standard feature-level preprocessing techniques from the field of machine learning. If the behavior is not overwritten, it will apply a sane default filling and preprocessing technique based on the data type of the feature.

{% hint style="info" %}
The following is a simplified version of the complete step. You can find the full code right [here](https://github.com/maiot-io/zenml/blob/main/zenml/steps/preprocesser/standard_preprocesser/standard_preprocesser.py).
{% endhint %}

```python
class StandardPreprocesser(BasePreprocesserStep):

    def preprocessing_fn(self, inputs: Dict):
        """
        Standard preprocessing function
        Args:
            inputs: Dict with features
        Returns:
            output: Dict with transformed features
        """
        schema = infer_schema(inputs)

        output = {}
        for key, value in inputs.items():
            # Apply filling to the feature
            value = self.apply_filling(value, self.f_dict[key])

            if key in self.features or key in self.labels:
                # Apply preprocessing to the feature
                result = self.apply_transform(key, value, self.t_dict[key])
                result = tf.cast(result, dtype=tf.float32)
                
                # Feature and label selection
                if key in self.features:
                    output[naming_utils.transformed_feature_name(key)] = result
                if key in self.labels:
                    output[naming_utils.transformed_label_name(key)] = result
            
            output[key] = value
        return output
```

We can now go ahead and use this step in our pipeline:

```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.split import RandomSplit

training_pipeline = TrainingPipeline()

...

training_pipeline.add_preprocesser(
    StandardPreprocesser(
        features=['times_pregnant', 'pgc', 'dbp', 'tst', 
                  'insulin', 'bmi', 'pedigree', 'age'],
        labels=['has_diabetes'],
        overwrite={'has_diabetes': {'transform': [{'method': 'no_transform', 
                                                   'parameters': {}}]}}))

...
```

{% hint style="warning" %}
**An important note here**: As you see from the code blocks that you see above, any input given to the constructor of a step will translate into an instance variable. So, when you want to use it you can use **`self`**, as we did with **`self.features`**.
{% endhint %}

By implementing this abstract method, we now have a complete preprocesser step ready to be used in our pipeline. If you have a task at hand which requires a more complicated logic to preprocess your data, you can follow the same paradigm and write your own `preprocessing_fn`.

## What's next?

* Here is a closer look at how the instance variables work in any step and what they represent. \[WIP\]
* The next potential **step** within a `TrainingPipeline` is the `Trainer` [**step**](trainer.md).

