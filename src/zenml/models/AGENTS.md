# ZenML Domain Models — Concise Guide

Compact reference for understanding, adding, or modifying ZenML domain models. For the canonical, detailed rules, see:
- .cursor/rules/zenml-domain-models.mdc
- Also keep models aligned with ORM schemas; see .cursor/rules/zenml-orm-schema.mdc

Models live under: src/zenml/models

## Core Concepts

- Layered model hierarchy: Requests, Updates, and typed Responses using a tripartite structure (Body, Metadata, Resources).
- Layered filter hierarchy: typed filter operations, scoping, sorting, pagination.
- Scoping variants: global (base), user-scoped, workspace-scoped.
- Strong typing and generics for response composition.
- Keep domain models and ORM schemas strictly in sync (names and types).

## Base Hierarchies

Model base:
- BaseZenModel: common root (analytics tracking, YAML serialization).
- BaseRequest → {Entity}Request (UserScopedRequest, WorkspaceScopedRequest as needed).
- BaseUpdate → {Entity}Update (omit if entity is immutable).
- BaseResponse[Body, Metadata, Resources]
  - BaseResponseBody → BaseDatedResponseBody
    - UserScopedResponseBody, WorkspaceScopedResponseBody
  - BaseResponseMetadata
    - UserScopedResponseMetadata, WorkspaceScopedResponseMetadata
  - BaseResponseResources
    - UserScopedResponseResources, WorkspaceScopedResponseResources
  - BaseIdentifiedResponse[DatedBody, Metadata, Resources]
    - UserScopedResponse[…]
      - WorkspaceScopedResponse[…]

Filter base:
- BaseFilter: core filtering, sorting, pagination.
- Filter (ABC) specializations: BoolFilter, StrFilter → UUIDFilter, NumericFilter, DatetimeFilter.
- UserScopedFilter → WorkspaceScopedFilter.
- TaggableFilter for entities that support tagging.
- FilterGenerator: creates appropriate filter instances.

Response generics:
- Body extends BaseResponseBody
- Metadata extends BaseResponseMetadata
- Resources extends BaseResponseResources

## Domain Model Types

1) Request ({Entity}Request)
- For creation. Inherit BaseRequest or scoped variants.
- Include all mandatory fields and input validation.
- Examples: name, has_custom_name, tags.

2) Response ({Entity}Response)
- Retrieval representation with Body/Metadata/Resources.
- Hydration via get_hydrated_version(); provide property accessors.
- May include analytics hooks and helper methods.

3) Update ({Entity}Update)
- For partial modifications; inherit BaseUpdate.
- Fields are Optional and restricted to mutable attributes.
- If the entity is immutable, omit the Update model.

4) Filter ({Entity}Filter)
- For querying; inherit BaseFilter or scoped variants (+ TaggableFilter if applicable).
- Declare filterable fields, sorting options, and query-building logic.
- Operations are type-specific (equals, not_equals, contains, startswith, gt, lt, etc.) and combinable (AND/OR).

## Hydration Pattern

Responses split into:
- Body: essential attributes (BaseResponseBody / BaseDatedResponseBody).
- Metadata: relationships/auxiliary info (BaseResponseMetadata). Optional; requires hydrated response.
- Resources: related/computed/dynamic data (BaseResponseResources).

Key methods:
- hydrate(), get_hydrated_version()
- get_body(), get_metadata(), get_resources()

## Scoping

- UserScoped*: associates entities with a user (base for workspace scope).
- WorkspaceScoped*: associates entities with both a user and a workspace.

For each scope, define matching types:
- *ScopedRequest, *ScopedResponseBody, *ScopedResponseMetadata, *ScopedResponseResources, *ScopedFilter

Select the narrowest scope that matches ownership semantics.

## Filtering

- Use BaseFilter / UserScopedFilter / WorkspaceScopedFilter (+ TaggableFilter if needed).
- Provide:
  - Declared filter fields with type-appropriate filters.
  - Supported sorts and any exclusions.
  - Scope-aware query rules.
- Use FilterGenerator where dynamic filter construction is needed.

## Naming and File Structure

- Class names:
  - Request: {Entity}Request
  - Response: {Entity}Response
  - Update: {Entity}Update
  - Filter: {Entity}Filter
  - Body: {Entity}ResponseBody
  - Metadata: {Entity}ResponseMetadata
  - Resources: {Entity}ResponseResources
- Files:
  - One entity per file, snake_case filename.
  - Place under appropriate subdirectory (e.g., core/, base/, misc/).

## Minimal New Entity Skeleton

```python
class NewEntityRequest(WorkspaceScopedRequest):
    # Required creation fields and validation

class NewEntityResponseBody(WorkspaceScopedResponseBody):
    # Core attributes

class NewEntityResponseMetadata(WorkspaceScopedResponseMetadata):
    # Optional relationships / metadata

class NewEntityResponseResources(WorkspaceScopedResponseResources):
    # Optional computed / dynamic data

class NewEntityResponse(
    WorkspaceScopedResponse[
        NewEntityResponseBody,
        NewEntityResponseMetadata,
        NewEntityResponseResources,
    ]
):
    # Optional: hydration overrides, convenience accessors
    # def get_hydrated_version(self) -> "NewEntityResponse": ...

class NewEntityFilter(WorkspaceScopedFilter):
    # Filter fields, supported operations, sorting options
```

## Implementation Checklist

- Scope
  - Choose global vs user vs workspace; select matching *Scoped base classes.
- Classes
  - Implement Request, ResponseBody, ResponseMetadata, ResponseResources, Response, Filter.
- Fields
  - Use Pydantic Field with clear title/description and precise typing.
  - Carefully separate mandatory vs Optional.
  - Keep names/types aligned with ORM schemas.
- Methods
  - Implement/override get_hydrated_version() if needed.
  - Add convenience properties and helper constructors (e.g., from_response()) when useful.
- Filtering
  - Define filterable fields, supported operations, sort keys, and exclusions.
  - Apply scope-specific query rules; combine filters with AND/OR as appropriate.
- Documentation
  - Add descriptive docstrings; remember these models back the REST API.
- Sync
  - Keep this guide and the canonical MDC rules synchronized.

Remember: Consistency, type-safety, and parity with the ORM schema are critical for stable API and internal behavior.
