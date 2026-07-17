# ZenML ORM Schema Agent Guidelines

This file applies when Codex starts in `src/zenml/zen_stores/schemas/` or
below. For detailed SQLModel examples, relationship patterns, and eager-loading
notes, use `.agents/skills/zenml-repo-workflows/SKILL.md`.

## Storage Rules

- ZenML uses SQLModel and SQLAlchemy for database operations.
- No raw SQL unless absolutely necessary.
- General string column limit is about 250 characters because of MySQL.
- Code outside `zen_stores/` should not import SQL-related code directly from
  this directory.
- External code should use `Client`; lower-level access should go through
  `client.zen_store` only when truly needed.

## Schema Patterns

- Inherit from `BaseSchema` or `NamedSchema`.
- Use declarative SQLModel style with explicit `table=True` and
  `__tablename__`.
- Keep ORM fields and types aligned with domain models.
- Schema changes usually require migrations.
- Export new schemas from `src/zenml/zen_stores/schemas/__init__.py`.
- Add indexes, unique constraints, and nullability according to actual query
  and business requirements.

## Relationships

- Use `schema_utils.build_foreign_key_field` for foreign keys.
- Always update both sides when adding or changing relationships.
- Keep `back_populates` symmetric.
- Use link models with composite primary keys for many-to-many relationships.

## Conversion and Updates

- Implement `to_model`.
- Implement `from_request` or `from_model` where appropriate.
- Implement `update` or `update_from_model`.
- Include heavy related resources only when requested by flags.
- Always refresh `updated` on mutations.
- Keep structured field serialization and decoding symmetric.

## Eager Loading

- Collections use `selectinload`; `joinedload` on collections can multiply rows.
- Single-valued relationships usually use `joinedload` on get paths when the
  related row usually exists.
- Keep `selectinload` for nullable foreign keys that are usually empty.

## Migration Coupling

Schema changes typically require migrations and matching domain model updates.
Check store behavior, client methods, CLI commands, tests, and docs when the
schema backs a user-visible feature.
