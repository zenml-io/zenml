# ZenML Migration Agent Guidelines

This file applies to changes in `src/zenml/zen_stores/migrations/` and
below. For detailed migration recipes and SQL inspection queries, use
the repo-root `.agents/skills/zenml-repo-workflows/SKILL.md`.

## Alembic Rules

- Create migrations with descriptive names, for example
  `alembic revision -m "Add X to Y table"`.
- Test upgrades only against a disposable database with isolated ZenML
  configuration. Never use the user's configured store as a test target.
- Downgrade testing is optional because ZenML generally does not support
  downgrades.
- Never modify existing migrations that are already on `main` or `develop`.
- Consider backward compatibility for rolling deployments.
- Include both schema changes and data migrations when needed.
- Run `scripts/check-alembic-branches.sh` to verify migration consistency.

## Testing Workflow

Follow the isolated migration testing workflow in the repo-root workflow skill.
Use a separate checkout/environment of the old version to populate test data,
then run the feature version against the same disposable database. Verify both
schema changes and preservation of representative data. Do not switch the
active checkout or run Alembic against an unspecified store.

## Coordination

Migration work often requires synchronized updates across ORM schemas, domain
models, store methods, client methods, CLI commands, tests, and docs.
