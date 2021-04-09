# Split

&lt;!DOCTYPE html&gt;

zenml.steps.split package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.steps.split.md)
  * * [zenml.steps.split package](zenml.steps.split.md)
      * [Submodules](zenml.steps.split.md#submodules)
      * [zenml.steps.split.base\_split\_step module](zenml.steps.split.md#module-zenml.steps.split.base_split_step)
      * [zenml.steps.split.categorical\_domain\_split\_step module](zenml.steps.split.md#module-zenml.steps.split.categorical_domain_split_step)
      * [zenml.steps.split.categorical\_ratio\_split\_step module](zenml.steps.split.md#module-zenml.steps.split.categorical_ratio_split_step)
      * [zenml.steps.split.constants module](zenml.steps.split.md#module-zenml.steps.split.constants)
      * [zenml.steps.split.no\_split\_step module](zenml.steps.split.md#module-zenml.steps.split.no_split_step)
      * [zenml.steps.split.random\_split module](zenml.steps.split.md#module-zenml.steps.split.random_split)
      * [zenml.steps.split.split\_step\_test module](zenml.steps.split.md#module-zenml.steps.split.split_step_test)
      * [zenml.steps.split.utils module](zenml.steps.split.md#module-zenml.steps.split.utils)
      * [zenml.steps.split.utils\_test module](zenml.steps.split.md#module-zenml.steps.split.utils_test)
      * [Module contents](zenml.steps.split.md#module-zenml.steps.split)
* [ « zenml.steps.s...](zenml.steps.sequencer/zenml.steps.sequencer.standard_sequencer/zenml.steps.sequencer.standard_sequencer.methods.md)
* [ zenml.steps.t... »](zenml.steps.tokenizer.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.split.rst.txt)

## zenml.steps.split package[¶](zenml.steps.split.md#zenml-steps-split-package)

### Submodules[¶](zenml.steps.split.md#submodules)

### zenml.steps.split.base\_split\_step module[¶](zenml.steps.split.md#module-zenml.steps.split.base_split_step)

 _class_ `zenml.steps.split.base_split_step.BaseSplit`\(_statistics: tensorflow\_metadata.proto.v0.statistics\_pb2.DatasetFeatureStatisticsList = None_, _schema: tensorflow\_metadata.proto.v0.schema\_pb2.Schema = None_, _\*\*kwargs_\)[¶](zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit)

Bases: [`zenml.steps.base_step.BaseStep`](./#zenml.steps.base_step.BaseStep)

Base split class. Each custom data split should derive from this. In order to define a custom split, override the base split’s partition\_fn method. `STEP_TYPE` _= 'split'_[¶](zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit.STEP_TYPE) `get_num_splits`\(\)[¶](zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit.get_num_splits)

Returns the total number of splits.Returns

A positive integer, the number of splits. _abstract_ `get_split_names`\(\) → List\[str\][¶](zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit.get_split_names)

Returns the names of the splits associated with this split step.Returns

A list of strings, which are the split names. _abstract_ `partition_fn`\(\)[¶](zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit.partition_fn)

Returns the partition function associated with the current split type, along with keyword arguments used in the signature of the partition function.

To be eligible in use in a Split Step, the partition\_fn has to adhere to the following design contract:

1. The signature is of the following type:

   > ```text
   > >>> def partition_fn(element, n, **kwargs) -> int,
   > ```
   >
   > where n is the number of splits;

2. The partition\_fn only returns signed integers i less than n, i.e.

   ```text
   0 ≤ i ≤ n - 1.
   ```

Returns

A tuple \(partition\_fn, kwargs\) of the partition function and its

additional keyword arguments \(see above\).

### zenml.steps.split.categorical\_domain\_split\_step module[¶](zenml.steps.split.md#module-zenml.steps.split.categorical_domain_split_step)

Implementation of the categorical domain split. _class_ `zenml.steps.split.categorical_domain_split_step.CategoricalDomainSplit`\(_categorical\_column: str_, _split\_map: Dict\[str, List\[Union\[str, int\]\]\]_, _unknown\_category\_policy: str = 'skip'_, _statistics=None_, _schema=None_\)[¶](zenml.steps.split.md#zenml.steps.split.categorical_domain_split_step.CategoricalDomainSplit)

Bases: [`zenml.steps.split.base_split_step.BaseSplit`](zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit)

Categorical domain split. Use this to split data based on values in a single categorical column. A categorical column is defined here as a column with finitely many values of type integer or string. `get_split_names`\(\) → List\[str\][¶](zenml.steps.split.md#zenml.steps.split.categorical_domain_split_step.CategoricalDomainSplit.get_split_names)

Returns the names of the splits associated with this split step.Returns

A list of strings, which are the split names. `partition_fn`\(\)[¶](zenml.steps.split.md#zenml.steps.split.categorical_domain_split_step.CategoricalDomainSplit.partition_fn)

Returns the partition function associated with the current split type, along with keyword arguments used in the signature of the partition function.

To be eligible in use in a Split Step, the partition\_fn has to adhere to the following design contract:

1. The signature is of the following type:

   > ```text
   > >>> def partition_fn(element, n, **kwargs) -> int,
   > ```
   >
   > where n is the number of splits;

2. The partition\_fn only returns signed integers i less than n, i.e.

   ```text
   0 ≤ i ≤ n - 1.
   ```

Returns

A tuple \(partition\_fn, kwargs\) of the partition function and its

additional keyword arguments \(see above\).

 `zenml.steps.split.categorical_domain_split_step.CategoricalPartitionFn`\(_element: Any_, _num\_partitions: int_, _categorical\_column: str_, _split\_map: Dict\[str, List\[Union\[str, int\]\]\]_, _unknown\_category\_policy: str_\) → int[¶](zenml.steps.split.md#zenml.steps.split.categorical_domain_split_step.CategoricalPartitionFn)

Function for a categorical split on data to be used in a beam.Partition. :param element: Data point, given as a tf.train.Example. :param num\_partitions: Number of splits, unused here. :param categorical\_column: Name of the categorical column in the data on which

> to perform the split.

Parameters

* **split\_map** – Dict {split\_name: \[category\_list\]} mapping the categorical values in categorical\_column to their respective splits.
* **unknown\_category\_policy** – Text, identifier on how to handle categorical values not present in the split\_map.

Returns

An integer n, where 0 ≤ n ≤ num\_partitions - 1. `zenml.steps.split.categorical_domain_split_step.lint_split_map`\(_split\_map: Dict\[str, List\[Union\[str, int\]\]\]_\)[¶](zenml.steps.split.md#zenml.steps.split.categorical_domain_split_step.lint_split_map)

Small utility to lint the split\_map

### zenml.steps.split.categorical\_ratio\_split\_step module[¶](zenml.steps.split.md#module-zenml.steps.split.categorical_ratio_split_step)

Implementation of the ratio-based categorical split. _class_ `zenml.steps.split.categorical_ratio_split_step.CategoricalRatioSplit`\(_categorical\_column: str_, _categories: List\[Union\[str, int\]\]_, _split\_ratio: Dict\[str, float\]_, _unknown\_category\_policy: str = 'skip'_, _statistics=None_, _schema=None_\)[¶](zenml.steps.split.md#zenml.steps.split.categorical_ratio_split_step.CategoricalRatioSplit)

Bases: [`zenml.steps.split.base_split_step.BaseSplit`](zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit)

Categorical ratio split. Use this to split data based on a list of values of interest in a single categorical column. A categorical column is defined here as a column with finitely many values of type integer or string. In contrast to the categorical domain split, here categorical values are assigned to different splits by the corresponding percentages, defined inside a split ratio object. `get_split_names`\(\) → List\[str\][¶](zenml.steps.split.md#zenml.steps.split.categorical_ratio_split_step.CategoricalRatioSplit.get_split_names)

Returns the names of the splits associated with this split step.Returns

A list of strings, which are the split names. `partition_fn`\(\)[¶](zenml.steps.split.md#zenml.steps.split.categorical_ratio_split_step.CategoricalRatioSplit.partition_fn)

Returns the partition function associated with the current split type, along with keyword arguments used in the signature of the partition function.

To be eligible in use in a Split Step, the partition\_fn has to adhere to the following design contract:

1. The signature is of the following type:

   > ```text
   > >>> def partition_fn(element, n, **kwargs) -> int,
   > ```
   >
   > where n is the number of splits;

2. The partition\_fn only returns signed integers i less than n, i.e.

   ```text
   0 ≤ i ≤ n - 1.
   ```

Returns

A tuple \(partition\_fn, kwargs\) of the partition function and its

additional keyword arguments \(see above\).

 `zenml.steps.split.categorical_ratio_split_step.lint_split_map`\(_split\_map: Dict\[str, float\]_\)[¶](zenml.steps.split.md#zenml.steps.split.categorical_ratio_split_step.lint_split_map)

Small utility to lint the split\_map

### zenml.steps.split.constants module[¶](zenml.steps.split.md#module-zenml.steps.split.constants)

### zenml.steps.split.no\_split\_step module[¶](zenml.steps.split.md#module-zenml.steps.split.no_split_step)

Implementation of the identity split. _class_ `zenml.steps.split.no_split_step.NoSplit`\(_statistics=None_, _schema=None_\)[¶](zenml.steps.split.md#zenml.steps.split.no_split_step.NoSplit)

Bases: [`zenml.steps.split.base_split_step.BaseSplit`](zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit)

No split function. Use this to pass your entire data forward completely unchanged. `get_split_names`\(\) → List\[str\][¶](zenml.steps.split.md#zenml.steps.split.no_split_step.NoSplit.get_split_names)

Returns the names of the splits associated with this split step.Returns

A list of strings, which are the split names. `partition_fn`\(\)[¶](zenml.steps.split.md#zenml.steps.split.no_split_step.NoSplit.partition_fn)

Returns the partition function associated with the current split type, along with keyword arguments used in the signature of the partition function.

To be eligible in use in a Split Step, the partition\_fn has to adhere to the following design contract:

1. The signature is of the following type:

   > ```text
   > >>> def partition_fn(element, n, **kwargs) -> int,
   > ```
   >
   > where n is the number of splits;

2. The partition\_fn only returns signed integers i less than n, i.e.

   ```text
   0 ≤ i ≤ n - 1.
   ```

Returns

A tuple \(partition\_fn, kwargs\) of the partition function and its

additional keyword arguments \(see above\).

 `zenml.steps.split.no_split_step.NoSplitPartitionFn`\(_element: Any_, _num\_partitions: int_\) → int[¶](zenml.steps.split.md#zenml.steps.split.no_split_step.NoSplitPartitionFn)

Function for no split on data; to be used in a beam.Partition. :param element: Data point, given as a tf.train.Example. :param num\_partitions: Number of splits, unused here.Returns

An integer n, where 0 ≤ n ≤ num\_partitions - 1.

### zenml.steps.split.random\_split module[¶](zenml.steps.split.md#module-zenml.steps.split.random_split)

Implementation of a random split of the input data set. _class_ `zenml.steps.split.random_split.RandomSplit`\(_split\_map: Dict\[str, float\]_, _statistics=None_, _schema=None_\)[¶](zenml.steps.split.md#zenml.steps.split.random_split.RandomSplit)

Bases: [`zenml.steps.split.base_split_step.BaseSplit`](zenml.steps.split.md#zenml.steps.split.base_split_step.BaseSplit)

Random split. Use this to randomly split data based on a cumulative distribution function defined by a split\_map dict. `get_split_names`\(\) → List\[str\][¶](zenml.steps.split.md#zenml.steps.split.random_split.RandomSplit.get_split_names)

Returns the names of the splits associated with this split step.Returns

A list of strings, which are the split names. `partition_fn`\(\)[¶](zenml.steps.split.md#zenml.steps.split.random_split.RandomSplit.partition_fn)

Returns the partition function associated with the current split type, along with keyword arguments used in the signature of the partition function.

To be eligible in use in a Split Step, the partition\_fn has to adhere to the following design contract:

1. The signature is of the following type:

   > ```text
   > >>> def partition_fn(element, n, **kwargs) -> int,
   > ```
   >
   > where n is the number of splits;

2. The partition\_fn only returns signed integers i less than n, i.e.

   ```text
   0 ≤ i ≤ n - 1.
   ```

Returns

A tuple \(partition\_fn, kwargs\) of the partition function and its

additional keyword arguments \(see above\).

 `zenml.steps.split.random_split.RandomSplitPartitionFn`\(_element: Any_, _num\_partitions: int_, _split\_map: Dict\[str, float\]_\) → int[¶](zenml.steps.split.md#zenml.steps.split.random_split.RandomSplitPartitionFn)

Function for a random split of the data; to be used in a beam.Partition. This function implements a simple random split algorithm by drawing integers from a categorical distribution defined by the values in split\_map.Parameters

* **element** – Data point, in format tf.train.Example.
* **num\_partitions** – Number of splits, unused here.
* **split\_map** – Dict mapping {split\_name: ratio of data in split}.

Returns

An integer n, where 0 ≤ n ≤ num\_partitions - 1. `zenml.steps.split.random_split.lint_split_map`\(_split\_map: Dict\[str, float\]_\)[¶](zenml.steps.split.md#zenml.steps.split.random_split.lint_split_map)

Small utility to lint the split\_map

### zenml.steps.split.split\_step\_test module[¶](zenml.steps.split.md#module-zenml.steps.split.split_step_test)

Tests for different split steps. `zenml.steps.split.split_step_test.create_random_dummy_data`\(\)[¶](zenml.steps.split.md#zenml.steps.split.split_step_test.create_random_dummy_data) `zenml.steps.split.split_step_test.create_structured_dummy_data`\(\)[¶](zenml.steps.split.md#zenml.steps.split.split_step_test.create_structured_dummy_data) `zenml.steps.split.split_step_test.test_categorical_domain_split`\(_create\_structured\_dummy\_data_\)[¶](zenml.steps.split.md#zenml.steps.split.split_step_test.test_categorical_domain_split) `zenml.steps.split.split_step_test.test_categorical_ratio_split`\(_create\_structured\_dummy\_data_\)[¶](zenml.steps.split.md#zenml.steps.split.split_step_test.test_categorical_ratio_split) `zenml.steps.split.split_step_test.test_categorical_split_ordering`\(_create\_structured\_dummy\_data_\)[¶](zenml.steps.split.md#zenml.steps.split.split_step_test.test_categorical_split_ordering) `zenml.steps.split.split_step_test.test_no_split`\(_create\_random\_dummy\_data_\)[¶](zenml.steps.split.md#zenml.steps.split.split_step_test.test_no_split) `zenml.steps.split.split_step_test.test_random_split`\(_create\_random\_dummy\_data_\)[¶](zenml.steps.split.md#zenml.steps.split.split_step_test.test_random_split)

### zenml.steps.split.utils module[¶](zenml.steps.split.md#module-zenml.steps.split.utils)

Some split step utilities are implemented here. `zenml.steps.split.utils.get_categorical_value`\(_example: tensorflow.core.example.example\_pb2.Example_, _cat\_col: str_\)[¶](zenml.steps.split.md#zenml.steps.split.utils.get_categorical_value)

Helper function to get the categorical value from a tf.train.Example.Parameters

* **example** – tf.train.Example, data point in proto format.
* **cat\_col** – Name of the categorical feature of which to extract the
* **from.** \(_value_\) –

Returns

The categorical value found in the cat\_col feature inside the tf.train.Example.Return type

valueRaises

* **AssertionError** – If the cat\_col feature is not present in the
* **tf.train.Example.** –

 `zenml.steps.split.utils.partition_cat_list`\(_cat\_list: List\[Union\[str, int\]\]_, _c\_ratio: Dict\[str, float\]_\)[¶](zenml.steps.split.md#zenml.steps.split.utils.partition_cat_list)

Helper to split a category list by the entries in a category split dict.Parameters

* **cat\_list** – List of categorical values found in the categorical column.
* **c\_ratio** – Dict {fold: ratio} mapping the ratio of all categories to split folds.

Returns

Dict {fold: categorical\_list} mapping lists of categorical

values in the data to their designated split folds.

Return type

cat\_dict

### zenml.steps.split.utils\_test module[¶](zenml.steps.split.md#module-zenml.steps.split.utils_test)

Split step utils tests. `zenml.steps.split.utils_test.test_get_categorical_value`\(\)[¶](zenml.steps.split.md#zenml.steps.split.utils_test.test_get_categorical_value) `zenml.steps.split.utils_test.test_partition_cat_list`\(\)[¶](zenml.steps.split.md#zenml.steps.split.utils_test.test_partition_cat_list)

### Module contents[¶](zenml.steps.split.md#module-zenml.steps.split)

 [Back to top](zenml.steps.split.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


