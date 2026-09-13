# ZenML Integrations Agent Guidelines

This file applies when Codex starts in `src/zenml/integrations/` or below. For
detailed examples, dependency update guidance, and step-operator notes, use
`.agents/skills/zenml-repo-workflows/SKILL.md`.

## Critical Flavor Import Rule

NEVER import integration libraries at the top level in flavor files.

Flavor files live at `src/zenml/integrations/*/flavors/*.py`. They are imported
by the ZenML server and client for stack component discovery. Optional
dependencies such as `boto3`, `sagemaker`, or `kubernetes` may not be installed.
A module-level import can break all of ZenML, not just that integration.

Allowed in flavor files:

- Standard library imports.
- Pydantic and ZenML core imports.
- Integration type imports inside `if TYPE_CHECKING:`.
- Implementation imports inside the `implementation_class` property or another
  method that only runs when the component is used.

Not allowed in flavor files:

- Top-level imports of the integration library.
- Top-level imports from implementation modules that themselves import the
  integration library.
- Config fields typed directly with third-party integration classes.

## Package Shape

Each integration usually has:

- `__init__.py` for integration registration.
- `flavors/` for flavor definitions.
- Implementation folders such as `orchestrators/`, `step_operators/`, and
  `materializers/`.

## Step Operators

New step operator integrations should implement the async-first lifecycle:

- `submit(...)`
- `get_status(...)`
- `wait(...)`
- `cancel(...)`

Store backend job IDs in run metadata immediately after submission so status,
cancel, and wait can work reliably.

## Dependencies

- Prefer inclusive lower bounds and exclusive upper bounds.
- Test realistic integration scenarios locally when changing dependencies.
- Dropping support for an older dependency version is a breaking change.

## Import Boundaries

- Integrations should not import from `zen_server/`.
- Integrations should not import SQL schemas directly from `zen_stores/`; use
  `Client` or `client.zen_store` only when lower-level access is truly needed.
