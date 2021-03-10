# Data splits in ZenML

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

## Getting started with split steps

### The random split

The simplest possible way to split your data is the **random split**. This is usually a good option for when you do not
have any special features that need careful selection, enough data is available, and the distribution of categorical
values in the data is not too skewed. Defining a random split in ZenML is as easy as the following piece of code:

```
from zenml.steps.split import RandomSplit

split = RandomSplit(split_map={"train": 0.5, "eval":0.5})

my_pipeline.add_split(split)
```

That was not too bad! Let us take a closer look. The `split_map` argument passed to the RandomSplit constructor simply
maps the names of your data splits to their respective data percentages. The above split configuration randomly assigns
50% of all data points to the `train` set and 50% to the `eval` set. The last line in the block above adds the split to
your pipeline object.

### The categorical split

Now we turn to a slightly different use case. Suppose you have a very interesting categorical attribute in your data
that you want to investigate further. A categorical attribute is defined here as a data feature either of type string or
integer, which can assume only finitely many values.

If you want to partition your data based on the values of your categorical column of interest, then ZenML exposes the
CategoricalSplit as the tool of choice for you. You can define a categorical split in two ways, either by assigning
categories to splits by hand or by percentage (like in the random split above).

#### 1. Creating a categorical domain split

The first way of defining a categorical split is by explicitly assigning all values in the _categorical domain_ into
different data splits. By the word categorical domain, we mean the set of all possible values that your categorical
feature can take. This approach gives you the most freedom in defining your split. You can define a categorical
domain-based split as such:

```
from zenml.steps.split import CategoricalDomainSplit

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

An important thing to note is the `unknown_category_policy` flag. This setting controls how categorical values are
handled that appear in the data but were not specified in the `split_map` argument on construction. A value of `"skip"`
denotes that those categories are meant to be discarded from the data set, and will not appear in any of the resulting
splits as a result.

Setting `unknown_category_policy` to any split name (i.e. so that it equals any of the keys in the split map) will
assign any categorical values not in the split map to that particular split. For
example, `unknown_category_policy="train"` will assign any unknown categorical value to the `"train"` split.

#### 2. Creating a categorical ratio split

The second way of specifying a categorical split is by supplying a list of categories of interest, and a split ratio
object that indicates what percentage of the categories in the list should go into which split.

Instantiating a categorical ratio-based split works as such:

```
from zenml.steps.split import CategoricalRatioSplit

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

### The importance of the `unknown_category_policy` flag

The categorical split is a powerful tool when you need to group your data by an important categorical feature. In
addition to data grouping, it serves the additional purpose of _data selection_: By using
the `unknown_category_policy="skip"` option, you are effectively filtering the data you pass on to your machine learning
pipeline based on your categorical attribute, by selecting only data with the specific values that you defined in your
split step. This mimics data selection mechanisms such as `WHERE` clauses in SQL, and can potentially not only save you
a lot of time and computational effort in pre-processing and model training, but also improve the predicting power of
your resulting model.

If you want to keep data with unknown / uninteresting categorical values out of your training/eval datasets, but you do
not want to just throw it away completely, either, then you can also make a completely new split with all excess data by
specifying your split_map like this:

```
split = CategoricalDomainSplit(categorical_column="my_categorical_column",
                               split_map = {"train": ["value_1", "value_2"],
                                            "eval": ["value_3", "value_4"],
                                            "test": []},
                               unknown_category_policy="test")
```

This way, all data with values for `my_categorical_column` other than `value_{1-4}` will go into the test split and
still be available for other components downstream.

## Summary

This concludes our small documentation piece on splitting data with ZenML. Both random, percentage-based splits and
categorical value-based splits are implemented in ZenML and immediately ready for use. If those do not meet your needs,
there is also the option of [creating your own custom split](custom-split.md) by overriding the `BaseSplit` class
methods. And with that, happy splitting!