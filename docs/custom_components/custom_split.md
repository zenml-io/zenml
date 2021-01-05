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

