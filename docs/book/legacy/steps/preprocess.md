# Preprocesser
The Preprocesser defines how data is transformed _before_ being sent to the [Trainer](trainer.md) for actual training.

## Standard Preprocesser
ZenML comes equipped with a standard preprocesser that exposes an interface to standard preprocessing operations.

### Tensorflow Transform
The Standard Preprocesser utilizes [Tensorflow Transform](https://www.tensorflow.org/tfx/transform/get_started) and the 
[Transform TFX component](https://www.tensorflow.org/tfx/guide/transform) under-the-hood. Therefore, 
all functionality enabled by Tensorflow Transform can be utilized, which covers basically all simple Tensorflow operations 
and special Tensorflow Transform helper functions for common preprocessing methods (like normalizing). Find out all 
functionalities that come out-of-box with Tensorflow Transform [here](https://www.tensorflow.org/tfx/transform/api_docs/python/tft).

Using Tensorflow Transform has also the advantage of scale, as it utilizes Apache Beam under-the-hood to distribute the preprocessing.

```{note}
In order to enable distributed computing, during pipeline run a user must had a Beam-compatible 
[Preprocessing Backend](../backends/processing-backends.md) like Google Dataflow.
```

#### Example
Coming soon.

## Create custom preprocesser
If the previous built-in options are not what you are looking for, there is also the option of implementing your own!

For this, ZenML provides the `BasePreprocesserStep` interface that one can subclass in a standard object-oriented manner to define
your own custom split logic.

```
from zenml.steps.preprocesser import BasePreprocesserStep

class MyCustomPreprocesser(BasePreprocesserStep):

    def preprocessing_fn(self, inputs: dict):
        outputs = {}
        
        # your preprocessing logic goes here
        
        return outputs
```
If you are familiar with Tensorflow Transform, this is the same [preprocessing_fn](https://www.tensorflow.org/tfx/tutorials/transform/census) 
function that you see when creating Tensorflow Transform pipelines. This is because that is exactly what is 
being used under the hood.

The `inputs` parameter in the `preprocessing_fn` is a dict where keys are feature names and values are 
Tensorflow tensors which represent the values of the features. `outputs` is a dict where keys are transformed 
feature names and values are tensors with the transformed values of the features.

The conversion of `inputs` to `outputs` can be performed by applying any Tensorflow or Tensorflow Transform based 
method to the values of `inputs` and then populating `outputs` with the results.

```{note}
Currently, the StandardPreprocesser is tied closely to Tensorflow Transform, and serves as a simple abstraction to it.
In future releases, this will be decoupled. Note that non-Tensorflow Trainers can still consume from artifacts produced 
by this Step. The PyTorch trainer example illustrates this well. 
```

### Example
Coming Soon. For now, please refer to extensive [Tensorflow Transform documentation](https://www.tensorflow.org/tfx/transform/get_started)
available online.