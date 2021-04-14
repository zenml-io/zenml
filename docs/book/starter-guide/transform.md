# Adding your preprocessing logic

## Overview

For data processing, **ZenML** usess the **`BasePreprocesserStep`** interface. Within the context of this interface, there is a single abstract method called `preprocessing_fn`.

```python
class BasePreprocesserStep(BaseStep):

    @abstractmethod
    def preprocessing_fn(self, inputs: Dict):
        ...
```

### preprocessing\_fn

```python
def partition_fn(element, n) -> int:
```

## A quick example: the built-in `StandardPreprocesser` step

{% hint style="info" %}
The following is an overview of the complete step. You can find the full code right [here](https://github.com/maiot-io/zenml/blob/main/zenml/steps/split/base_split_step.py).
{% endhint %}

```python
class StandardPreprocesser(BasePreprocesserStep):

    def preprocessing_fn(self, inputs: Dict):
        """
        Standard preprocessing function.
        Args:
            inputs: Dict mapping features to their respective data.
        Returns:
            output: Dict mapping transformed features to their respective
             transformed data.
        """
        schema = infer_schema(inputs)

        output = {}
        for key, value in inputs.items():
            if key not in self.f_dict:
                self.f_dict[key] = self.f_d_dict[schema[key]]
            value = self.apply_filling(value, self.f_dict[key])

            if key in self.features or key in self.labels:
                if key not in self.t_dict:
                    self.t_dict[key] = self.t_d_dict[schema[key]]
                result = self.apply_transform(key, value, self.t_dict[key])
                result = tf.cast(result, dtype=tf.float32)

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
        overwrite={'has_diabetes': {'transform': [{
                        'method': 'no_transform', 
                        'parameters': {}}]}}))

...
```

{% hint style="warning" %}
**An important note here**: As you see from the code blocks that you see above, any input given to the constructor of a step will translate into an instance variable. So, when you want to use it you can use **`self`**, as we did with **`self.features`**.
{% endhint %}

## What's next?

* 
