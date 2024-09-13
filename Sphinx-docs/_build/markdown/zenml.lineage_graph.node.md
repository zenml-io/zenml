# zenml.lineage_graph.node package

## Submodules

## zenml.lineage_graph.node.artifact_node module

Class for all lineage artifact nodes.

### *class* zenml.lineage_graph.node.artifact_node.ArtifactNode(\*, id: str, type: str = 'artifact', data: [ArtifactNodeDetails](#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails))

Bases: [`BaseNode`](#zenml.lineage_graph.node.base_node.BaseNode)

A class that represents an artifact node in a lineage graph.

#### data *: [ArtifactNodeDetails](#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails)*

#### id *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'data': FieldInfo(annotation=ArtifactNodeDetails, required=True), 'id': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=False, default='artifact')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: str*

### *class* zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails(\*, execution_id: str, name: str, status: [ArtifactNodeStatus](#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus), is_cached: bool, artifact_type: str, artifact_data_type: str, parent_step_id: str, producer_step_id: str | None, uri: str, metadata: List[Tuple[str, str, str]])

Bases: [`BaseNodeDetails`](#zenml.lineage_graph.node.base_node.BaseNodeDetails)

Captures all artifact details for the node.

#### artifact_data_type *: str*

#### artifact_type *: str*

#### execution_id *: str*

#### is_cached *: bool*

#### metadata *: List[Tuple[str, str, str]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_data_type': FieldInfo(annotation=str, required=True), 'artifact_type': FieldInfo(annotation=str, required=True), 'execution_id': FieldInfo(annotation=str, required=True), 'is_cached': FieldInfo(annotation=bool, required=True), 'metadata': FieldInfo(annotation=List[Tuple[str, str, str]], required=True), 'name': FieldInfo(annotation=str, required=True), 'parent_step_id': FieldInfo(annotation=str, required=True), 'producer_step_id': FieldInfo(annotation=Union[str, NoneType], required=True), 'status': FieldInfo(annotation=ArtifactNodeStatus, required=True), 'uri': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### parent_step_id *: str*

#### producer_step_id *: str | None*

#### status *: [ArtifactNodeStatus](#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus)*

#### uri *: str*

### *class* zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

Enum that represents the status of an artifact.

#### CACHED *= 'cached'*

#### CREATED *= 'created'*

#### EXTERNAL *= 'external'*

#### UNKNOWN *= 'unknown'*

## zenml.lineage_graph.node.base_node module

Base class for all lineage nodes.

### *class* zenml.lineage_graph.node.base_node.BaseNode(\*, id: str, type: str, data: [BaseNodeDetails](#zenml.lineage_graph.node.base_node.BaseNodeDetails))

Bases: `BaseModel`

A class that represents a node in a lineage graph.

#### data *: [BaseNodeDetails](#zenml.lineage_graph.node.base_node.BaseNodeDetails)*

#### id *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'data': FieldInfo(annotation=BaseNodeDetails, required=True), 'id': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: str*

### *class* zenml.lineage_graph.node.base_node.BaseNodeDetails(\*, execution_id: str, name: str)

Bases: `BaseModel`

Captures all details for the node.

#### execution_id *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'execution_id': FieldInfo(annotation=str, required=True), 'name': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

## zenml.lineage_graph.node.step_node module

Class for all lineage step nodes.

### *class* zenml.lineage_graph.node.step_node.StepNode(\*, id: str, type: str = 'step', data: [StepNodeDetails](#zenml.lineage_graph.node.step_node.StepNodeDetails))

Bases: [`BaseNode`](#zenml.lineage_graph.node.base_node.BaseNode)

A class that represents a step node in a lineage graph.

#### data *: [StepNodeDetails](#zenml.lineage_graph.node.step_node.StepNodeDetails)*

#### id *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'data': FieldInfo(annotation=StepNodeDetails, required=True), 'id': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=False, default='step')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: str*

### *class* zenml.lineage_graph.node.step_node.StepNodeDetails(\*, execution_id: str, name: str, status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus), entrypoint_name: str, parameters: Dict[str, Any], configuration: Dict[str, Any], inputs: Dict[str, Any], outputs: Dict[str, Any], metadata: List[Tuple[str, str, str]])

Bases: [`BaseNodeDetails`](#zenml.lineage_graph.node.base_node.BaseNodeDetails)

Captures all artifact details for the node.

#### configuration *: Dict[str, Any]*

#### entrypoint_name *: str*

#### execution_id *: str*

#### inputs *: Dict[str, Any]*

#### metadata *: List[Tuple[str, str, str]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'configuration': FieldInfo(annotation=Dict[str, Any], required=True), 'entrypoint_name': FieldInfo(annotation=str, required=True), 'execution_id': FieldInfo(annotation=str, required=True), 'inputs': FieldInfo(annotation=Dict[str, Any], required=True), 'metadata': FieldInfo(annotation=List[Tuple[str, str, str]], required=True), 'name': FieldInfo(annotation=str, required=True), 'outputs': FieldInfo(annotation=Dict[str, Any], required=True), 'parameters': FieldInfo(annotation=Dict[str, Any], required=True), 'status': FieldInfo(annotation=ExecutionStatus, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### outputs *: Dict[str, Any]*

#### parameters *: Dict[str, Any]*

#### status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)*

## Module contents

Initialization of lineage nodes.

### *class* zenml.lineage_graph.node.ArtifactNode(\*, id: str, type: str = 'artifact', data: [ArtifactNodeDetails](#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails))

Bases: [`BaseNode`](#zenml.lineage_graph.node.base_node.BaseNode)

A class that represents an artifact node in a lineage graph.

#### data *: [ArtifactNodeDetails](#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails)*

#### id *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'data': FieldInfo(annotation=ArtifactNodeDetails, required=True), 'id': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=False, default='artifact')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: str*

### *class* zenml.lineage_graph.node.ArtifactNodeDetails(\*, execution_id: str, name: str, status: [ArtifactNodeStatus](#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus), is_cached: bool, artifact_type: str, artifact_data_type: str, parent_step_id: str, producer_step_id: str | None, uri: str, metadata: List[Tuple[str, str, str]])

Bases: [`BaseNodeDetails`](#zenml.lineage_graph.node.base_node.BaseNodeDetails)

Captures all artifact details for the node.

#### artifact_data_type *: str*

#### artifact_type *: str*

#### execution_id *: str*

#### is_cached *: bool*

#### metadata *: List[Tuple[str, str, str]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_data_type': FieldInfo(annotation=str, required=True), 'artifact_type': FieldInfo(annotation=str, required=True), 'execution_id': FieldInfo(annotation=str, required=True), 'is_cached': FieldInfo(annotation=bool, required=True), 'metadata': FieldInfo(annotation=List[Tuple[str, str, str]], required=True), 'name': FieldInfo(annotation=str, required=True), 'parent_step_id': FieldInfo(annotation=str, required=True), 'producer_step_id': FieldInfo(annotation=Union[str, NoneType], required=True), 'status': FieldInfo(annotation=ArtifactNodeStatus, required=True), 'uri': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### parent_step_id *: str*

#### producer_step_id *: str | None*

#### status *: [ArtifactNodeStatus](#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus)*

#### uri *: str*

### *class* zenml.lineage_graph.node.BaseNode(\*, id: str, type: str, data: [BaseNodeDetails](#zenml.lineage_graph.node.base_node.BaseNodeDetails))

Bases: `BaseModel`

A class that represents a node in a lineage graph.

#### data *: [BaseNodeDetails](#zenml.lineage_graph.node.base_node.BaseNodeDetails)*

#### id *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'data': FieldInfo(annotation=BaseNodeDetails, required=True), 'id': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: str*

### *class* zenml.lineage_graph.node.StepNode(\*, id: str, type: str = 'step', data: [StepNodeDetails](#zenml.lineage_graph.node.step_node.StepNodeDetails))

Bases: [`BaseNode`](#zenml.lineage_graph.node.base_node.BaseNode)

A class that represents a step node in a lineage graph.

#### data *: [StepNodeDetails](#zenml.lineage_graph.node.step_node.StepNodeDetails)*

#### id *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'data': FieldInfo(annotation=StepNodeDetails, required=True), 'id': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=False, default='step')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: str*

### *class* zenml.lineage_graph.node.StepNodeDetails(\*, execution_id: str, name: str, status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus), entrypoint_name: str, parameters: Dict[str, Any], configuration: Dict[str, Any], inputs: Dict[str, Any], outputs: Dict[str, Any], metadata: List[Tuple[str, str, str]])

Bases: [`BaseNodeDetails`](#zenml.lineage_graph.node.base_node.BaseNodeDetails)

Captures all artifact details for the node.

#### configuration *: Dict[str, Any]*

#### entrypoint_name *: str*

#### execution_id *: str*

#### inputs *: Dict[str, Any]*

#### metadata *: List[Tuple[str, str, str]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'configuration': FieldInfo(annotation=Dict[str, Any], required=True), 'entrypoint_name': FieldInfo(annotation=str, required=True), 'execution_id': FieldInfo(annotation=str, required=True), 'inputs': FieldInfo(annotation=Dict[str, Any], required=True), 'metadata': FieldInfo(annotation=List[Tuple[str, str, str]], required=True), 'name': FieldInfo(annotation=str, required=True), 'outputs': FieldInfo(annotation=Dict[str, Any], required=True), 'parameters': FieldInfo(annotation=Dict[str, Any], required=True), 'status': FieldInfo(annotation=ExecutionStatus, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

#### outputs *: Dict[str, Any]*

#### parameters *: Dict[str, Any]*

#### status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)*
