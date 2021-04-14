# Modifying the split

## Overview

In order to control the process of splitting a dataset, **ZenML** utilizes the so-called **`BaseSplit`** interface. In the definition of this interface, there are two main abstract methods called `partition_fn` and `get_split_names`.

```python
class BaseSplit(BaseStep):

    @abstractmethod
    def partition_fn(self):
        ...

    @abstractmethod
    def get_split_names(self) -> List[Text]:    
        ...
```

### partition\_fn

The goal of the `partition_fn` is to determine the right split selection for each incoming datapoint. It has two inputs, namely `element`, which denotes the incoming input in `tf.train.Example` format, and `n`, which denotes the number of potential splits, and it returns an integer indicating the selection of the split. The `partition_fn` has the following signature:

```python
def partition_fn(element, n) -> int:
```

### get\_split\_names

Through the method `get_split_names`, which returns a list of split names, the `BaseSplit` can prepare the output artifacts. Moreover, it helps us to compute the number of splits, which will be natively used when calling the `partition_fn` above.

```python
def get_split_names(self) -> List[Text]:
```

## A quick example: the built-in `RandomSplit` step

Now that the theoretical flow is in place, we can quickly give an example by using one of our built-in split-steps `RandomSplit` that splits data into smaller sets in a random manner.

{% hint style="info" %}
The following is an overview of the complete step. You can find the full code right [here](https://github.com/maiot-io/zenml/blob/main/zenml/steps/split/base_split_step.py).
{% endhint %}

```python
class RandomSplit(BaseSplit):
    """
    Select a random split for each incoming data point
    """    

    def partition_fn(self, 
                     element: Any,
                     num_partitions: int) -> int):
        probability_mass = np.cumsum(list(self.split_map.values()))
        max_value = probability_mass[-1]
        return bisect.bisect(probability_mass, np.random.uniform(0, max_value))

    def get_split_names(self) -> List[Text]:
        return list(self.split_map.keys())
```

We can now go ahead and use this split step in our pipeline:

```python
from zenml.pipelines import TrainingPipeline
from zenml.steps.split import RandomSplit

training_pipeline = TrainingPipeline()

...

training_pipeline.add_split(RandomSplit(split_map={'train': 0.7,
                                                   'eval': 0.2, 
                                                   'test': 0.1}))

...
```

{% hint style="warning" %}
**An important note here**: As you see from the code blocks that you see above, any input given to the constructor of a step will translate into an instance variable. So, when you want to use it you can use **`self`**, as we did with **`self.split_map`**.
{% endhint %}

As easy as that, we have a complete split step in our pipeline. If you have a task at hand which requires a more complicated logic to split your dataset, you can follow the same paradigm and write your own `partition_fn` and the `get_split_names`.

## What's next?

* You can find a more in-depth guide on how to create a custom split step here. \[WIP\]
* Additionally, here is a closer look at how the instance variables work in any step and what they represent. \[WIP\]
* The next step along the way is [data preprocessing](transform.md).

