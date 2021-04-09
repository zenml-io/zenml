# Modifying the split

In order to control the process of splitting a dataset, **ZenML** utilizes the **`BaseSplit`** interface. In the definition of this interface, there are two main abstract methods called `partition_fn` and `get_split_names`. 

```python
class BaseSplit(BaseStep):
    """
    Base split class. Each custom data split should derive from this.
    In order to define a custom split, override the base split's partition_fn
    method.
    """

    STEP_TYPE = StepTypes.split.name

    def __init__(self,
                 statistics: DatasetFeatureStatisticsList = None,
                 schema: Schema = None,
                 **kwargs):
        """
        Base Split constructor.
        Args:
            statistics: Parsed statistics output of a preceding StatisticsGen.
            schema: Parsed schema output of a preceding SchemaGen.
        """
        super().__init__(**kwargs)
        self.statistics = statistics
        self.schema = schema

    @abstractmethod
    def partition_fn(self):
        """
        Returns the partition function associated with the current split type,
        along with keyword arguments used in the signature of the partition
        function.
        To be eligible in use in a Split Step, the partition_fn has to adhere
        to the following design contract:
        1. The signature is of the following type:
            >>> def partition_fn(element, n, **kwargs) -> int,
            where n is the number of splits;
        2. The partition_fn only returns signed integers i less than n, i.e. ::
                0 ≤ i ≤ n - 1.
        Returns:
            A tuple (partition_fn, kwargs) of the partition function and its
             additional keyword arguments (see above).
        """
        pass

    @abstractmethod
    def get_split_names(self) -> List[Text]:
        """
        Returns the names of the splits associated with this split step.
        Returns:
            A list of strings, which are the split names.
        """
        pass

    def get_num_splits(self):
        """
        Returns the total number of splits.
        Returns:
            A positive integer, the number of splits.
        """
        return len(self.get_split_names())
```

Any split step in a ZenML training pipeline needs to implement this method:

```python
from zenml.steps.split import BaseSplit

class AnySplitStep(BaseSplit):

    def partition_fn(self):
        # the logic goes here
    
    def get_split_names(self) -> List[Text]:
        # the logic goes here
```

#### partition\_fn

The `partition_fn` has the following signature:

```python
def my_partition(element, n, **kwargs) -> int:
```

### A quick example: the built-in `RandomSplit` step

Now that the theoretical flow is in place, we can quickly give an example by building a partition function that splits data into `train` and `eval` sets based on whether an integer feature in the data is odd or even.

```python
import bisect
from typing import Text, List, Dict, Any

import numpy as np

from zenml.steps.split import BaseSplit


def lint_split_map(split_map: Dict[Text, float]):
    """Small utility to lint the split_map"""
    if len(split_map) <= 1:
        raise AssertionError('Please specify more than 1 split name in the '
                             'split_map!')

    if not all(isinstance(v, (int, float)) for v in split_map.values()):
        raise AssertionError("Only int or float values are allowed when "
                             "specifying a random split!")


def RandomSplitPartitionFn(element: Any,
                           num_partitions: int,
                           split_map: Dict[Text, float]) -> int:
    """
    Function for a random split of the data; to be used in a beam.Partition.
    This function implements a simple random split algorithm by drawing
    integers from a categorical distribution defined by the values in
    split_map.
    Args:
        element: Data point, in format tf.train.Example.
        num_partitions: Number of splits, unused here.
        split_map: Dict mapping {split_name: ratio of data in split}.
    Returns:
        An integer n, where 0 ≤ n ≤ num_partitions - 1.
    """

    # calculates probability mass of each split
    probability_mass = np.cumsum(list(split_map.values()))
    max_value = probability_mass[-1]

    return bisect.bisect(probability_mass, np.random.uniform(0, max_value))


class RandomSplit(BaseSplit):
    """
    Random split. Use this to randomly split data based on a cumulative
    distribution function defined by a split_map dict.
    """

    def __init__(
            self,
            split_map: Dict[Text, float],
            statistics=None,
            schema=None,
    ):
        """
        Random split constructor.
        Randomly split the data based on a cumulative distribution function
        defined by split_map.
        Example usage:
        # Split data randomly, but evenly into train, eval and test
        >>> split = RandomSplit(
        ... split_map = {"train": 0.334,
        ...              "eval": 0.333,
        ...              "test": 0.333})
        Here, each data split gets assigned about one third of the probability
        mass. The split is carried out by sampling from the categorical
        distribution defined by the values p_i in the split map, i.e.
        P(index = i) = p_i, i = 1,...,n ;
        where n is the number of splits defined in the split map. Hence, the
        values in the split map must sum up to 1. For more information, see
        https://en.wikipedia.org/wiki/Categorical_distribution.
        Args:
            statistics: Parsed statistics from a preceding StatisticsGen.
            schema: Parsed schema from a preceding SchemaGen.
            split_map: A dict { split_name: percentage of data in split }.
        """

        lint_split_map(split_map)
        self.split_map = split_map

        super().__init__(statistics=statistics,
                         schema=schema,
                         split_map=split_map)

    def partition_fn(self):
        return RandomSplitPartitionFn, {
            'split_map': self.split_map
        }

    def get_split_names(self) -> List[Text]:
        return list(self.split_map.keys())
```

Note that we could **not** have done the same logic with a categorical split, since the split above does not assume any knowledge about which integers are present beforehand. For a categorical split to work as built into ZenML, prior knowledge about the categorical domain of the feature has to be present.

