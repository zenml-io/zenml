# zenml.integrations.evidently package

## Subpackages

* [zenml.integrations.evidently.data_validators package](zenml.integrations.evidently.data_validators.md)
  * [Submodules](zenml.integrations.evidently.data_validators.md#submodules)
  * [zenml.integrations.evidently.data_validators.evidently_data_validator module](zenml.integrations.evidently.data_validators.md#module-zenml.integrations.evidently.data_validators.evidently_data_validator)
    * [`EvidentlyDataValidator`](zenml.integrations.evidently.data_validators.md#zenml.integrations.evidently.data_validators.evidently_data_validator.EvidentlyDataValidator)
      * [`EvidentlyDataValidator.FLAVOR`](zenml.integrations.evidently.data_validators.md#zenml.integrations.evidently.data_validators.evidently_data_validator.EvidentlyDataValidator.FLAVOR)
      * [`EvidentlyDataValidator.NAME`](zenml.integrations.evidently.data_validators.md#zenml.integrations.evidently.data_validators.evidently_data_validator.EvidentlyDataValidator.NAME)
      * [`EvidentlyDataValidator.data_profiling()`](zenml.integrations.evidently.data_validators.md#zenml.integrations.evidently.data_validators.evidently_data_validator.EvidentlyDataValidator.data_profiling)
      * [`EvidentlyDataValidator.data_validation()`](zenml.integrations.evidently.data_validators.md#zenml.integrations.evidently.data_validators.evidently_data_validator.EvidentlyDataValidator.data_validation)
  * [Module contents](zenml.integrations.evidently.data_validators.md#module-zenml.integrations.evidently.data_validators)
    * [`EvidentlyDataValidator`](zenml.integrations.evidently.data_validators.md#zenml.integrations.evidently.data_validators.EvidentlyDataValidator)
      * [`EvidentlyDataValidator.FLAVOR`](zenml.integrations.evidently.data_validators.md#zenml.integrations.evidently.data_validators.EvidentlyDataValidator.FLAVOR)
      * [`EvidentlyDataValidator.NAME`](zenml.integrations.evidently.data_validators.md#zenml.integrations.evidently.data_validators.EvidentlyDataValidator.NAME)
      * [`EvidentlyDataValidator.data_profiling()`](zenml.integrations.evidently.data_validators.md#zenml.integrations.evidently.data_validators.EvidentlyDataValidator.data_profiling)
      * [`EvidentlyDataValidator.data_validation()`](zenml.integrations.evidently.data_validators.md#zenml.integrations.evidently.data_validators.EvidentlyDataValidator.data_validation)
* [zenml.integrations.evidently.flavors package](zenml.integrations.evidently.flavors.md)
  * [Submodules](zenml.integrations.evidently.flavors.md#submodules)
  * [zenml.integrations.evidently.flavors.evidently_data_validator_flavor module](zenml.integrations.evidently.flavors.md#module-zenml.integrations.evidently.flavors.evidently_data_validator_flavor)
    * [`EvidentlyDataValidatorFlavor`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.evidently_data_validator_flavor.EvidentlyDataValidatorFlavor)
      * [`EvidentlyDataValidatorFlavor.docs_url`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.evidently_data_validator_flavor.EvidentlyDataValidatorFlavor.docs_url)
      * [`EvidentlyDataValidatorFlavor.implementation_class`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.evidently_data_validator_flavor.EvidentlyDataValidatorFlavor.implementation_class)
      * [`EvidentlyDataValidatorFlavor.logo_url`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.evidently_data_validator_flavor.EvidentlyDataValidatorFlavor.logo_url)
      * [`EvidentlyDataValidatorFlavor.name`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.evidently_data_validator_flavor.EvidentlyDataValidatorFlavor.name)
      * [`EvidentlyDataValidatorFlavor.sdk_docs_url`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.evidently_data_validator_flavor.EvidentlyDataValidatorFlavor.sdk_docs_url)
  * [Module contents](zenml.integrations.evidently.flavors.md#module-zenml.integrations.evidently.flavors)
    * [`EvidentlyDataValidatorFlavor`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.EvidentlyDataValidatorFlavor)
      * [`EvidentlyDataValidatorFlavor.docs_url`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.EvidentlyDataValidatorFlavor.docs_url)
      * [`EvidentlyDataValidatorFlavor.implementation_class`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.EvidentlyDataValidatorFlavor.implementation_class)
      * [`EvidentlyDataValidatorFlavor.logo_url`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.EvidentlyDataValidatorFlavor.logo_url)
      * [`EvidentlyDataValidatorFlavor.name`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.EvidentlyDataValidatorFlavor.name)
      * [`EvidentlyDataValidatorFlavor.sdk_docs_url`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.EvidentlyDataValidatorFlavor.sdk_docs_url)
* [zenml.integrations.evidently.steps package](zenml.integrations.evidently.steps.md)
  * [Submodules](zenml.integrations.evidently.steps.md#submodules)
  * [zenml.integrations.evidently.steps.evidently_report module](zenml.integrations.evidently.steps.md#module-zenml.integrations.evidently.steps.evidently_report)
  * [zenml.integrations.evidently.steps.evidently_test module](zenml.integrations.evidently.steps.md#module-zenml.integrations.evidently.steps.evidently_test)
  * [Module contents](zenml.integrations.evidently.steps.md#module-zenml.integrations.evidently.steps)

## Submodules

## zenml.integrations.evidently.column_mapping module

ZenML representation of an Evidently column mapping.

### *class* zenml.integrations.evidently.column_mapping.EvidentlyColumnMapping(\*, target: str | None = None, prediction: Annotated[str | Sequence[str] | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = 'prediction', datetime: str | None = None, id: str | None = None, numerical_features: List[str] | None = None, categorical_features: List[str] | None = None, datetime_features: List[str] | None = None, target_names: List[str] | None = None, task: str | None = None, pos_label: Annotated[str | int | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = 1, text_features: List[str] | None = None)

Bases: `BaseModel`

Column mapping configuration for Evidently.

This class is a 1-to-1 serializable analogue of Evidently’s
ColumnMapping data type that can be used as a step configuration field
(see [https://docs.evidentlyai.com/user-guide/input-data/column-mapping](https://docs.evidentlyai.com/user-guide/input-data/column-mapping)).

Attributes:
: target: target column
  prediction: target column
  datetime: datetime column
  id: id column
  numerical_features: numerical features
  categorical_features: categorical features
  datetime_features: datetime features
  target_names: target column names
  task: model task
  pos_label: positive label
  text_features: text features

#### categorical_features *: List[str] | None*

#### datetime *: str | None*

#### datetime_features *: List[str] | None*

#### id *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'validate_assignment': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'categorical_features': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'datetime': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'datetime_features': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'numerical_features': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'pos_label': FieldInfo(annotation=Union[str, int, NoneType], required=False, default=1, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'prediction': FieldInfo(annotation=Union[str, Sequence[str], NoneType], required=False, default='prediction', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'target': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'target_names': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'task': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'text_features': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### numerical_features *: List[str] | None*

#### pos_label *: str | int | None*

#### prediction *: str | Sequence[str] | None*

#### target *: str | None*

#### target_names *: List[str] | None*

#### task *: str | None*

#### text_features *: List[str] | None*

#### to_evidently_column_mapping() → ColumnMapping

Convert this Pydantic object to an Evidently ColumnMapping object.

Returns:
: An Evidently column mapping converted from this Pydantic object.

## zenml.integrations.evidently.metrics module

ZenML declarative representation of Evidently Metrics.

### *class* zenml.integrations.evidently.metrics.EvidentlyMetricConfig(\*, class_path: str, parameters: Dict[str, Any] = None, is_generator: bool = False, columns: Annotated[str | List[str] | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, skip_id_column: bool = False)

Bases: `BaseModel`

Declarative Evidently Metric configuration.

This is a declarative representation of the configuration that goes into an
Evidently Metric, MetricPreset or Metric generator instance. We need this to
be able to store the configuration as part of a ZenML step parameter and
later instantiate the Evidently Metric from it.

This representation covers all 3 possible ways of configuring an Evidently
Metric or Metric-like object that can later be used in an Evidently Report:

1. A Metric (derived from the Metric class).
2. A MetricPreset (derived from the MetricPreset class).
3. A column Metric generator (derived from the BaseGenerator class).

Ideally, it should be possible to just pass a Metric or Metric-like
object to this class and have it automatically derive the configuration used
to instantiate it. Unfortunately, this is not possible because the Evidently
Metric classes are not designed in a way that allows us to extract the
constructor parameters from them in a generic way.

Attributes:
: class_path: The full class path of the Evidently Metric class.
  parameters: The parameters of the Evidently Metric.
  is_generator: Whether this is an Evidently column Metric generator.
  columns: The columns that the Evidently column Metric generator is
  <br/>
  > applied to. Only used if generator is True.
  <br/>
  skip_id_column: Whether to skip the ID column when applying the
  : Evidently Metric generator. Only used if generator is True.

#### class_path *: str*

#### columns *: str | List[str] | None*

#### *classmethod* default_metrics() → List[[EvidentlyMetricConfig](#zenml.integrations.evidently.metrics.EvidentlyMetricConfig)]

Default Evidently metric configurations.

Call this to fetch a default list of Evidently metrics to use in cases
where no metrics are explicitly configured for a data validator.
All available Evidently MetricPreset classes are used, except for the
TextOverviewPreset which requires a text column, which we don’t have
by default.

Returns:
: A list of EvidentlyMetricConfig objects to use as default metrics.

#### *static* get_metric_class(metric_name: str) → Metric | MetricPreset

Get the Evidently metric or metric preset class from a string.

Args:
: metric_name: The metric or metric preset class or full class
  : path.

Returns:
: The Evidently metric or metric preset class.

Raises:
: ValueError: If the name cannot be converted into a valid Evidently
  : metric or metric preset class.

#### is_generator *: bool*

#### *classmethod* metric(metric: Type[Metric] | Type[MetricPreset] | str, \*\*parameters: Any) → [EvidentlyMetricConfig](#zenml.integrations.evidently.metrics.EvidentlyMetricConfig)

Create a declarative configuration for an Evidently Metric.

Call this method to get a declarative representation for the
configuration of an Evidently Metric.

### Some examples

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyMetric

# Configure an Evidently MetricPreset using its class name
config = EvidentlyMetric.metric(“DataDriftPreset”)

```
``
```

```
`
```

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyMetric

# Configure an Evidently MetricPreset using its full class path
config = EvidentlyMetric.metric(

> “evidently.metric_preset.DataDriftPreset”

#### )

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyMetric

# Configure an Evidently Metric using its class and pass additional
# parameters
from evidently.metrics import ColumnSummaryMetric
config = EvidentlyMetric.metric(

> ColumnSummaryMetric, column_name=”age”

#### )

Args:
: metric: The Evidently Metric or MetricPreset class, class name or
  : class path.
  <br/>
  parameters: Additional optional parameters needed to instantiate the
  : Evidently Metric or MetricPreset.

Returns:
: The EvidentlyMetric declarative representation of the Evidently
  Metric configuration.

Raises:
: ValueError: If metric does not point to a valid Evidently Metric
  : or MetricPreset class.

#### *classmethod* metric_generator(metric: Type[Metric] | str, columns: str | List[str] | None = None, skip_id_column: bool = False, \*\*parameters: Any) → [EvidentlyMetricConfig](#zenml.integrations.evidently.metrics.EvidentlyMetricConfig)

Create a declarative configuration for an Evidently column Metric generator.

Call this method to get a declarative representation for the
configuration of an Evidently column Metric generator.

The columns, skip_id_column and parameters arguments will be
passed to the Evidently generate_column_metrics function:

- if columns is a list, it is interpreted as a list of column names.
- if columns is a string, it can be one of values:
  : - “all” - use all columns, including target/prediction columns
    - “num” - for numeric features
    - “cat” - for category features
    - “text” - for text features
    - “features” - for all features, not target/prediction columns.
- a None value is the same as “all”.

### Some examples

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyMetric

# Configure an Evidently Metric generator using a Metric class name
# and pass additional parameters
config = EvidentlyMetric.metric_generator(

> “ColumnQuantileMetric”, columns=”num”, quantile=0.5

#### )

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyMetric

# Configure an Evidently Metric generator using a full Metric class
# path
config = EvidentlyMetric.metric_generator(

> “evidently.metrics.ColumnSummaryMetric”, columns=[“age”, “name”]

#### )

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyMetric

# Configure an Evidently Metric generator using a Metric class
from evidently.metrics import ColumnDriftMetric
config = EvidentlyMetric.metric_generator(

> ColumnDriftMetric, columns=”all”, skip_id_column=True

#### )

Args:
: metric: The Evidently Metric class, class name or class path to use
  : for the generator.
  <br/>
  columns: The columns to apply the generator to. Takes the same
  : values that the Evidently generate_column_metrics function
    takes.
  <br/>
  skip_id_column: Whether to skip the ID column when applying the
  : generator.
  <br/>
  parameters: Additional optional parameters needed to instantiate the
  : Evidently Metric. These will be passed to the Evidently
    generate_column_metrics function.

Returns:
: The EvidentlyMetric declarative representation of the Evidently
  Metric generator configuration.

Raises:
: ValueError: If metric does not point to a valid Evidently Metric
  : or MetricPreset class.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'class_path': FieldInfo(annotation=str, required=True), 'columns': FieldInfo(annotation=Union[str, List[str], NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'is_generator': FieldInfo(annotation=bool, required=False, default=False), 'parameters': FieldInfo(annotation=Dict[str, Any], required=False, default_factory=dict), 'skip_id_column': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### parameters *: Dict[str, Any]*

#### skip_id_column *: bool*

#### to_evidently_metric() → Metric | MetricPreset | BaseGenerator

Create an Evidently Metric, MetricPreset or metric generator object.

Call this method to create an Evidently Metric, MetricPreset or metric
generator instance from its declarative representation.

Returns:
: The Evidently Metric, MetricPreset or metric generator object.

Raises:
: ValueError: If the Evidently Metric, MetricPreset or column metric
  : generator could not be instantiated.

## zenml.integrations.evidently.test_pipeline module

## zenml.integrations.evidently.tests module

ZenML declarative representation of Evidently Tests.

### *class* zenml.integrations.evidently.tests.EvidentlyTestConfig(\*, class_path: str, parameters: Dict[str, Any] = None, is_generator: bool = False, columns: Annotated[str | List[str] | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: `BaseModel`

Declarative Evidently Test configuration.

This is a declarative representation of the configuration that goes into an
Evidently Test, TestPreset or Test generator instance. We need this to
be able to store the configuration as part of a ZenML step parameter and
later instantiate the Evidently Test from it.

This representation covers all 3 possible ways of configuring an Evidently
Test or Test-like object that can later be used in an Evidently TestSuite:

1. A Test (derived from the Test class).
2. A TestPreset (derived from the TestPreset class).
3. A column Test generator (derived from the BaseGenerator class).

Ideally, it should be possible to just pass a Test or Test-like
object to this class and have it automatically derive the configuration used
to instantiate it. Unfortunately, this is not possible because the Evidently
Test classes are not designed in a way that allows us to extract the
constructor parameters from them in a generic way.

Attributes:
: class_path: The full class path of the Evidently Test class.
  parameters: The parameters of the Evidently Test.
  is_generator: Whether this is an Evidently column Test generator.
  columns: The columns that the Evidently column Test generator is
  <br/>
  > applied to. Only used if generator is True.

#### class_path *: str*

#### columns *: str | List[str] | None*

#### *classmethod* default_tests() → List[[EvidentlyTestConfig](#zenml.integrations.evidently.tests.EvidentlyTestConfig)]

Default Evidently test configurations.

Call this to fetch a default list of Evidently tests to use in cases
where no tests are explicitly configured for a data validator.
All available Evidently TestPreset classes are used.

Returns:
: A list of EvidentlyTestConfig objects to use as default tests.

#### *static* get_test_class(test_name: str) → Test | TestPreset

Get the Evidently test or test preset class from a string.

Args:
: test_name: The test or test preset class or full class
  : path.

Returns:
: The Evidently test or test preset class.

Raises:
: ValueError: If the name cannot be converted into a valid Evidently
  : test or test preset class.

#### is_generator *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'class_path': FieldInfo(annotation=str, required=True), 'columns': FieldInfo(annotation=Union[str, List[str], NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'is_generator': FieldInfo(annotation=bool, required=False, default=False), 'parameters': FieldInfo(annotation=Dict[str, Any], required=False, default_factory=dict)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### parameters *: Dict[str, Any]*

#### *classmethod* test(test: Type[Test] | Type[TestPreset] | str, \*\*parameters: Any) → [EvidentlyTestConfig](#zenml.integrations.evidently.tests.EvidentlyTestConfig)

Create a declarative configuration for an Evidently Test.

Call this method to get a declarative representation for the
configuration of an Evidently Test.

### Some examples

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyTest

# Configure an Evidently TestPreset using its class name
config = EvidentlyTest.test(“DataDriftPreset”)

```
``
```

```
`
```

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyTest

# Configure an Evidently TestPreset using its full class path
config = EvidentlyTest.test(

> “evidently.test_preset.DataDriftPreset”

#### )

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyTest

# Configure an Evidently Test using its class and pass additional
# parameters
from evidently.tests import ColumnSummaryTest
config = EvidentlyTest.test(

> ColumnSummaryTest, column_name=”age”

#### )

Args:
: test: The Evidently Test or TestPreset class, class name or
  : class path.
  <br/>
  parameters: Additional optional parameters needed to instantiate the
  : Evidently Test or TestPreset.

Returns:
: The EvidentlyTest declarative representation of the Evidently
  Test configuration.

Raises:
: ValueError: If test does not point to a valid Evidently Test
  : or TestPreset class.

#### *classmethod* test_generator(test: Type[Test] | str, columns: str | List[str] | None = None, \*\*parameters: Any) → [EvidentlyTestConfig](#zenml.integrations.evidently.tests.EvidentlyTestConfig)

Create a declarative configuration for an Evidently column Test generator.

Call this method to get a declarative representation for the
configuration of an Evidently column Test generator.

The columns, parameters arguments will be
passed to the Evidently generate_column_tests function:

- if columns is a list, it is interpreted as a list of column names.
- if columns is a string, it can be one of values:
  : - “all” - use all columns, including target/prediction columns
    - “num” - for numeric features
    - “cat” - for category features
    - “text” - for text features
    - “features” - for all features, not target/prediction columns.
- a None value is the same as “all”.

### Some examples

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyTest

# Configure an Evidently Test generator using a Test class name
# and pass additional parameters
config = EvidentlyTest.test_generator(

> “TestColumnValueMin”, columns=”num”, gt=0.5

#### )

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyTest

# Configure an Evidently Test generator using a full Test class
# path
config = EvidentlyTest.test_generator(

> “evidently.tests.TestColumnShareOfMissingValues”, columns=[“age”, “name”]

#### )

```
``
```

```
`
```

python
from zenml.integrations.evidently.data_validators import EvidentlyTest

# Configure an Evidently Test generator using a Test class
from evidently.tests import TestColumnQuantile
config = EvidentlyTest.test_generator(

> TestColumnQuantile, columns=”all”, quantile=0.5

#### )

Args:
: test: The Evidently Test class, class name or class path to use
  : for the generator.
  <br/>
  columns: The columns to apply the generator to. Takes the same
  : values that the Evidently generate_column_tests function
    takes.
  <br/>
  parameters: Additional optional parameters needed to instantiate the
  : Evidently Test. These will be passed to the Evidently
    generate_column_tests function.

Returns:
: The EvidentlyTest declarative representation of the Evidently
  Test generator configuration.

Raises:
: ValueError: If test does not point to a valid Evidently Test
  : or TestPreset class.

#### to_evidently_test() → Test | TestPreset | BaseGenerator

Create an Evidently Test, TestPreset or test generator object.

Call this method to create an Evidently Test, TestPreset or test
generator instance from its declarative representation.

Returns:
: The Evidently Test, TestPreset or test generator object.

Raises:
: ValueError: If the Evidently Test, TestPreset or column test
  : generator could not be instantiated.

## Module contents

Initialization of the Evidently integration.

The Evidently integration provides a way to monitor your models in production.
It includes a way to detect data drift and different kinds of model performance
issues.

The results of Evidently calculations can either be exported as an interactive
dashboard (visualized as an html file or in your Jupyter notebook), or as a JSON
file.

### *class* zenml.integrations.evidently.EvidentlyIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

[Evidently]([https://github.com/evidentlyai/evidently](https://github.com/evidentlyai/evidently)) integration for ZenML.

#### NAME *= 'evidently'*

#### REQUIREMENTS *: List[str]* *= ['evidently>=0.4.16,<=0.4.22', 'tenacity!=8.4.0']*

#### REQUIREMENTS_IGNORED_ON_UNINSTALL *: List[str]* *= ['tenacity', 'pandas']*

#### *classmethod* flavors() → List[Type[[Flavor](zenml.stack.md#zenml.stack.flavor.Flavor)]]

Declare the stack component flavors for the Great Expectations integration.

Returns:
: List of stack component flavors for this integration.

#### *classmethod* get_requirements(target_os: str | None = None) → List[str]

Method to get the requirements for the integration.

Args:
: target_os: The target operating system to get the requirements for.

Returns:
: A list of requirements.
