# zenml.lineage_graph package

## Subpackages

* [zenml.lineage_graph.node package](zenml.lineage_graph.node.md)
  * [Submodules](zenml.lineage_graph.node.md#submodules)
  * [zenml.lineage_graph.node.artifact_node module](zenml.lineage_graph.node.md#module-zenml.lineage_graph.node.artifact_node)
    * [`ArtifactNode`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode)
      * [`ArtifactNode.data`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode.data)
      * [`ArtifactNode.id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode.id)
      * [`ArtifactNode.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode.model_computed_fields)
      * [`ArtifactNode.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode.model_config)
      * [`ArtifactNode.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode.model_fields)
      * [`ArtifactNode.type`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode.type)
    * [`ArtifactNodeDetails`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails)
      * [`ArtifactNodeDetails.artifact_data_type`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.artifact_data_type)
      * [`ArtifactNodeDetails.artifact_type`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.artifact_type)
      * [`ArtifactNodeDetails.execution_id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.execution_id)
      * [`ArtifactNodeDetails.is_cached`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.is_cached)
      * [`ArtifactNodeDetails.metadata`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.metadata)
      * [`ArtifactNodeDetails.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.model_computed_fields)
      * [`ArtifactNodeDetails.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.model_config)
      * [`ArtifactNodeDetails.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.model_fields)
      * [`ArtifactNodeDetails.name`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.name)
      * [`ArtifactNodeDetails.parent_step_id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.parent_step_id)
      * [`ArtifactNodeDetails.producer_step_id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.producer_step_id)
      * [`ArtifactNodeDetails.status`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.status)
      * [`ArtifactNodeDetails.uri`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails.uri)
    * [`ArtifactNodeStatus`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus)
      * [`ArtifactNodeStatus.CACHED`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus.CACHED)
      * [`ArtifactNodeStatus.CREATED`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus.CREATED)
      * [`ArtifactNodeStatus.EXTERNAL`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus.EXTERNAL)
      * [`ArtifactNodeStatus.UNKNOWN`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus.UNKNOWN)
  * [zenml.lineage_graph.node.base_node module](zenml.lineage_graph.node.md#module-zenml.lineage_graph.node.base_node)
    * [`BaseNode`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNode)
      * [`BaseNode.data`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNode.data)
      * [`BaseNode.id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNode.id)
      * [`BaseNode.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNode.model_computed_fields)
      * [`BaseNode.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNode.model_config)
      * [`BaseNode.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNode.model_fields)
      * [`BaseNode.type`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNode.type)
    * [`BaseNodeDetails`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNodeDetails)
      * [`BaseNodeDetails.execution_id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNodeDetails.execution_id)
      * [`BaseNodeDetails.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNodeDetails.model_computed_fields)
      * [`BaseNodeDetails.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNodeDetails.model_config)
      * [`BaseNodeDetails.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNodeDetails.model_fields)
      * [`BaseNodeDetails.name`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNodeDetails.name)
  * [zenml.lineage_graph.node.step_node module](zenml.lineage_graph.node.md#module-zenml.lineage_graph.node.step_node)
    * [`StepNode`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode)
      * [`StepNode.data`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode.data)
      * [`StepNode.id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode.id)
      * [`StepNode.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode.model_computed_fields)
      * [`StepNode.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode.model_config)
      * [`StepNode.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode.model_fields)
      * [`StepNode.type`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode.type)
    * [`StepNodeDetails`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails)
      * [`StepNodeDetails.configuration`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.configuration)
      * [`StepNodeDetails.entrypoint_name`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.entrypoint_name)
      * [`StepNodeDetails.execution_id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.execution_id)
      * [`StepNodeDetails.inputs`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.inputs)
      * [`StepNodeDetails.metadata`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.metadata)
      * [`StepNodeDetails.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.model_computed_fields)
      * [`StepNodeDetails.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.model_config)
      * [`StepNodeDetails.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.model_fields)
      * [`StepNodeDetails.name`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.name)
      * [`StepNodeDetails.outputs`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.outputs)
      * [`StepNodeDetails.parameters`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.parameters)
      * [`StepNodeDetails.status`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails.status)
  * [Module contents](zenml.lineage_graph.node.md#module-zenml.lineage_graph.node)
    * [`ArtifactNode`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNode)
      * [`ArtifactNode.data`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNode.data)
      * [`ArtifactNode.id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNode.id)
      * [`ArtifactNode.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNode.model_computed_fields)
      * [`ArtifactNode.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNode.model_config)
      * [`ArtifactNode.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNode.model_fields)
      * [`ArtifactNode.type`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNode.type)
    * [`ArtifactNodeDetails`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails)
      * [`ArtifactNodeDetails.artifact_data_type`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.artifact_data_type)
      * [`ArtifactNodeDetails.artifact_type`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.artifact_type)
      * [`ArtifactNodeDetails.execution_id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.execution_id)
      * [`ArtifactNodeDetails.is_cached`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.is_cached)
      * [`ArtifactNodeDetails.metadata`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.metadata)
      * [`ArtifactNodeDetails.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.model_computed_fields)
      * [`ArtifactNodeDetails.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.model_config)
      * [`ArtifactNodeDetails.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.model_fields)
      * [`ArtifactNodeDetails.name`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.name)
      * [`ArtifactNodeDetails.parent_step_id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.parent_step_id)
      * [`ArtifactNodeDetails.producer_step_id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.producer_step_id)
      * [`ArtifactNodeDetails.status`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.status)
      * [`ArtifactNodeDetails.uri`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.ArtifactNodeDetails.uri)
    * [`BaseNode`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.BaseNode)
      * [`BaseNode.data`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.BaseNode.data)
      * [`BaseNode.id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.BaseNode.id)
      * [`BaseNode.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.BaseNode.model_computed_fields)
      * [`BaseNode.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.BaseNode.model_config)
      * [`BaseNode.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.BaseNode.model_fields)
      * [`BaseNode.type`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.BaseNode.type)
    * [`StepNode`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNode)
      * [`StepNode.data`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNode.data)
      * [`StepNode.id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNode.id)
      * [`StepNode.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNode.model_computed_fields)
      * [`StepNode.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNode.model_config)
      * [`StepNode.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNode.model_fields)
      * [`StepNode.type`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNode.type)
    * [`StepNodeDetails`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails)
      * [`StepNodeDetails.configuration`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.configuration)
      * [`StepNodeDetails.entrypoint_name`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.entrypoint_name)
      * [`StepNodeDetails.execution_id`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.execution_id)
      * [`StepNodeDetails.inputs`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.inputs)
      * [`StepNodeDetails.metadata`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.metadata)
      * [`StepNodeDetails.model_computed_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.model_computed_fields)
      * [`StepNodeDetails.model_config`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.model_config)
      * [`StepNodeDetails.model_fields`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.model_fields)
      * [`StepNodeDetails.name`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.name)
      * [`StepNodeDetails.outputs`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.outputs)
      * [`StepNodeDetails.parameters`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.parameters)
      * [`StepNodeDetails.status`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.StepNodeDetails.status)

## Submodules

## zenml.lineage_graph.edge module

Class for Edges in a lineage graph.

### *class* zenml.lineage_graph.edge.Edge(\*, id: str, source: str, target: str)

Bases: `BaseModel`

A class that represents an edge in a lineage graph.

#### id *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'id': FieldInfo(annotation=str, required=True), 'source': FieldInfo(annotation=str, required=True), 'target': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### source *: str*

#### target *: str*

## zenml.lineage_graph.lineage_graph module

Class for lineage graph generation.

### *class* zenml.lineage_graph.lineage_graph.LineageGraph(\*, nodes: List[[StepNode](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode) | [ArtifactNode](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode)] = [], edges: List[[Edge](#zenml.lineage_graph.edge.Edge)] = [], root_step_id: str | None = None, run_metadata: List[Tuple[str, str, str]] = [])

Bases: `BaseModel`

A lineage graph representation of a PipelineRunResponseModel.

#### add_artifact_node(artifact: [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse), id: str, name: str, step_id: str, status: [ArtifactNodeStatus](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus)) → None

Adds an artifact node to the lineage graph.

Args:
: artifact: The artifact to add a node for.
  id: The id of the artifact node.
  name: The input or output name of the artifact.
  step_id: The id of the step that produced the artifact.
  status: The status of the step that produced the artifact.

#### add_direct_edges(run: [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)) → None

Add all direct edges between nodes generated by after=….

Args:
: run: The pipeline run to add direct edges for.

#### add_edge(source: str, target: str) → None

Adds an edge to the lineage graph.

Args:
: source: The source node id.
  target: The target node id.

#### add_external_artifacts(run: [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)) → None

Adds all external artifacts to the lineage graph.

Args:
: run: The pipeline run to add external artifacts for.

#### add_step_node(step: [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse), id: str) → None

Adds a step node to the lineage graph.

Args:
: step: The step to add a node for.
  id: The id of the step node.

#### edges *: List[[Edge](#zenml.lineage_graph.edge.Edge)]*

#### generate_run_nodes_and_edges(run: [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)) → None

Initializes a lineage graph from a pipeline run.

Args:
: run: The PipelineRunResponseModel to generate the lineage graph for.

#### generate_step_nodes_and_edges(step: [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse)) → None

Generates the nodes and edges for a step and its artifacts.

Args:
: step: The step to generate the nodes and edges for.

#### has_artifact_link(step_id: str, parent_step_id: str) → bool

Checks if a step has an artifact link to a parent step.

This is the case for all parent steps that were not specified via
after=….

Args:
: step_id: The node ID of the step to check.
  parent_step_id: T node ID of the parent step to check.

Returns:
: True if the steps are linked via an artifact, False otherwise.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'edges': FieldInfo(annotation=List[Edge], required=False, default=[]), 'nodes': FieldInfo(annotation=List[Union[StepNode, ArtifactNode]], required=False, default=[]), 'root_step_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'run_metadata': FieldInfo(annotation=List[Tuple[str, str, str]], required=False, default=[])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### nodes *: List[[StepNode](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode) | [ArtifactNode](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode)]*

#### root_step_id *: str | None*

#### run_metadata *: List[Tuple[str, str, str]]*

## Module contents

Initialization of lineage generation module.

### *class* zenml.lineage_graph.ArtifactNode(\*, id: str, type: str = 'artifact', data: [ArtifactNodeDetails](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails))

Bases: [`BaseNode`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNode)

A class that represents an artifact node in a lineage graph.

#### data *: [ArtifactNodeDetails](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeDetails)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'data': FieldInfo(annotation=ArtifactNodeDetails, required=True), 'id': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=False, default='artifact')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: str*

### *class* zenml.lineage_graph.ArtifactNodeDetails(\*, execution_id: str, name: str, status: [ArtifactNodeStatus](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus), is_cached: bool, artifact_type: str, artifact_data_type: str, parent_step_id: str, producer_step_id: str | None, uri: str, metadata: List[Tuple[str, str, str]])

Bases: [`BaseNodeDetails`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNodeDetails)

Captures all artifact details for the node.

#### artifact_data_type *: str*

#### artifact_type *: str*

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

#### parent_step_id *: str*

#### producer_step_id *: str | None*

#### status *: [ArtifactNodeStatus](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus)*

#### uri *: str*

### *class* zenml.lineage_graph.BaseNode(\*, id: str, type: str, data: [BaseNodeDetails](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNodeDetails))

Bases: `BaseModel`

A class that represents a node in a lineage graph.

#### data *: [BaseNodeDetails](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNodeDetails)*

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

### *class* zenml.lineage_graph.Edge(\*, id: str, source: str, target: str)

Bases: `BaseModel`

A class that represents an edge in a lineage graph.

#### id *: str*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'id': FieldInfo(annotation=str, required=True), 'source': FieldInfo(annotation=str, required=True), 'target': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### source *: str*

#### target *: str*

### *class* zenml.lineage_graph.LineageGraph(\*, nodes: List[[StepNode](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode) | [ArtifactNode](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode)] = [], edges: List[[Edge](#zenml.lineage_graph.edge.Edge)] = [], root_step_id: str | None = None, run_metadata: List[Tuple[str, str, str]] = [])

Bases: `BaseModel`

A lineage graph representation of a PipelineRunResponseModel.

#### add_artifact_node(artifact: [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse), id: str, name: str, step_id: str, status: [ArtifactNodeStatus](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNodeStatus)) → None

Adds an artifact node to the lineage graph.

Args:
: artifact: The artifact to add a node for.
  id: The id of the artifact node.
  name: The input or output name of the artifact.
  step_id: The id of the step that produced the artifact.
  status: The status of the step that produced the artifact.

#### add_direct_edges(run: [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)) → None

Add all direct edges between nodes generated by after=….

Args:
: run: The pipeline run to add direct edges for.

#### add_edge(source: str, target: str) → None

Adds an edge to the lineage graph.

Args:
: source: The source node id.
  target: The target node id.

#### add_external_artifacts(run: [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)) → None

Adds all external artifacts to the lineage graph.

Args:
: run: The pipeline run to add external artifacts for.

#### add_step_node(step: [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse), id: str) → None

Adds a step node to the lineage graph.

Args:
: step: The step to add a node for.
  id: The id of the step node.

#### edges *: List[[Edge](#zenml.lineage_graph.edge.Edge)]*

#### generate_run_nodes_and_edges(run: [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)) → None

Initializes a lineage graph from a pipeline run.

Args:
: run: The PipelineRunResponseModel to generate the lineage graph for.

#### generate_step_nodes_and_edges(step: [StepRunResponse](zenml.models.md#zenml.models.StepRunResponse)) → None

Generates the nodes and edges for a step and its artifacts.

Args:
: step: The step to generate the nodes and edges for.

#### has_artifact_link(step_id: str, parent_step_id: str) → bool

Checks if a step has an artifact link to a parent step.

This is the case for all parent steps that were not specified via
after=….

Args:
: step_id: The node ID of the step to check.
  parent_step_id: T node ID of the parent step to check.

Returns:
: True if the steps are linked via an artifact, False otherwise.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'edges': FieldInfo(annotation=List[Edge], required=False, default=[]), 'nodes': FieldInfo(annotation=List[Union[StepNode, ArtifactNode]], required=False, default=[]), 'root_step_id': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'run_metadata': FieldInfo(annotation=List[Tuple[str, str, str]], required=False, default=[])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### nodes *: List[[StepNode](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNode) | [ArtifactNode](zenml.lineage_graph.node.md#zenml.lineage_graph.node.artifact_node.ArtifactNode)]*

#### root_step_id *: str | None*

#### run_metadata *: List[Tuple[str, str, str]]*

### *class* zenml.lineage_graph.StepNode(\*, id: str, type: str = 'step', data: [StepNodeDetails](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails))

Bases: [`BaseNode`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNode)

A class that represents a step node in a lineage graph.

#### data *: [StepNodeDetails](zenml.lineage_graph.node.md#zenml.lineage_graph.node.step_node.StepNodeDetails)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'data': FieldInfo(annotation=StepNodeDetails, required=True), 'id': FieldInfo(annotation=str, required=True), 'type': FieldInfo(annotation=str, required=False, default='step')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### type *: str*

### *class* zenml.lineage_graph.StepNodeDetails(\*, execution_id: str, name: str, status: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus), entrypoint_name: str, parameters: Dict[str, Any], configuration: Dict[str, Any], inputs: Dict[str, Any], outputs: Dict[str, Any], metadata: List[Tuple[str, str, str]])

Bases: [`BaseNodeDetails`](zenml.lineage_graph.node.md#zenml.lineage_graph.node.base_node.BaseNodeDetails)

Captures all artifact details for the node.

#### configuration *: Dict[str, Any]*

#### entrypoint_name *: str*

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

#### outputs *: Dict[str, Any]*

#### parameters *: Dict[str, Any]*

#### status *: [ExecutionStatus](zenml.md#zenml.enums.ExecutionStatus)*
