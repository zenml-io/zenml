# ZenML Integrations — Agent Guidelines

Guidance for agents working with ZenML integration code.

## ⚠️ CRITICAL: Integration Flavor Import Rule

**This is the #1 review concern for integration PRs.** Getting this wrong can break all of ZenML.

### The Rule

**NEVER import integration libraries at the top level in flavor files.**

Flavor files are located at: `src/zenml/integrations/*/flavors/*.py`

### Why This Matters

1. **Server-side imports**: Flavor files are imported by the ZenML server and client to discover available stack components
2. **Optional dependencies**: Integration libraries (boto3, sagemaker, kubernetes, etc.) are optional—users only install what they need
3. **Cascading failures**: If a flavor file imports an uninstalled library at module level, importing that module fails, which can break the entire ZenML installation—not just that integration

### ✅ Correct Pattern

```python
# src/zenml/integrations/aws/flavors/sagemaker_orchestrator_flavor.py

from typing import TYPE_CHECKING, Optional, Type
from pydantic import Field

from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor

# Use TYPE_CHECKING for type hints only—never executed at runtime
if TYPE_CHECKING:
    from zenml.integrations.aws.orchestrators import SagemakerOrchestrator


class SagemakerOrchestratorConfig(BaseOrchestratorConfig):
    """Config for the Sagemaker orchestrator."""
    execution_role: str = Field(...)
    # ... other fields using only stdlib/zenml types


class SagemakerOrchestratorFlavor(BaseOrchestratorFlavor):
    
    @property
    def config_class(self) -> Type[SagemakerOrchestratorConfig]:
        return SagemakerOrchestratorConfig
    
    @property
    def implementation_class(self) -> Type["SagemakerOrchestrator"]:
        # Import INSIDE the method—only executed when actually needed
        from zenml.integrations.aws.orchestrators import SagemakerOrchestrator
        return SagemakerOrchestrator
```

### ❌ Incorrect Pattern

```python
# src/zenml/integrations/aws/flavors/sagemaker_orchestrator_flavor.py

# BAD: Top-level import of integration library
import sagemaker  # ← This breaks ZenML if sagemaker isn't installed!
from sagemaker.processing import Processor  # ← Also bad

# BAD: Even indirect imports that pull in the integration library
from zenml.integrations.aws.orchestrators import SagemakerOrchestrator  # ← Bad at top level


class SagemakerOrchestratorConfig(BaseOrchestratorConfig):
    # BAD: Using integration library types in config fields
    processor: sagemaker.processing.Processor  # ← Requires import at top
```

### Key Points

| Location | Integration imports allowed? |
|----------|------------------------------|
| `flavors/*.py` | ❌ Never at top level; only in `TYPE_CHECKING` blocks or inside methods |
| `orchestrators/*.py`, `step_operators/*.py`, etc. | ✅ Yes—these are only imported when the integration is used |
| Config classes in flavor files | ❌ Only use stdlib types, Pydantic types, or ZenML core types |
| `implementation_class` property | ✅ Import inside the property method body |

### Review Checklist for Integration PRs

When reviewing or creating integration code:

- [ ] No top-level imports of the integration library in `flavors/*.py`
- [ ] Implementation class imports are inside the `implementation_class` property
- [ ] Config fields only use stdlib/Pydantic/ZenML types, not integration library types
- [ ] Any type hints for integration classes are protected by `if TYPE_CHECKING:`

## Integration Package Structure

Each integration follows this structure:

```
src/zenml/integrations/<name>/
├── __init__.py           # Integration registration
├── flavors/              # Flavor definitions (NO integration library imports!)
│   ├── __init__.py
│   └── *_flavor.py
├── orchestrators/        # Actual implementations (integration imports OK here)
│   └── *.py
├── step_operators/
│   └── *.py
├── materializers/
│   └── *.py
└── ...
```

## Adding New Integrations

1. Create the integration package structure
2. Register the integration in `__init__.py`
3. Implement flavors (respecting the import rule above)
4. Implement the actual stack components
5. Add tests in `/tests/integration/`
6. Add documentation in `/docs/book/component-guide/`

## Dependency Updates

When updating integration dependencies in `pyproject.toml`:

1. **Check compatibility**: Ensure the new version works with supported Python versions (3.9+)
2. **Test locally**: Run integration tests with the new dependency version
3. **Update bounds carefully**: Prefer inclusive lower bounds and exclusive upper bounds (`>=1.0.0,<2.0.0`)
4. **Document breaking changes**: If the update requires code changes, mention this in the PR
5. **Consider transitive dependencies**: Major version bumps may affect other integrations

### Version Constraint Guidelines

```toml
# Good: Clear bounds
"sagemaker>=2.117.0,<3.0.0"

# Avoid: Unbounded upper versions (can break unexpectedly)
"sagemaker>=2.117.0"

# Avoid: Overly tight constraints
"sagemaker==2.117.0"
```
