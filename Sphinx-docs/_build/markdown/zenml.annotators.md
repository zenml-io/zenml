# zenml.annotators package

## Submodules

## zenml.annotators.base_annotator module

Base class for ZenML annotator stack components.

### *class* zenml.annotators.base_annotator.BaseAnnotator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML annotators.

#### *abstract* add_dataset(\*\*kwargs: Any) → Any

Registers a dataset for annotation.

Args:
: ```
  **
  ```
  <br/>
  kwargs: keyword arguments.

Returns:
: The dataset or confirmation object on adding the dataset.

#### *property* config *: [BaseAnnotatorConfig](#zenml.annotators.base_annotator.BaseAnnotatorConfig)*

Returns the BaseAnnotatorConfig config.

Returns:
: The configuration.

#### *abstract* delete_dataset(\*\*kwargs: Any) → None

Deletes a dataset.

Args:
: ```
  **
  ```
  <br/>
  kwargs: keyword arguments.

#### *abstract* get_dataset(\*\*kwargs: Any) → Any

Gets the dataset with the given name.

Args:
: ```
  **
  ```
  <br/>
  kwargs: keyword arguments.

Returns:
: The dataset with the given name.

#### *abstract* get_dataset_names() → List[str]

Gets the names of the datasets currently available for annotation.

Returns:
: The names of the datasets currently available for annotation.

#### *abstract* get_dataset_stats(dataset_name: str) → Tuple[int, int]

Gets the statistics of a dataset.

Args:
: dataset_name: name of the dataset.

Returns:
: A tuple containing (labeled_task_count, unlabeled_task_count) for
  : the dataset.

#### *abstract* get_datasets() → List[Any]

Gets the datasets currently available for annotation.

Returns:
: The datasets currently available for annotation.

#### *abstract* get_labeled_data(\*\*kwargs: Any) → Any

Gets the labeled data for the given dataset.

Args:
: ```
  **
  ```
  <br/>
  kwargs: keyword arguments.

Returns:
: The labeled data for the given dataset.

#### *abstract* get_unlabeled_data(\*\*kwargs: str) → Any

Gets the unlabeled data for the given dataset.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments to pass to the Label Studio client.

Returns:
: The unlabeled data for the given dataset.

#### *abstract* get_url() → str

Gets the URL of the annotation interface.

Returns:
: The URL of the annotation interface.

#### *abstract* get_url_for_dataset(dataset_name: str) → str

Gets the URL of the annotation interface for a specific dataset.

Args:
: dataset_name: name of the dataset.

Returns:
: The URL of the dataset annotation interface.

#### *abstract* launch(\*\*kwargs: Any) → None

Launches the annotation interface.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments to pass to the
  : annotation client.

### *class* zenml.annotators.base_annotator.BaseAnnotatorConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for annotators.

Attributes:
: notebook_only: if the annotator can only be used in a notebook.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### notebook_only *: ClassVar[bool]* *= False*

### *class* zenml.annotators.base_annotator.BaseAnnotatorFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for annotator flavors.

#### *property* config_class *: Type[[BaseAnnotatorConfig](#zenml.annotators.base_annotator.BaseAnnotatorConfig)]*

Config class for this flavor.

Returns:
: The config class.

#### *abstract property* implementation_class *: Type[[BaseAnnotator](#zenml.annotators.base_annotator.BaseAnnotator)]*

Implementation class.

Returns:
: The implementation class.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

## Module contents

Initialization of the ZenML annotator stack component.

### *class* zenml.annotators.BaseAnnotator(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML annotators.

#### *abstract* add_dataset(\*\*kwargs: Any) → Any

Registers a dataset for annotation.

Args:
: ```
  **
  ```
  <br/>
  kwargs: keyword arguments.

Returns:
: The dataset or confirmation object on adding the dataset.

#### *property* config *: [BaseAnnotatorConfig](#zenml.annotators.base_annotator.BaseAnnotatorConfig)*

Returns the BaseAnnotatorConfig config.

Returns:
: The configuration.

#### *abstract* delete_dataset(\*\*kwargs: Any) → None

Deletes a dataset.

Args:
: ```
  **
  ```
  <br/>
  kwargs: keyword arguments.

#### *abstract* get_dataset(\*\*kwargs: Any) → Any

Gets the dataset with the given name.

Args:
: ```
  **
  ```
  <br/>
  kwargs: keyword arguments.

Returns:
: The dataset with the given name.

#### *abstract* get_dataset_names() → List[str]

Gets the names of the datasets currently available for annotation.

Returns:
: The names of the datasets currently available for annotation.

#### *abstract* get_dataset_stats(dataset_name: str) → Tuple[int, int]

Gets the statistics of a dataset.

Args:
: dataset_name: name of the dataset.

Returns:
: A tuple containing (labeled_task_count, unlabeled_task_count) for
  : the dataset.

#### *abstract* get_datasets() → List[Any]

Gets the datasets currently available for annotation.

Returns:
: The datasets currently available for annotation.

#### *abstract* get_labeled_data(\*\*kwargs: Any) → Any

Gets the labeled data for the given dataset.

Args:
: ```
  **
  ```
  <br/>
  kwargs: keyword arguments.

Returns:
: The labeled data for the given dataset.

#### *abstract* get_unlabeled_data(\*\*kwargs: str) → Any

Gets the unlabeled data for the given dataset.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments to pass to the Label Studio client.

Returns:
: The unlabeled data for the given dataset.

#### *abstract* get_url() → str

Gets the URL of the annotation interface.

Returns:
: The URL of the annotation interface.

#### *abstract* get_url_for_dataset(dataset_name: str) → str

Gets the URL of the annotation interface for a specific dataset.

Args:
: dataset_name: name of the dataset.

Returns:
: The URL of the dataset annotation interface.

#### *abstract* launch(\*\*kwargs: Any) → None

Launches the annotation interface.

Args:
: ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments to pass to the
  : annotation client.
