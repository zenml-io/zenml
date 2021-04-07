# Creating your own split logic

If the previous built-in options are not what you are looking for, there is also the option of implementing your own!

For this, ZenML provides the `BaseSplit` interface that you can subclass in a standard object-oriented manner to define
your own custom split logic.

```
from zenml.steps.split import BaseSplit

class MyCustomSplit(BaseSplit):

# your custom split logic follows
```

There are two main abstract methods that you have to implement to be able to use your custom split with ZenML's own
split component, `partition_fn` and `get_split_names`. The former returns your custom partition function along with its
keyword arguments for use in ZenML's split component. To be eligible in use in a Split Step, the partition function
needs to adhere to the following design contract:

1. The signature is of the following type:

```
def my_partition(element, n, **kwargs) -> int,
```

where n is the number of splits.

2. The partition_fn only returns signed integers i less than n, i.e. 0 ≤ i ≤ n - 1.

Then, the class method `partition_fn` returns the tuple `(my_partition, kwargs)` consisting of your custom partition
function and its keyword arguments.

The second method `get_split_names` needs to return a list of data split names used in your ZenML pipeline. These can be
different depending on your target workload.

## A quick example

Now that the theoretical flow is in place, we can quickly give an example by building a partition function that splits
data into `train` and `eval` sets based on whether an integer feature in the data is odd or even.

```
from zenml.steps.split import BaseSplit
from zenml.steps.split.utils import get_categorical_value

def OddEvenPartitionFn(element, num_partitions, int_feature):

    # get integer value of int_feature from the element
    int_value = get_categorical_value(element, int_feature)
    
    return int_value % 2

class OddEvenSplit(BaseSplit):
    def __init__(self, 
                 int_feature: Text,
                 statistics=None,
                 schema=None):
                 
        self.int_feature = int_feature
        super().__init__(statistics=statistics,
                         schema=schema,
                         int_feature=int_feature)
        
    def partition_fn(self):
        return OddEvenPartitionFn, {"int_feature": self.int_feature}
    
    def get_split_names(self):
        return ["train", "eval"]
```

Note that we could **not** have done the same logic with a categorical split, since the split above does not assume 
any knowledge about which integers are present beforehand. For a categorical split to work as built into ZenML, prior
knowledge about the categorical domain of the feature has to be present.
