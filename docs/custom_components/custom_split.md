# Adding custom splits in ZenML

## Motivation

Data splits are a well-known mechanic in Deep Learning workflows. The main reason behind splitting your data is to
validate that your trained model is indeed improving by obtaining its predictions and measuring its performance on
unseen data.

## Internals

In ZenML, we are applying the same split paradigm on datasets of potentially enormous sizes. As a result, any code that
we write for splitting data has to work for datasets of different sizes, regardless of whether they are in the order of
kilobytes or terabytes. In order to deliver this, we use a technology called **Apache Beam** that handles these
workloads by pipelining the operations necessary for splitting and applying it to the data.

You as the user do not have to worry about this, though - in fact, you can define your splitting logic using the ZenML
steps paradigm in about than five lines of code! The rest, including the pipelining and orchestration logic, is taken
care of internally.

ZenML supports some of the most common splitting schemes, like the random split and the categorical split, where you
split data based on the value of a categorical attribute.

# Getting started with split steps

## The random split

The simplest possible way to split your data is the **random split**. This is usually a good option for when you do not
have any special features that need careful selection, enough data is available, and the distribution of categorical
values in the data is not too skewed. Defining a random split in ZenML is as easy as the following piece of code:

```
from zenml.core.steps.split.random_split import RandomSplit

split = RandomSplit(split_map={"train": 0.5, "eval":0.5})

my_pipeline.add_split(split)
```

That was not too bad! Let us take a closer look. The `split_map` argument passed to the RandomSplit constructor simply
maps the names of your data splits to their respective data percentages. The above split configuration randomly assigns
50% of all data points to the `train` set and 50% to the `eval` set. The last line in the block above adds the split to
your pipeline object.

## The categorical split

Now we turn to a slightly different use case. Suppose you have a very interesting categorical attribute in your data
that you want to investigate further. A categorical attribute is defined here as a data feature either of type string or
integer, which can assume only finitely many values.

If you want to partition your data based on the values of your categorical column of interest, then ZenML exposes the
CategoricalSplit as the tool of choice for you. You can define a categorical split in two ways, either by assigning
categories to splits by hand or by percentage (like in the random split above).

### 1. Creating a categorical domain split

The first way of defining a categorical split is by explicitly assigning all values in the _categorical domain_ into
different data splits. By the word categorical domain, we mean the set of all possible values that your categorical
feature can take. This approach gives you the most freedom in defining your split. You can define a categorical
domain-based split as such:

```
from zenml.core.steps.split.categorical_domain_split_step import CategoricalDomainSplit

split = CategoricalDomainSplit(categorical_column="my_categorical_column",
                               split_map = {"train": ["value_1", "value_2"],
                                            "eval": ["value_3", "value_4"]},
                               unknown_category_policy="skip")

my_pipeline.add_split(split)
```

The domain split constructor takes three arguments. The first is the categorical column name, which is needed to know on
which attribute to split the data. Secondly, you need to also supply a `split_map` argument, just as in the random
split, but in this case it has a slightly different functionality. Here, for each split (marked by a key in the map),
the split map holds a list of categorical values that should be put into the corresponding split.

In the above example, all data points that have either `value_1` or `value_2` as the value in `my_categorical_column`
will be put into the `train` split, while all data points with either `value_3` or `value_4` will be put into the
`eval` split.

An important thing to note is the `unknown_category_policy="skip"` flag. This setting controls how categorical values
are handled that appear in the data but were not specified in the `split_map` argument on construction. A value
of `"skip"`
denotes that those categories are meant to be discarded from the data set, and will not appear in any of the resulting
splits as a result.

Setting `unknown_category_policy` to any split name (i.e. so that it equals any of the keys in the split map) will
assign any categorical values not in the split map to that particular split.

Example: `unknown_category_policy="train"` will assign any unknown categorical value to the "train" split.

### 2. Creating a categorical ratio split

The second way of specifying a categorical split is by supplying a list of categories of interest, and a split ratio
object that indicates what percentage of the categories in the list should go into which split.

Instantiating a categorical ratio-based split works as such:

```
from zenml.core.steps.split.categorical_ratio_split_step import CategoricalRatioSplit

split = CategoricalRatioSplit(categorical_column="color",
                              categories = ["red", "green", "blue", "yellow"],
                              split_ratio = {"train": 0.5,
                                             "eval": 0.5},
                              unknown_category_policy="skip")
           
my_pipeline.add_split(split)                   
```

In the above example, a categorical attribute called `color` is specified with `"red", "green", "blue"` and `"yellow"`
as the categorical values of interest. The `split_ratio` map indicates that these color values should be evenly split
into `train` and `eval` sets, with 50% of these categories assigned to either split. The `unknown_category_policy` flag
works just as in the domain split.

## Creating your own split logic

If the above options are not what you are looking for, there is also the option of implementing your own!

For this, ZenML provides the `BaseSplit` interface that you can subclass in a standard object-oriented manner to define
your own custom split logic.

```
from zenml.core.steps.split.base_split_step import BaseSplit

class MyCustomSplit(BaseSplit):

(... your custom split logic follows)
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
different depending on your target workload; we recommend that you infer them dynamically, e.g. from constructor
arguments that specify splits such as the `split_map` argument found in the builtin splits.

## Summary

This concludes our small documentation piece on splitting data with ZenML. Both random, percentage-based splits and
categorical value-based splits are implemented in ZenML and immediately ready for use. If those do not meet your needs,
there is also the option of creating your own custom split by overriding the `BaseSplit` class methods. And with that,
happy splitting!