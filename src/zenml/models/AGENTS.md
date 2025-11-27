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

## ⚠️ Adding New Filter Fields — CLI-Client Coupling

When adding a field to a filter model (e.g., `PipelineRunFilter`), **you must update THREE locations** or the CLI will break at runtime.

### Why This Matters

The CLI uses `@list_options(FilterModel)` (in `src/zenml/cli/utils.py`) to auto-generate CLI options from filter model fields. These options are passed as `**kwargs` to client methods, but client methods have **explicit parameter lists** that must match. If they don't match, users get:
```
TypeError: list_pipeline_runs() got an unexpected keyword argument 'new_field'
```

This error only occurs at runtime when the CLI option is used—there's no mypy or test coverage to catch it.

### Three-Location Update Checklist

When adding a new filter field:

1. **Filter Model** (`src/zenml/models/v2/core/<entity>.py`)
   ```python
   class PipelineRunFilter(...):
       new_field: Optional[str] = Field(default=None, description="...")
   ```

2. **Client Method Signature** (`src/zenml/client.py`)
   ```python
   def list_pipeline_runs(
       self,
       # ... existing params ...
       new_field: Optional[str] = None,  # ← ADD THIS
   ) -> Page[PipelineRunResponse]:
   ```

3. **Client Method Body** — filter model instantiation inside the same method:
   ```python
   runs_filter_model = PipelineRunFilter(
       # ... existing params ...
       new_field=new_field,  # ← ADD THIS
   )
   ```

### Optional: Exclude from CLI

If the field should NOT be a CLI option, add it to `CLI_EXCLUDE_FIELDS`:
```python
class PipelineRunFilter(...):
    CLI_EXCLUDE_FIELDS = [
        *ProjectScopedFilter.CLI_EXCLUDE_FIELDS,
        "new_field",  # Not exposed in CLI
    ]
```

### Testing

Always test the new filter via CLI after adding:
```bash
zenml pipeline runs list --new_field=some_value
```

### Related Files

| Component | Location |
|-----------|----------|
| Filter models | `src/zenml/models/v2/core/*.py`, `src/zenml/models/v2/base/scoped.py` |
| list_options decorator | `src/zenml/cli/utils.py:2798` |
| Client list methods | `src/zenml/client.py` |
| CLI commands | `src/zenml/cli/*.py` |

## Model Changes and Backwards Compatibility

When modifying domain models, be aware of server/client compatibility implications:

| Change Type | Compatibility Impact |
|-------------|---------------------|
| **Adding new properties** | Usually NOT a problem (extras are now allowed in Pydantic) |
| **Deleting properties** | ⚠️ PROBLEMATIC — breaks server/client compatibility |
| **Making required→optional** | ⚠️ PROBLEMATIC — similar to deletion |
| **Renaming properties** | ⚠️ PROBLEMATIC — equivalent to delete + add |
| **Changing property types** | ⚠️ PROBLEMATIC — may break serialization |

### Why This Matters

ZenML clients and servers may run different versions. When a newer server sends a response with a deleted field, older clients expecting that field will break. Similarly, when an older client sends a request missing a newly-required field, the server will reject it.

### Safe Evolution Pattern

1. **Add new optional fields** — always safe
2. **Deprecate before removing** — mark fields as deprecated, keep them for 2+ minor versions
3. **Use default values** — when adding required fields, provide sensible defaults
4. **Version responses** — for major changes, consider response versioning

---

## Client Method Patterns

When adding or modifying client methods in `src/zenml/client.py`, follow existing patterns:

### Get Methods
```python
def get_pipeline(self, name_id_or_prefix: Union[str, UUID]) -> PipelineResponse:
    """Get a pipeline by name, ID, or prefix."""
    # If it looks like a UUID, fetch directly
    # If it's a name, list + filter to find it
    # Follow what other get_* methods do
```

### List Methods
```python
def list_pipelines(
    self,
    # All filter model fields as explicit parameters
    name: Optional[str] = None,
    size: int = PAGE_SIZE_DEFAULT,
    # ... etc
) -> Page[PipelineResponse]:
    """List pipelines with filtering."""
    filter_model = PipelineFilter(name=name, ...)
    return self.zen_store.list_pipelines(filter_model)
```

### Key Conventions
- **Get by name or ID**: Most `get_*` methods accept either a name or UUID
- **Explicit parameters**: List methods have explicit parameters matching filter fields (see CLI coupling above)
- **Consistent return types**: Get returns single Response, List returns `Page[Response]`
- **Follow existing patterns**: When in doubt, look at similar methods in the same file
