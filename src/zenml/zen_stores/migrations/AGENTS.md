# ZenML Migration Agent Guidelines

This file applies when Codex starts in `src/zenml/zen_stores/migrations/` or
below. For detailed migration recipes and SQL inspection queries, use
`.agents/skills/zenml-repo-workflows/SKILL.md`.

## Alembic Rules

- Create migrations with descriptive names, for example
  `alembic revision -m "Add X to Y table"`.
- Test upgrade paths with `alembic upgrade head`.
- Downgrade testing is optional because ZenML generally does not support
  downgrades.
- Never modify existing migrations that are already on `main` or `develop`.
- Consider backward compatibility for rolling deployments.
- Include both schema changes and data migrations when needed.
- Run `scripts/check-alembic-branches.sh` to verify migration consistency.

## Testing Workflow

1. Check out `develop` or the relevant old release.
2. Populate the database from that version.
3. Switch to the feature branch.
4. Run `alembic upgrade head`.

## Coordination

Migration work often requires synchronized updates across ORM schemas, domain
models, store methods, client methods, CLI commands, tests, and docs.
