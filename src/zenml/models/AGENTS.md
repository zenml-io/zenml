# ZenML Domain Models Agent Guidelines

This file applies when Codex starts in `src/zenml/models/` or below. For
detailed model hierarchy notes and examples, use
`.agents/skills/zenml-repo-workflows/SKILL.md`.

Models live under `src/zenml/models`. Keep them aligned with ORM schemas and
store behavior.

## Core Patterns

- Requests represent creation payloads.
- Updates represent partial modification payloads.
- Responses use Body, Metadata, and Resources.
- Filters define query fields, operations, sorting, scoping, and pagination.
- Choose the narrowest scope that matches ownership semantics: global, user, or
  project.

## Cross-Layer Families

Trace the full path when touching:

- Triggers and schedule/platform event trigger models.
- Resource pools, subject policies, and resource requests.
- Run wait conditions.
- Nested child pipeline run fields such as `parent_run_id`, `child_key`, and
  `root_run_id`.

These often require aligned changes in CLI, client methods, server endpoints,
schemas, migrations, tests, and docs.

## Filter Field Checklist

When adding a filter field, update:

1. The filter model.
2. The corresponding `Client` list method signature.
3. The filter model instantiation inside that client method.

If the field should not be exposed by CLI, add it to `CLI_EXCLUDE_FIELDS`.
Relationship-backed filters may also need custom ORM join logic in the store
layer.

## Compatibility

Usually safe:

- Adding optional properties.

Risky or breaking:

- Deleting properties.
- Renaming properties.
- Making required fields optional in a way older code cannot tolerate.
- Changing property types incompatibly.

Use deprecation periods and defaults when evolving public model responses.
