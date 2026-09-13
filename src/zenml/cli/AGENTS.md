# ZenML CLI Agent Guidelines

This file applies when Codex starts in `src/zenml/cli/` or below. For detailed
CLI examples and command-family notes, use
`.agents/skills/zenml-repo-workflows/SKILL.md`.

## Key Files

- `utils.py` - CLI helpers, including `list_options`.
- `pipeline.py` - pipeline, run, legacy schedule, and replay/resume commands.
- `trigger.py` - native schedule and platform-event trigger commands.
- `resource_pool.py` and `resource_request.py` - resource pool management and
  queue/request inspection commands.
- `stack.py` - stack management.
- `base.py` - core CLI setup and common decorators.

## Filter and Client Coupling

List commands often use `@list_options(FilterModel)` to generate CLI options
from filter fields, then pass those options to explicit `Client` method
parameters.

When adding a filter field, update all matching client method signatures and
filter model construction sites. If the field should not be a CLI option, add
it to `CLI_EXCLUDE_FIELDS` on the filter model.

Failure story: the CLI exposes `--new-field`, passes `new_field` to
`Client.list_pipeline_runs`, and the client method does not accept it. The user
gets `TypeError: list_pipeline_runs() got an unexpected keyword argument`.

## Import Rules

- Never import integration libraries at module level in CLI files.
- Do not import from `zen_server/` in CLI code.
- Do not import SQL schemas directly from `zen_stores/`; use `Client`.
- Keep heavy optional imports inside the command that needs them.

## Command Families

- Legacy schedules: `zenml pipeline schedule ...` in `pipeline.py`.
- Native schedule triggers: `zenml trigger schedule ...` in `trigger.py`.
- Platform event triggers: `zenml trigger platform-event ...` in `trigger.py`.
- Resource pool behavior often spans CLI commands, models, store methods, and
  Pro/backend scheduling behavior.
