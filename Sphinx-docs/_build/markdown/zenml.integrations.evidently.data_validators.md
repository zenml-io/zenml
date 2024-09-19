# zenml.integrations.evidently.data_validators package

## Submodules

## zenml.integrations.evidently.data_validators.evidently_data_validator module

Implementation of the Evidently data validator.

### *class* zenml.integrations.evidently.data_validators.evidently_data_validator.EvidentlyDataValidator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseDataValidator`](zenml.data_validators.md#zenml.data_validators.base_data_validator.BaseDataValidator)

Evidently data validator stack component.

#### FLAVOR

alias of [`EvidentlyDataValidatorFlavor`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.evidently_data_validator_flavor.EvidentlyDataValidatorFlavor)

#### NAME *: ClassVar[str]* *= 'Evidently'*

#### data_profiling(dataset: DataFrame, comparison_dataset: DataFrame | None = None, profile_list: Sequence[[EvidentlyMetricConfig](zenml.integrations.evidently.md#zenml.integrations.evidently.metrics.EvidentlyMetricConfig)] | None = None, column_mapping: ColumnMapping | None = None, report_options: Sequence[Tuple[str, Dict[str, Any]]] = [], download_nltk_data: bool = False, \*\*kwargs: Any) → Report

Analyze a dataset and generate a data report with Evidently.

The method takes in an optional list of Evidently options to be passed
to the report constructor (report_options). Each element in the list must be
composed of two items: the first is a full class path of an Evidently
option dataclass, the second is a dictionary of kwargs with the actual
option parameters, e.g.:

```
``
```

```
`
```

python
options = [

> (
> : “evidently.options.ColorOptions”,{
>   : “primary_color”: “#5a86ad”,
>     “fill_color”: “#fff4f2”,
>     “zero_line_color”: “#016795”,
>     “current_data_color”: “#c292a1”,
>     “reference_data_color”: “#017b92”,
>   <br/>
>   }

> ),

### ]

Args:
: dataset: Target dataset to be profiled. When a comparison dataset
  : is provided, this dataset is considered the reference dataset.
  <br/>
  comparison_dataset: Optional dataset to be used for data profiles
  : that require a current dataset for comparison (e.g data drift
    profiles).
  <br/>
  profile_list: List of Evidently metric configurations to
  : be included in the report. If not provided, all available
    metric presets will be included.
  <br/>
  column_mapping: Properties of the DataFrame columns used
  report_options: List of Evidently options to be passed to the
  <br/>
  > report constructor.
  <br/>
  download_nltk_data: Whether to download NLTK data for text metrics.
  : Defaults to False.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Extra keyword arguments (unused).

Returns:
: The Evidently Report as JSON object and as HTML.

#### data_validation(dataset: Any, comparison_dataset: Any | None = None, check_list: Sequence[[EvidentlyTestConfig](zenml.integrations.evidently.md#zenml.integrations.evidently.tests.EvidentlyTestConfig)] | None = None, test_options: Sequence[Tuple[str, Dict[str, Any]]] = [], column_mapping: ColumnMapping | None = None, download_nltk_data: bool = False, \*\*kwargs: Any) → TestSuite

Validate a dataset with Evidently.

Args:
: dataset: Target dataset to be validated.
  comparison_dataset: Optional dataset to be used for data validation
  <br/>
  > that require a baseline for comparison (e.g data drift
  > validation).
  <br/>
  check_list: List of Evidently test configurations to be
  : included in the test suite. If not provided, all available
    test presets will be included.
  <br/>
  test_options: List of Evidently options to be passed to the
  : test suite constructor.
  <br/>
  column_mapping: Properties of the DataFrame columns used
  download_nltk_data: Whether to download NLTK data for text tests.
  <br/>
  > Defaults to False.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Extra keyword arguments (unused).

Returns:
: The Evidently Test Suite as JSON object and as HTML.

## Module contents

Initialization of the Evidently data validator for ZenML.

### *class* zenml.integrations.evidently.data_validators.EvidentlyDataValidator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`BaseDataValidator`](zenml.data_validators.md#zenml.data_validators.base_data_validator.BaseDataValidator)

Evidently data validator stack component.

#### FLAVOR

alias of [`EvidentlyDataValidatorFlavor`](zenml.integrations.evidently.flavors.md#zenml.integrations.evidently.flavors.evidently_data_validator_flavor.EvidentlyDataValidatorFlavor)

#### NAME *: ClassVar[str]* *= 'Evidently'*

#### data_profiling(dataset: DataFrame, comparison_dataset: DataFrame | None = None, profile_list: Sequence[[EvidentlyMetricConfig](zenml.integrations.evidently.md#zenml.integrations.evidently.metrics.EvidentlyMetricConfig)] | None = None, column_mapping: ColumnMapping | None = None, report_options: Sequence[Tuple[str, Dict[str, Any]]] = [], download_nltk_data: bool = False, \*\*kwargs: Any) → Report

Analyze a dataset and generate a data report with Evidently.

The method takes in an optional list of Evidently options to be passed
to the report constructor (report_options). Each element in the list must be
composed of two items: the first is a full class path of an Evidently
option dataclass, the second is a dictionary of kwargs with the actual
option parameters, e.g.:

```
``
```

```
`
```

python
options = [

> (
> : “evidently.options.ColorOptions”,{
>   : “primary_color”: “#5a86ad”,
>     “fill_color”: “#fff4f2”,
>     “zero_line_color”: “#016795”,
>     “current_data_color”: “#c292a1”,
>     “reference_data_color”: “#017b92”,
>   <br/>
>   }

> ),

### ]

Args:
: dataset: Target dataset to be profiled. When a comparison dataset
  : is provided, this dataset is considered the reference dataset.
  <br/>
  comparison_dataset: Optional dataset to be used for data profiles
  : that require a current dataset for comparison (e.g data drift
    profiles).
  <br/>
  profile_list: List of Evidently metric configurations to
  : be included in the report. If not provided, all available
    metric presets will be included.
  <br/>
  column_mapping: Properties of the DataFrame columns used
  report_options: List of Evidently options to be passed to the
  <br/>
  > report constructor.
  <br/>
  download_nltk_data: Whether to download NLTK data for text metrics.
  : Defaults to False.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Extra keyword arguments (unused).

Returns:
: The Evidently Report as JSON object and as HTML.

#### data_validation(dataset: Any, comparison_dataset: Any | None = None, check_list: Sequence[[EvidentlyTestConfig](zenml.integrations.evidently.md#zenml.integrations.evidently.tests.EvidentlyTestConfig)] | None = None, test_options: Sequence[Tuple[str, Dict[str, Any]]] = [], column_mapping: ColumnMapping | None = None, download_nltk_data: bool = False, \*\*kwargs: Any) → TestSuite

Validate a dataset with Evidently.

Args:
: dataset: Target dataset to be validated.
  comparison_dataset: Optional dataset to be used for data validation
  <br/>
  > that require a baseline for comparison (e.g data drift
  > validation).
  <br/>
  check_list: List of Evidently test configurations to be
  : included in the test suite. If not provided, all available
    test presets will be included.
  <br/>
  test_options: List of Evidently options to be passed to the
  : test suite constructor.
  <br/>
  column_mapping: Properties of the DataFrame columns used
  download_nltk_data: Whether to download NLTK data for text tests.
  <br/>
  > Defaults to False.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Extra keyword arguments (unused).

Returns:
: The Evidently Test Suite as JSON object and as HTML.
