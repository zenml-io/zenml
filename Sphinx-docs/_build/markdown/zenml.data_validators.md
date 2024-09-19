# zenml.data_validators package

## Submodules

## zenml.data_validators.base_data_validator module

Base class for all ZenML data validators.

### *class* zenml.data_validators.base_data_validator.BaseDataValidator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent)

Base class for all ZenML data validators.

#### FLAVOR *: ClassVar[Type[[BaseDataValidatorFlavor](#zenml.data_validators.base_data_validator.BaseDataValidatorFlavor)]]*

#### NAME *: ClassVar[str]*

#### *property* config *: [BaseDataValidatorConfig](#zenml.data_validators.base_data_validator.BaseDataValidatorConfig)*

Returns the config of this data validator.

Returns:
: The config of this data validator.

#### data_profiling(dataset: Any, comparison_dataset: Any | None = None, profile_list: Sequence[Any] | None = None, \*\*kwargs: Any) → Any

Analyze one or more datasets and generate a data profile.

This method should be implemented by data validators that support
analyzing a dataset and generating a data profile (e.g. schema,
statistical summary, data distribution profile, validation
rules, data drift reports etc.).
The method should return a data profile object.

This method also accepts an optional second dataset argument to
accommodate different categories of data profiling, e.g.:

* profiles generated from a single dataset: schema inference, validation

rules inference, statistical profiles, data integrity reports
\* differential profiles that need a second dataset for comparison:
differential statistical profiles, data drift reports

Data validators that support generating multiple categories of data
profiles should also take in a profile_list argument that lists the
subset of profiles to be generated. If not supplied, the behavior is
implementation specific, but it is recommended to provide a good default
(e.g. a single default data profile type may be generated and returned,
or all available data profiles may be generated and returned as a single
result).

Args:
: dataset: Target dataset to be profiled.
  comparison_dataset: Optional second dataset to be used for data
  <br/>
  > comparison profiles (e.g data drift reports).
  <br/>
  profile_list: Optional list identifying the categories of data
  : profiles to be generated.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Implementation specific keyword arguments.

Raises:
: NotImplementedError: if data profiling is not supported by this
  : data validator.

#### data_validation(dataset: Any, comparison_dataset: Any | None = None, check_list: Sequence[Any] | None = None, \*\*kwargs: Any) → Any

Run data validation checks on a dataset.

This method should be implemented by data validators that support
running data quality checks an input dataset (e.g. data integrity
checks, data drift checks).

This method also accepts an optional second dataset argument to
accommodate different categories of data validation tests, e.g.:

* single dataset checks: data integrity checks (e.g. missing

values, conflicting labels, mixed data types etc.)
\* checks that compare two datasets: data drift checks (e.g. new labels,
feature drift, label drift etc.)

Data validators that support running multiple categories of data
integrity checks should also take in a check_list argument that
lists the subset of checks to be performed. If not supplied, the
behavior is implementation specific, but it is recommended to provide a
good default (e.g. a single default validation check may be performed,
or all available validation checks may be performed and their results
returned as a list of objects).

Args:
: dataset: Target dataset to be validated.
  comparison_dataset: Optional second dataset to be used for data
  <br/>
  > comparison checks (e.g data drift checks).
  <br/>
  check_list: Optional list identifying the data checks to
  : be performed.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Implementation specific keyword arguments.

Raises:
: NotImplementedError: if data validation is not
  : supported by this data validator.

#### *classmethod* get_active_data_validator() → [BaseDataValidator](#zenml.data_validators.base_data_validator.BaseDataValidator)

Get the data validator registered in the active stack.

Returns:
: The data validator registered in the active stack.

Raises:
: TypeError: if a data validator is not part of the
  : active stack.

#### model_validation(dataset: Any, model: Any, comparison_dataset: Any | None = None, check_list: Sequence[Any] | None = None, \*\*kwargs: Any) → Any

Run model validation checks.

This method should be implemented by data validators that support
running model validation checks (e.g. confusion matrix validation,
performance reports, model error analyses, etc).

Unlike data_validation, model validation checks require that a model
be present as an active component during the validation process.

This method also accepts an optional second dataset argument to
accommodate different categories of data validation tests, e.g.:

* single dataset tests: confusion matrix validation,

performance reports, model error analyses, etc
\* model comparison tests: tests that identify changes in a model
behavior by comparing how it performs on two different datasets.

Data validators that support running multiple categories of model
validation checks should also take in a check_list argument that
lists the subset of checks to be performed. If not supplied, the
behavior is implementation specific, but it is recommended to provide a
good default (e.g. a single default validation check may be performed,
or all available validation checks may be performed and their results
returned as a list of objects).

Args:
: dataset: Target dataset to be validated.
  model: Target model to be validated.
  comparison_dataset: Optional second dataset to be used for model
  <br/>
  > comparison checks (e.g model performance comparison checks).
  <br/>
  check_list: Optional list identifying the model validation checks to
  : be performed.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Implementation specific keyword arguments.

Raises:
: NotImplementedError: if model validation is not supported by this
  : data validator.

### *class* zenml.data_validators.base_data_validator.BaseDataValidatorConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for all data validators.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.data_validators.base_data_validator.BaseDataValidatorFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for data validator flavors.

#### *property* config_class *: Type[[BaseDataValidatorConfig](#zenml.data_validators.base_data_validator.BaseDataValidatorConfig)]*

Config class for data validator.

Returns:
: Config class for data validator.

#### *property* implementation_class *: Type[[BaseDataValidator](#zenml.data_validators.base_data_validator.BaseDataValidator)]*

Implementation for data validator.

Returns:
: Implementation for data validator.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

The type of the component.

Returns:
: The type of the component.

## Module contents

Data validators are stack components responsible for data profiling and validation.

### *class* zenml.data_validators.BaseDataValidator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent)

Base class for all ZenML data validators.

#### FLAVOR *: ClassVar[Type[[BaseDataValidatorFlavor](#zenml.data_validators.BaseDataValidatorFlavor)]]*

#### NAME *: ClassVar[str]*

#### *property* config *: [BaseDataValidatorConfig](#zenml.data_validators.base_data_validator.BaseDataValidatorConfig)*

Returns the config of this data validator.

Returns:
: The config of this data validator.

#### data_profiling(dataset: Any, comparison_dataset: Any | None = None, profile_list: Sequence[Any] | None = None, \*\*kwargs: Any) → Any

Analyze one or more datasets and generate a data profile.

This method should be implemented by data validators that support
analyzing a dataset and generating a data profile (e.g. schema,
statistical summary, data distribution profile, validation
rules, data drift reports etc.).
The method should return a data profile object.

This method also accepts an optional second dataset argument to
accommodate different categories of data profiling, e.g.:

* profiles generated from a single dataset: schema inference, validation

rules inference, statistical profiles, data integrity reports
\* differential profiles that need a second dataset for comparison:
differential statistical profiles, data drift reports

Data validators that support generating multiple categories of data
profiles should also take in a profile_list argument that lists the
subset of profiles to be generated. If not supplied, the behavior is
implementation specific, but it is recommended to provide a good default
(e.g. a single default data profile type may be generated and returned,
or all available data profiles may be generated and returned as a single
result).

Args:
: dataset: Target dataset to be profiled.
  comparison_dataset: Optional second dataset to be used for data
  <br/>
  > comparison profiles (e.g data drift reports).
  <br/>
  profile_list: Optional list identifying the categories of data
  : profiles to be generated.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Implementation specific keyword arguments.

Raises:
: NotImplementedError: if data profiling is not supported by this
  : data validator.

#### data_validation(dataset: Any, comparison_dataset: Any | None = None, check_list: Sequence[Any] | None = None, \*\*kwargs: Any) → Any

Run data validation checks on a dataset.

This method should be implemented by data validators that support
running data quality checks an input dataset (e.g. data integrity
checks, data drift checks).

This method also accepts an optional second dataset argument to
accommodate different categories of data validation tests, e.g.:

* single dataset checks: data integrity checks (e.g. missing

values, conflicting labels, mixed data types etc.)
\* checks that compare two datasets: data drift checks (e.g. new labels,
feature drift, label drift etc.)

Data validators that support running multiple categories of data
integrity checks should also take in a check_list argument that
lists the subset of checks to be performed. If not supplied, the
behavior is implementation specific, but it is recommended to provide a
good default (e.g. a single default validation check may be performed,
or all available validation checks may be performed and their results
returned as a list of objects).

Args:
: dataset: Target dataset to be validated.
  comparison_dataset: Optional second dataset to be used for data
  <br/>
  > comparison checks (e.g data drift checks).
  <br/>
  check_list: Optional list identifying the data checks to
  : be performed.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Implementation specific keyword arguments.

Raises:
: NotImplementedError: if data validation is not
  : supported by this data validator.

#### *classmethod* get_active_data_validator() → [BaseDataValidator](#zenml.data_validators.base_data_validator.BaseDataValidator)

Get the data validator registered in the active stack.

Returns:
: The data validator registered in the active stack.

Raises:
: TypeError: if a data validator is not part of the
  : active stack.

#### model_validation(dataset: Any, model: Any, comparison_dataset: Any | None = None, check_list: Sequence[Any] | None = None, \*\*kwargs: Any) → Any

Run model validation checks.

This method should be implemented by data validators that support
running model validation checks (e.g. confusion matrix validation,
performance reports, model error analyses, etc).

Unlike data_validation, model validation checks require that a model
be present as an active component during the validation process.

This method also accepts an optional second dataset argument to
accommodate different categories of data validation tests, e.g.:

* single dataset tests: confusion matrix validation,

performance reports, model error analyses, etc
\* model comparison tests: tests that identify changes in a model
behavior by comparing how it performs on two different datasets.

Data validators that support running multiple categories of model
validation checks should also take in a check_list argument that
lists the subset of checks to be performed. If not supplied, the
behavior is implementation specific, but it is recommended to provide a
good default (e.g. a single default validation check may be performed,
or all available validation checks may be performed and their results
returned as a list of objects).

Args:
: dataset: Target dataset to be validated.
  model: Target model to be validated.
  comparison_dataset: Optional second dataset to be used for model
  <br/>
  > comparison checks (e.g model performance comparison checks).
  <br/>
  check_list: Optional list identifying the model validation checks to
  : be performed.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Implementation specific keyword arguments.

Raises:
: NotImplementedError: if model validation is not supported by this
  : data validator.

### *class* zenml.data_validators.BaseDataValidatorFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for data validator flavors.

#### *property* config_class *: Type[[BaseDataValidatorConfig](#zenml.data_validators.base_data_validator.BaseDataValidatorConfig)]*

Config class for data validator.

Returns:
: Config class for data validator.

#### *property* implementation_class *: Type[[BaseDataValidator](#zenml.data_validators.base_data_validator.BaseDataValidator)]*

Implementation for data validator.

Returns:
: Implementation for data validator.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

The type of the component.

Returns:
: The type of the component.
