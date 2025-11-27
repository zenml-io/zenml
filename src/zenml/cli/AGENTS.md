# ZenML CLI — Agent Guidelines

Guidance for agents working with ZenML CLI code.

## Key Files

| File | Purpose |
|------|---------|
| `utils.py` | CLI utilities including `list_options` decorator |
| `pipeline.py` | Pipeline and run management commands |
| `stack.py` | Stack management commands |
| `base.py` | Core CLI setup and common decorators |

## Adding or Modifying List Commands

List commands (e.g., `zenml pipeline runs list`) use the `@list_options(FilterModel)` decorator to auto-generate CLI options from filter model fields.

**Critical:** When adding new filter fields, you must update multiple locations or the CLI will break. See the detailed checklist in:

→ `src/zenml/models/AGENTS.md` § "Adding New Filter Fields — CLI-Client Coupling"

### Quick Summary

The `@list_options` decorator auto-generates CLI options from filter model fields, but passes them to client methods that have explicit parameter lists. If a filter model field isn't also a client method parameter, users get:
```
TypeError: list_pipeline_runs() got an unexpected keyword argument 'new_field'
```

## CLI Patterns

### List Command Structure
```python
@entity.command("list")
@list_options(EntityFilter)  # Auto-generates --field options
def list_entities(**kwargs: Any) -> None:
    client = Client()
    entities = client.list_entities(**kwargs)  # kwargs passed to client
```

### Excluding Fields from CLI
Add to `CLI_EXCLUDE_FIELDS` in the filter model (not here in CLI code):
```python
# In src/zenml/models/v2/core/<entity>.py
class EntityFilter(...):
    CLI_EXCLUDE_FIELDS = [..., "internal_field"]
```

## Integration Imports

Never import integration libraries at module level in CLI files. Integrations may not be installed, and module-level imports would break the entire CLI.

```python
# Bad - breaks CLI if sklearn not installed
from sklearn import metrics

# Good - import inside function when needed
def some_command():
    from sklearn import metrics
```
