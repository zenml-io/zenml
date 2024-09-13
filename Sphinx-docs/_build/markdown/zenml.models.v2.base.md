# zenml.models.v2.base package

## Submodules

## zenml.models.v2.base.base module

Base model definitions.

### *class* zenml.models.v2.base.base.BaseDatedResponseBody(\*, created: datetime, updated: datetime)

Bases: [`BaseResponseBody`](#zenml.models.v2.base.base.BaseResponseBody)

Base body model for entities that track a creation and update timestamp.

Used as a base class for all body models associated with responses.
Features a creation and update timestamp.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseIdentifiedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseResponse[~AnyDatedBody, ~AnyMetadata, ~AnyResources]`, `Generic`[`AnyDatedBody`, `AnyMetadata`, `AnyResources`]

Base domain model for resources with DB representation.

#### body *: 'AnyBody' | None*

#### *property* created *: datetime*

The created property.

Returns:
: the value of the property.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for base response models.

Returns:
: The analytics metadata.

#### get_body() → AnyDatedBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access the
  : entity represented by this response.

#### get_hydrated_version() → [BaseIdentifiedResponse](#id208)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

Raises:
: IllegalOperationError: If the user lacks permission to access this
  : entity represented by this response.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyDatedBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* updated *: datetime*

The updated property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.base.BaseRequest

Bases: [`BaseZenModel`](#zenml.models.v2.base.base.BaseZenModel)

Base request model.

Used as a base class for all request models.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.base.base.BaseResponse(\*, body: AnyBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None)

Bases: [`BaseZenModel`](#zenml.models.v2.base.base.BaseZenModel), `Generic`[`AnyBody`, `AnyMetadata`, `AnyResources`]

Base domain model for all responses.

#### body *: AnyBody | None*

#### get_body() → AnyBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: RuntimeError: If the body was not included in the response.

#### get_hydrated_version() → [BaseResponse](#id248)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

#### get_resources() → AnyResources

Fetch the resources related to this entity.

Returns:
: The resources field of the response.

Raises:
: RuntimeError: If the resources field was not included in the response.

#### metadata *: AnyMetadata | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyBody, NoneType], required=False, default=None, title='The body of the resource.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### resources *: AnyResources | None*

### *class* zenml.models.v2.base.base.BaseResponseBody

Bases: [`BaseZenModel`](#zenml.models.v2.base.base.BaseZenModel)

Base body model.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.base.base.BaseResponseMetadata

Bases: [`BaseZenModel`](#zenml.models.v2.base.base.BaseZenModel)

Base metadata model.

Used as a base class for all metadata models associated with responses.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.base.base.BaseResponseResources(\*\*extra_data: Any)

Bases: [`BaseZenModel`](#zenml.models.v2.base.base.BaseZenModel)

Base resources model.

Used as a base class for all resource models associated with responses.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.base.base.BaseResponse(\*, body: AnyBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None)

Bases: [`BaseZenModel`](#zenml.models.v2.base.base.BaseZenModel), `Generic`[`AnyBody`, `AnyMetadata`, `AnyResources`]

Base domain model for all responses.

#### body *: AnyBody | None*

#### get_body() → AnyBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: RuntimeError: If the body was not included in the response.

#### get_hydrated_version() → [BaseResponse](#id248)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

#### get_resources() → AnyResources

Fetch the resources related to this entity.

Returns:
: The resources field of the response.

Raises:
: RuntimeError: If the resources field was not included in the response.

#### metadata *: AnyMetadata | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyBody, NoneType], required=False, default=None, title='The body of the resource.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### resources *: AnyResources | None*

### *class* zenml.models.v2.base.base.BaseResponse(\*, body: AnyBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None)

Bases: [`BaseZenModel`](#zenml.models.v2.base.base.BaseZenModel), `Generic`[`AnyBody`, `AnyMetadata`, `AnyResources`]

Base domain model for all responses.

#### body *: AnyBody | None*

#### get_body() → AnyBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: RuntimeError: If the body was not included in the response.

#### get_hydrated_version() → [BaseResponse](#id248)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

#### get_resources() → AnyResources

Fetch the resources related to this entity.

Returns:
: The resources field of the response.

Raises:
: RuntimeError: If the resources field was not included in the response.

#### metadata *: AnyMetadata | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyBody, NoneType], required=False, default=None, title='The body of the resource.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### resources *: AnyResources | None*

### *class* zenml.models.v2.base.base.BaseResponse(\*, body: AnyBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None)

Bases: [`BaseZenModel`](#zenml.models.v2.base.base.BaseZenModel), `Generic`[`AnyBody`, `AnyMetadata`, `AnyResources`]

Base domain model for all responses.

#### body *: AnyBody | None*

#### get_body() → AnyBody

Fetch the body of the entity.

Returns:
: The body field of the response.

Raises:
: RuntimeError: If the body was not included in the response.

#### get_hydrated_version() → [BaseResponse](#id248)

Abstract method to fetch the hydrated version of the model.

Raises:
: NotImplementedError: in case the method is not implemented.

#### get_metadata() → AnyMetadata

Fetch the metadata of the entity.

Returns:
: The metadata field of the response.

#### get_resources() → AnyResources

Fetch the resources related to this entity.

Returns:
: The resources field of the response.

Raises:
: RuntimeError: If the resources field was not included in the response.

#### metadata *: AnyMetadata | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyBody, NoneType], required=False, default=None, title='The body of the resource.'), 'metadata': FieldInfo(annotation=Union[~AnyMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'resources': FieldInfo(annotation=Union[~AnyResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### resources *: AnyResources | None*

### *class* zenml.models.v2.base.base.BaseUpdate

Bases: [`BaseZenModel`](#zenml.models.v2.base.base.BaseZenModel)

Base update model.

Used as a base class for all update models.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.base.base.BaseZenModel

Bases: [`YAMLSerializationMixin`](zenml.utils.md#zenml.utils.pydantic_utils.YAMLSerializationMixin), [`AnalyticsTrackedModelMixin`](zenml.analytics.md#zenml.analytics.models.AnalyticsTrackedModelMixin)

Base model class for all ZenML models.

This class is used as a base class for all ZenML models. It provides
functionality for tracking analytics events.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.base.base_plugin_flavor module

Plugin flavor model definitions.

### *class* zenml.models.v2.base.base_plugin_flavor.BasePluginFlavorResponse(\*, body: AnyPluginBody | None = None, metadata: AnyPluginMetadata | None = None, resources: AnyPluginResources | None = None, name: str, type: [PluginType](zenml.md#zenml.enums.PluginType), subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType))

Bases: `BaseResponse[~AnyPluginBody, ~AnyPluginMetadata, ~AnyPluginResources]`, `Generic`[`AnyPluginBody`, `AnyPluginMetadata`, `AnyPluginResources`]

Base response for all Plugin Flavors.

#### body *: 'AnyBody' | None*

#### get_hydrated_version() → [BasePluginFlavorResponse](#id272)

Abstract method to fetch the hydrated version of the model.

Returns:
: Hydrated version of the PluginFlavorResponse

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyPluginBody, NoneType], required=False, default=None, title='The body of the resource.'), 'metadata': FieldInfo(annotation=Union[~AnyPluginMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='Name of the flavor.'), 'resources': FieldInfo(annotation=Union[~AnyPluginResources, NoneType], required=False, default=None, title='The resources related to this resource.'), 'subtype': FieldInfo(annotation=PluginSubType, required=True, title='Subtype of the plugin.'), 'type': FieldInfo(annotation=PluginType, required=True, title='Type of the plugin.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### resources *: 'AnyResources' | None*

#### subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

#### type *: [PluginType](zenml.md#zenml.enums.PluginType)*

### *class* zenml.models.v2.base.base_plugin_flavor.BasePluginFlavorResponse(\*, body: AnyPluginBody | None = None, metadata: AnyPluginMetadata | None = None, resources: AnyPluginResources | None = None, name: str, type: [PluginType](zenml.md#zenml.enums.PluginType), subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType))

Bases: `BaseResponse[~AnyPluginBody, ~AnyPluginMetadata, ~AnyPluginResources]`, `Generic`[`AnyPluginBody`, `AnyPluginMetadata`, `AnyPluginResources`]

Base response for all Plugin Flavors.

#### body *: 'AnyBody' | None*

#### get_hydrated_version() → [BasePluginFlavorResponse](#id272)

Abstract method to fetch the hydrated version of the model.

Returns:
: Hydrated version of the PluginFlavorResponse

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyPluginBody, NoneType], required=False, default=None, title='The body of the resource.'), 'metadata': FieldInfo(annotation=Union[~AnyPluginMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='Name of the flavor.'), 'resources': FieldInfo(annotation=Union[~AnyPluginResources, NoneType], required=False, default=None, title='The resources related to this resource.'), 'subtype': FieldInfo(annotation=PluginSubType, required=True, title='Subtype of the plugin.'), 'type': FieldInfo(annotation=PluginType, required=True, title='Type of the plugin.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### resources *: 'AnyResources' | None*

#### subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

#### type *: [PluginType](zenml.md#zenml.enums.PluginType)*

### *class* zenml.models.v2.base.base_plugin_flavor.BasePluginFlavorResponse(\*, body: AnyPluginBody | None = None, metadata: AnyPluginMetadata | None = None, resources: AnyPluginResources | None = None, name: str, type: [PluginType](zenml.md#zenml.enums.PluginType), subtype: [PluginSubType](zenml.md#zenml.enums.PluginSubType))

Bases: `BaseResponse[~AnyPluginBody, ~AnyPluginMetadata, ~AnyPluginResources]`, `Generic`[`AnyPluginBody`, `AnyPluginMetadata`, `AnyPluginResources`]

Base response for all Plugin Flavors.

#### body *: 'AnyBody' | None*

#### get_hydrated_version() → [BasePluginFlavorResponse](#id272)

Abstract method to fetch the hydrated version of the model.

Returns:
: Hydrated version of the PluginFlavorResponse

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~AnyPluginBody, NoneType], required=False, default=None, title='The body of the resource.'), 'metadata': FieldInfo(annotation=Union[~AnyPluginMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'name': FieldInfo(annotation=str, required=True, title='Name of the flavor.'), 'resources': FieldInfo(annotation=Union[~AnyPluginResources, NoneType], required=False, default=None, title='The resources related to this resource.'), 'subtype': FieldInfo(annotation=PluginSubType, required=True, title='Subtype of the plugin.'), 'type': FieldInfo(annotation=PluginType, required=True, title='Type of the plugin.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### name *: str*

#### resources *: 'AnyResources' | None*

#### subtype *: [PluginSubType](zenml.md#zenml.enums.PluginSubType)*

#### type *: [PluginType](zenml.md#zenml.enums.PluginType)*

### *class* zenml.models.v2.base.base_plugin_flavor.BasePluginResponseBody

Bases: [`BaseResponseBody`](#zenml.models.v2.base.base.BaseResponseBody)

Response body for plugins.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.base.base_plugin_flavor.BasePluginResponseMetadata

Bases: [`BaseResponseMetadata`](#zenml.models.v2.base.base.BaseResponseMetadata)

Response metadata for plugins.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.base.base_plugin_flavor.BasePluginResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](#zenml.models.v2.base.base.BaseResponseResources)

Response resources for plugins.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.models.v2.base.filter module

Base filter model definitions.

### *class* zenml.models.v2.base.filter.BaseFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None)

Bases: `BaseModel`

Class to unify all filter, paginate and sort request parameters.

This Model allows fine-grained filtering, sorting and pagination of
resources.

Usage example for subclasses of this class:

```
``
```

\`
ResourceListModel(

> name=”contains:default”,
> workspace=”default”
> count_steps=”gte:5”
> sort_by=”created”,
> page=2,
> size=20

### )

#### API_MULTI_INPUT_PARAMS *: ClassVar[List[str]]* *= []*

#### CLI_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= []*

#### CUSTOM_SORTING_OPTIONS *: ClassVar[List[str]]* *= []*

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator']*

#### apply_filter(query: AnyQuery, table: Type[AnySchema]) → AnyQuery

Applies the filter to a query.

Args:
: query: The query to which to apply the filter.
  table: The query table.

Returns:
: The query with filter applied.

#### apply_sorting(query: AnyQuery, table: Type[AnySchema]) → AnyQuery

Apply sorting to the query.

Args:
: query: The query to which to apply the sorting.
  table: The query table.

Returns:
: The query with sorting applied.

#### *classmethod* check_field_annotation(k: str, type_: Any) → bool

Checks whether a model field has a certain annotation.

Args:
: k: The name of the field.
  <br/>
  ```
  type_
  ```
  <br/>
  : The type to check.

Raises:
: ValueError: if the model field within does not have an annotation.

Returns:
: True if the annotation of the field matches the given type, False
  otherwise.

#### configure_rbac(authenticated_user_id: UUID, \*\*column_allowed_ids: Set[UUID] | None) → None

Configure RBAC allowed column values.

Args:
: authenticated_user_id: ID of the authenticated user. All entities
  : owned by this user will be included.
  <br/>
  column_allowed_ids: Set of IDs per column to limit the query to.
  : If given, the remaining filters will be applied to entities
    within this set only. If None, the remaining filters will
    be applied to all entries in the table.

#### created *: datetime | str | None*

#### *classmethod* filter_ops(data: Any, validation_info: ValidationInfo) → Any

Wrapper method to handle the raw data.

Args:
: cls: the class handler
  data: the raw input data
  validation_info: the context of the validation.

Returns:
: the validated data

#### generate_filter(table: Type[SQLModel]) → ColumnElement[bool]

Generate the filter for the query.

Args:
: table: The Table that is being queried from.

Returns:
: The filter expression for the query.

Raises:
: RuntimeError: If a valid logical operator is not supplied.

#### generate_rbac_filter(table: Type[AnySchema]) → ColumnElement[bool] | None

Generates an optional RBAC filter.

Args:
: table: The query table.

Returns:
: The RBAC filter.

#### get_custom_filters() → List[ColumnElement[bool]]

Get custom filters.

This can be overridden by subclasses to define custom filters that are
not based on the columns of the underlying table.

Returns:
: A list of custom filters.

#### id *: UUID | str | None*

#### *classmethod* is_bool_field(k: str) → bool

Checks if it’s a bool field.

Args:
: k: The key to check.

Returns:
: True if the field is a bool field, False otherwise.

#### *classmethod* is_datetime_field(k: str) → bool

Checks if it’s a datetime field.

Args:
: k: The key to check.

Returns:
: True if the field is a datetime field, False otherwise.

#### *classmethod* is_int_field(k: str) → bool

Checks if it’s an int field.

Args:
: k: The key to check.

Returns:
: True if the field is an int field, False otherwise.

#### *classmethod* is_sort_by_field(k: str) → bool

Checks if it’s a sort by field.

Args:
: k: The key to check.

Returns:
: True if the field is a sort by field, False otherwise.

#### *classmethod* is_str_field(k: str) → bool

Checks if it’s a string field.

Args:
: k: The key to check.

Returns:
: True if the field is a string field, False otherwise.

#### *classmethod* is_uuid_field(k: str) → bool

Checks if it’s a UUID field.

Args:
: k: The key to check.

Returns:
: True if the field is a UUID field, False otherwise.

#### *property* list_of_filters *: List[[Filter](#zenml.models.v2.base.filter.Filter)]*

Converts the class variables into a list of usable Filter Models.

Returns:
: A list of Filter models.

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### *property* offset *: int*

Returns the offset needed for the query on the data persistence layer.

Returns:
: The offset for the query.

#### page *: int*

#### size *: int*

#### sort_by *: str*

#### *property* sorting_params *: Tuple[str, [SorterOps](zenml.md#zenml.enums.SorterOps)]*

Converts the class variables into a list of usable Filter Models.

Returns:
: A tuple of the column to sort by and the sorting operand.

#### updated *: datetime | str | None*

#### *classmethod* validate_sort_by(value: Any) → Any

Validate that the sort_column is a valid column with a valid operand.

Args:
: value: The sort_by field value.

Returns:
: The validated sort_by field value.

Raises:
: ValidationError: If the sort_by field is not a string.
  ValueError: If the resource can’t be sorted by this field.

### *class* zenml.models.v2.base.filter.BoolFilter(\*, operation: [GenericFilterOps](zenml.md#zenml.enums.GenericFilterOps), column: str, value: Any | None = None)

Bases: [`Filter`](#zenml.models.v2.base.filter.Filter)

Filter for all Boolean fields.

#### ALLOWED_OPS *: ClassVar[List[str]]* *= [GenericFilterOps.EQUALS]*

#### column *: str*

#### generate_query_conditions_from_column(column: Any) → Any

Generate query conditions for a boolean column.

Args:
: column: The boolean column of an SQLModel table on which to filter.

Returns:
: A list of query conditions.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'column': FieldInfo(annotation=str, required=True), 'operation': FieldInfo(annotation=GenericFilterOps, required=True), 'value': FieldInfo(annotation=Union[Any, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### operation *: [GenericFilterOps](zenml.md#zenml.enums.GenericFilterOps)*

#### value *: Any | None*

### *class* zenml.models.v2.base.filter.Filter(\*, operation: [GenericFilterOps](zenml.md#zenml.enums.GenericFilterOps), column: str, value: Any | None = None)

Bases: `BaseModel`, `ABC`

Filter for all fields.

A Filter is a combination of a column, a value that the user uses to
filter on this column and an operation to use. The easiest example
would be user equals aria with column=\`user\`, value=\`aria\` and the
operation=\`equals\`.

All subclasses of this class will support different sets of operations.
This operation set is defined in the ALLOWED_OPS class variable.

#### ALLOWED_OPS *: ClassVar[List[str]]* *= []*

#### column *: str*

#### generate_query_conditions(table: Type[SQLModel]) → ColumnElement[bool]

Generate the query conditions for the database.

This method converts the Filter class into an appropriate SQLModel
query condition, to be used when filtering on the Database.

Args:
: table: The SQLModel table to use for the query creation

Returns:
: A list of conditions that will be combined using the and operation

#### *abstract* generate_query_conditions_from_column(column: Any) → Any

Generate query conditions given the corresponding database column.

This method should be overridden by subclasses to define how each
supported operation in self.ALLOWED_OPS can be used to filter the
given column by self.value.

Args:
: column: The column of an SQLModel table on which to filter.

Returns:
: A list of query conditions.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'column': FieldInfo(annotation=str, required=True), 'operation': FieldInfo(annotation=GenericFilterOps, required=True), 'value': FieldInfo(annotation=Union[Any, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### operation *: [GenericFilterOps](zenml.md#zenml.enums.GenericFilterOps)*

#### *classmethod* validate_operation(value: Any) → Any

Validate that the operation is a valid op for the field type.

Args:
: value: The operation of this filter.

Returns:
: The operation if it is valid.

Raises:
: ValueError: If the operation is not valid for this field type.

#### value *: Any | None*

### *class* zenml.models.v2.base.filter.NumericFilter(\*, operation: [GenericFilterOps](zenml.md#zenml.enums.GenericFilterOps), column: str, value: Annotated[float | datetime, \_PydanticGeneralMetadata(union_mode='left_to_right')])

Bases: [`Filter`](#zenml.models.v2.base.filter.Filter)

Filter for all numeric fields.

#### ALLOWED_OPS *: ClassVar[List[str]]* *= [GenericFilterOps.EQUALS, GenericFilterOps.GT, GenericFilterOps.GTE, GenericFilterOps.LT, GenericFilterOps.LTE]*

#### column *: str*

#### generate_query_conditions_from_column(column: Any) → Any

Generate query conditions for a UUID column.

Args:
: column: The UUID column of an SQLModel table on which to filter.

Returns:
: A list of query conditions.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'column': FieldInfo(annotation=str, required=True), 'operation': FieldInfo(annotation=GenericFilterOps, required=True), 'value': FieldInfo(annotation=Union[float, datetime], required=True, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### operation *: [GenericFilterOps](zenml.md#zenml.enums.GenericFilterOps)*

#### value *: float | datetime*

### *class* zenml.models.v2.base.filter.StrFilter(\*, operation: [GenericFilterOps](zenml.md#zenml.enums.GenericFilterOps), column: str, value: Any | None = None)

Bases: [`Filter`](#zenml.models.v2.base.filter.Filter)

Filter for all string fields.

#### ALLOWED_OPS *: ClassVar[List[str]]* *= [GenericFilterOps.EQUALS, GenericFilterOps.STARTSWITH, GenericFilterOps.CONTAINS, GenericFilterOps.ENDSWITH]*

#### column *: str*

#### generate_query_conditions_from_column(column: Any) → Any

Generate query conditions for a string column.

Args:
: column: The string column of an SQLModel table on which to filter.

Returns:
: A list of query conditions.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'column': FieldInfo(annotation=str, required=True), 'operation': FieldInfo(annotation=GenericFilterOps, required=True), 'value': FieldInfo(annotation=Union[Any, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### operation *: [GenericFilterOps](zenml.md#zenml.enums.GenericFilterOps)*

#### value *: Any | None*

### *class* zenml.models.v2.base.filter.UUIDFilter(\*, operation: [GenericFilterOps](zenml.md#zenml.enums.GenericFilterOps), column: str, value: Any | None = None)

Bases: [`StrFilter`](#zenml.models.v2.base.filter.StrFilter)

Filter for all uuid fields which are mostly treated like strings.

#### column *: str*

#### generate_query_conditions_from_column(column: Any) → Any

Generate query conditions for a UUID column.

Args:
: column: The UUID column of an SQLModel table on which to filter.

Returns:
: A list of query conditions.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'column': FieldInfo(annotation=str, required=True), 'operation': FieldInfo(annotation=GenericFilterOps, required=True), 'value': FieldInfo(annotation=Union[Any, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### operation *: [GenericFilterOps](zenml.md#zenml.enums.GenericFilterOps)*

#### value *: Any | None*

## zenml.models.v2.base.page module

Page model definitions.

### *class* zenml.models.v2.base.page.Page(\*, index: Annotated[int, Gt(gt=0)], max_size: Annotated[int, Gt(gt=0)], total_pages: Annotated[int, Ge(ge=0)], total: Annotated[int, Ge(ge=0)], items: List[B])

Bases: `BaseModel`, `Generic`[`B`]

Return Model for List Models to accommodate pagination.

#### index *: Annotated[int, Gt(gt=0)]*

#### items *: List[B]*

#### max_size *: Annotated[int, Gt(gt=0)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'index': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'items': FieldInfo(annotation=List[~B], required=True), 'max_size': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'total': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)]), 'total_pages': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* size *: int*

Return the item count of the page.

Returns:
: The amount of items in the page.

#### total *: Annotated[int, Ge(ge=0)]*

#### total_pages *: Annotated[int, Ge(ge=0)]*

### *class* zenml.models.v2.base.page.Page(\*, index: Annotated[int, Gt(gt=0)], max_size: Annotated[int, Gt(gt=0)], total_pages: Annotated[int, Ge(ge=0)], total: Annotated[int, Ge(ge=0)], items: List[B])

Bases: `BaseModel`, `Generic`[`B`]

Return Model for List Models to accommodate pagination.

#### index *: Annotated[int, Gt(gt=0)]*

#### items *: List[B]*

#### max_size *: Annotated[int, Gt(gt=0)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'index': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'items': FieldInfo(annotation=List[~B], required=True), 'max_size': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'total': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)]), 'total_pages': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* size *: int*

Return the item count of the page.

Returns:
: The amount of items in the page.

#### total *: Annotated[int, Ge(ge=0)]*

#### total_pages *: Annotated[int, Ge(ge=0)]*

### *class* zenml.models.v2.base.page.Page(\*, index: Annotated[int, Gt(gt=0)], max_size: Annotated[int, Gt(gt=0)], total_pages: Annotated[int, Ge(ge=0)], total: Annotated[int, Ge(ge=0)], items: List[B])

Bases: `BaseModel`, `Generic`[`B`]

Return Model for List Models to accommodate pagination.

#### index *: Annotated[int, Gt(gt=0)]*

#### items *: List[B]*

#### max_size *: Annotated[int, Gt(gt=0)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'index': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'items': FieldInfo(annotation=List[~B], required=True), 'max_size': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'total': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)]), 'total_pages': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* size *: int*

Return the item count of the page.

Returns:
: The amount of items in the page.

#### total *: Annotated[int, Ge(ge=0)]*

#### total_pages *: Annotated[int, Ge(ge=0)]*

### *class* zenml.models.v2.base.page.Page(\*, index: Annotated[int, Gt(gt=0)], max_size: Annotated[int, Gt(gt=0)], total_pages: Annotated[int, Ge(ge=0)], total: Annotated[int, Ge(ge=0)], items: List[B])

Bases: `BaseModel`, `Generic`[`B`]

Return Model for List Models to accommodate pagination.

#### index *: Annotated[int, Gt(gt=0)]*

#### items *: List[B]*

#### max_size *: Annotated[int, Gt(gt=0)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'index': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'items': FieldInfo(annotation=List[~B], required=True), 'max_size': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'total': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)]), 'total_pages': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* size *: int*

Return the item count of the page.

Returns:
: The amount of items in the page.

#### total *: Annotated[int, Ge(ge=0)]*

#### total_pages *: Annotated[int, Ge(ge=0)]*

### *class* zenml.models.v2.base.page.Page(\*, index: Annotated[int, Gt(gt=0)], max_size: Annotated[int, Gt(gt=0)], total_pages: Annotated[int, Ge(ge=0)], total: Annotated[int, Ge(ge=0)], items: List[B])

Bases: `BaseModel`, `Generic`[`B`]

Return Model for List Models to accommodate pagination.

#### index *: Annotated[int, Gt(gt=0)]*

#### items *: List[B]*

#### max_size *: Annotated[int, Gt(gt=0)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'index': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'items': FieldInfo(annotation=List[~B], required=True), 'max_size': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'total': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)]), 'total_pages': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* size *: int*

Return the item count of the page.

Returns:
: The amount of items in the page.

#### total *: Annotated[int, Ge(ge=0)]*

#### total_pages *: Annotated[int, Ge(ge=0)]*

### *class* zenml.models.v2.base.page.Page(\*, index: Annotated[int, Gt(gt=0)], max_size: Annotated[int, Gt(gt=0)], total_pages: Annotated[int, Ge(ge=0)], total: Annotated[int, Ge(ge=0)], items: List[B])

Bases: `BaseModel`, `Generic`[`B`]

Return Model for List Models to accommodate pagination.

#### index *: Annotated[int, Gt(gt=0)]*

#### items *: List[B]*

#### max_size *: Annotated[int, Gt(gt=0)]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'index': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'items': FieldInfo(annotation=List[~B], required=True), 'max_size': FieldInfo(annotation=int, required=True, metadata=[Gt(gt=0)]), 'total': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)]), 'total_pages': FieldInfo(annotation=int, required=True, metadata=[Ge(ge=0)])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* size *: int*

Return the item count of the page.

Returns:
: The amount of items in the page.

#### total *: Annotated[int, Ge(ge=0)]*

#### total_pages *: Annotated[int, Ge(ge=0)]*

## zenml.models.v2.base.scoped module

Scoped model definitions.

### *class* zenml.models.v2.base.scoped.UserScopedFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_user: UUID | None = None)

Bases: [`BaseFilter`](#zenml.models.v2.base.filter.BaseFilter)

Model to enable advanced user-based scoping.

#### CLI_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['scope_user']*

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_user']*

#### apply_filter(query: AnyQuery, table: Type[AnySchema]) → AnyQuery

Applies the filter to a query.

Args:
: query: The query to which to apply the filter.
  table: The query table.

Returns:
: The query with filter applied.

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_user': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The user to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### page *: int*

#### scope_user *: UUID | None*

#### set_scope_user(user_id: UUID) → None

Set the user that is performing the filtering to scope the response.

Args:
: user_id: The user ID to scope the response to.

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.base.scoped.UserScopedRequest(\*, user: UUID)

Bases: [`BaseRequest`](#zenml.models.v2.base.base.BaseRequest)

Base user-owned request model.

Used as a base class for all domain models that are “owned” by a user.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for user scoped models.

Returns:
: The analytics metadata.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### user *: UUID*

### *class* zenml.models.v2.base.scoped.UserScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[~UserBody, ~UserMetadata, ~UserResources]`, `Generic`[`UserBody`, `UserMetadata`, `UserResources`]

Base user-owned model.

Used as a base class for all domain models that are “owned” by a user.

#### body *: 'AnyBody' | None*

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for user scoped models.

Returns:
: The analytics metadata.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~UserBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~UserMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~UserResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* user *: [UserResponse](zenml.models.md#zenml.models.UserResponse) | None*

The user property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.UserScopedResponseBody(\*, created: datetime, updated: datetime)

Bases: [`BaseDatedResponseBody`](#zenml.models.v2.base.base.BaseDatedResponseBody)

Base user-owned body.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[ForwardRef('UserResponse'), NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

#### user *: [UserResponse](zenml.models.md#zenml.models.UserResponse) | None*

### *class* zenml.models.v2.base.scoped.UserScopedResponseMetadata

Bases: [`BaseResponseMetadata`](#zenml.models.v2.base.base.BaseResponseMetadata)

Base user-owned metadata.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.base.scoped.UserScopedResponseResources(\*\*extra_data: Any)

Bases: [`BaseResponseResources`](#zenml.models.v2.base.base.BaseResponseResources)

Base class for all resource models associated with the user.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.base.scoped.UserScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[~UserBody, ~UserMetadata, ~UserResources]`, `Generic`[`UserBody`, `UserMetadata`, `UserResources`]

Base user-owned model.

Used as a base class for all domain models that are “owned” by a user.

#### body *: 'AnyBody' | None*

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for user scoped models.

Returns:
: The analytics metadata.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~UserBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~UserMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~UserResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* user *: [UserResponse](zenml.models.md#zenml.models.UserResponse) | None*

The user property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.UserScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[~UserBody, ~UserMetadata, ~UserResources]`, `Generic`[`UserBody`, `UserMetadata`, `UserResources`]

Base user-owned model.

Used as a base class for all domain models that are “owned” by a user.

#### body *: 'AnyBody' | None*

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for user scoped models.

Returns:
: The analytics metadata.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~UserBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~UserMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~UserResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* user *: [UserResponse](zenml.models.md#zenml.models.UserResponse) | None*

The user property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.UserScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `BaseIdentifiedResponse[~UserBody, ~UserMetadata, ~UserResources]`, `Generic`[`UserBody`, `UserMetadata`, `UserResources`]

Base user-owned model.

Used as a base class for all domain models that are “owned” by a user.

#### body *: 'AnyBody' | None*

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for user scoped models.

Returns:
: The analytics metadata.

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~UserBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~UserMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~UserResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* user *: [UserResponse](zenml.models.md#zenml.models.UserResponse) | None*

The user property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None)

Bases: [`BaseFilter`](#zenml.models.v2.base.filter.BaseFilter)

Model to enable advanced scoping with workspace.

#### CLI_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['scope_workspace']*

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace']*

#### apply_filter(query: AnyQuery, table: Type[AnySchema]) → AnyQuery

Applies the filter to a query.

Args:
: query: The query to which to apply the filter.
  table: The query table.

Returns:
: The query with filter applied.

#### created *: datetime | str | None*

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### page *: int*

#### scope_workspace *: UUID | None*

#### set_scope_workspace(workspace_id: UUID) → None

Set the workspace to scope this response.

Args:
: workspace_id: The workspace to scope this response to.

#### size *: int*

#### sort_by *: str*

#### updated *: datetime | str | None*

### *class* zenml.models.v2.base.scoped.WorkspaceScopedRequest(\*, user: UUID, workspace: UUID)

Bases: [`UserScopedRequest`](#zenml.models.v2.base.scoped.UserScopedRequest)

Base workspace-scoped request domain model.

Used as a base class for all domain models that are workspace-scoped.

#### get_analytics_metadata() → Dict[str, Any]

Fetches the analytics metadata for workspace scoped models.

Returns:
: The analytics metadata.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'user': FieldInfo(annotation=UUID, required=True, title='The id of the user that created this resource.'), 'workspace': FieldInfo(annotation=UUID, required=True, title='The workspace to which this resource belongs.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### user *: UUID*

#### workspace *: UUID*

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponseBody(\*, created: datetime, updated: datetime, user: [UserResponse](zenml.models.v2.core.md#zenml.models.v2.core.user.UserResponse) | None = None)

Bases: [`UserScopedResponseBody`](#zenml.models.v2.base.scoped.UserScopedResponseBody)

Base workspace-scoped body.

#### created *: datetime*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was created.'), 'updated': FieldInfo(annotation=datetime, required=True, title='The timestamp when this resource was last updated.'), 'user': FieldInfo(annotation=Union[UserResponse, NoneType], required=False, default=None, title='The user who created this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### updated *: datetime*

#### user *: [UserResponse](zenml.models.md#zenml.models.UserResponse) | None*

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponseMetadata

Bases: [`UserScopedResponseMetadata`](#zenml.models.v2.base.scoped.UserScopedResponseMetadata)

Base workspace-scoped metadata.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'workspace': FieldInfo(annotation=ForwardRef('WorkspaceResponse'), required=True, title='The workspace of this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponseResources(\*\*extra_data: Any)

Bases: [`UserScopedResponseResources`](#zenml.models.v2.base.scoped.UserScopedResponseResources)

Base workspace-scoped resources.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedResponse(\*, body: AnyDatedBody | None = None, metadata: AnyMetadata | None = None, resources: AnyResources | None = None, id: UUID, permission_denied: bool = False)

Bases: `UserScopedResponse[~WorkspaceBody, ~WorkspaceMetadata, ~WorkspaceResources]`, `Generic`[`WorkspaceBody`, `WorkspaceMetadata`, `WorkspaceResources`]

Base workspace-scoped domain model.

Used as a base class for all domain models that are workspace-scoped.

#### body *: 'AnyBody' | None*

#### id *: UUID*

#### metadata *: 'AnyMetadata' | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[~WorkspaceBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[~WorkspaceMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[~WorkspaceResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

#### resources *: 'AnyResources' | None*

#### *property* workspace *: [WorkspaceResponse](zenml.models.md#zenml.models.WorkspaceResponse)*

The workspace property.

Returns:
: the value of the property.

### *class* zenml.models.v2.base.scoped.WorkspaceScopedTaggableFilter(\*, sort_by: str = 'created', logical_operator: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators) = LogicalOperators.AND, page: Annotated[int, Ge(ge=1)] = 1, size: Annotated[int, Ge(ge=1), Le(le=10000)] = 20, id: Annotated[UUID | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, created: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, updated: Annotated[datetime | str | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, scope_workspace: UUID | None = None, tag: str | None = None)

Bases: [`WorkspaceScopedFilter`](#zenml.models.v2.base.scoped.WorkspaceScopedFilter)

Model to enable advanced scoping with workspace and tagging.

#### FILTER_EXCLUDE_FIELDS *: ClassVar[List[str]]* *= ['sort_by', 'page', 'size', 'logical_operator', 'scope_workspace', 'tag']*

#### apply_filter(query: AnyQuery, table: Type[AnySchema]) → AnyQuery

Applies the filter to a query.

Args:
: query: The query to which to apply the filter.
  table: The query table.

Returns:
: The query with filter applied.

#### created *: datetime | str | None*

#### get_custom_filters() → List[ColumnElement[bool]]

Get custom tag filters.

Returns:
: A list of custom filters.

#### id *: UUID | str | None*

#### logical_operator *: [LogicalOperators](zenml.md#zenml.enums.LogicalOperators)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Created', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'id': FieldInfo(annotation=Union[UUID, str, NoneType], required=False, default=None, description='Id for this resource', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'logical_operator': FieldInfo(annotation=LogicalOperators, required=False, default=<LogicalOperators.AND: 'and'>, description="Which logical operator to use between all filters ['and', 'or']"), 'page': FieldInfo(annotation=int, required=False, default=1, description='Page number', metadata=[Ge(ge=1)]), 'scope_workspace': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None, description='The workspace to scope this query to.'), 'size': FieldInfo(annotation=int, required=False, default=20, description='Page size', metadata=[Ge(ge=1), Le(le=10000)]), 'sort_by': FieldInfo(annotation=str, required=False, default='created', description='Which column to sort by.'), 'tag': FieldInfo(annotation=Union[str, NoneType], required=False, default=None, description='Tag to apply to the filter query.'), 'updated': FieldInfo(annotation=Union[datetime, str, NoneType], required=False, default=None, description='Updated', metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### page *: int*

#### scope_workspace *: UUID | None*

#### size *: int*

#### sort_by *: str*

#### tag *: str | None*

#### updated *: datetime | str | None*

## Module contents
