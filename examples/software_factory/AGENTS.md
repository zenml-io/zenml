# Software Factory Agent Guidelines

This file applies when a coding agent works in `examples/software_factory/`.
`README.md` explains what the pipeline does, how to run it and the design
behind it ("How It Works"). Read it first, this file only adds the rules
for changing the code.

## Layout

- `pipeline.py` - step definitions and the dynamic `software_factory` pipeline.
- `factory_utils.py` - sandbox, git, `gh` and agent CLI helpers. Steps call
  these, they never call `session.exec` or `subprocess` directly.
- `models.py` - Pydantic models exchanged between steps and gates.
- `run.py` - CLI entrypoint. Every pipeline parameter has a flag here.
- `snapshot.yaml` - placeholder parameters and settings for snapshots.
- `Dockerfile` - the sandbox image, not the orchestrator image.

## Rules

- Secrets reach the sandbox only per command, through `git_auth_env()`,
  `GH_TOKEN` and the agent auth variables. Never write credentials into
  files, git config or the image.
- Steps that change the checkout commit and push before they return.
  `attach_or_recreate` resets the session to `origin/<branch>`, so
  uncommitted work is lost by design.
- Agent results go through files in `.factory/`, read with
  `read_repo_file`. Do not parse the agent's free-text answer.
- A step invoked more than once in the pipeline function needs a
  deterministic `id=`.
- A step that creates its own session destroys it. The shared workspace is
  destroyed by `close_workspace` and by the `on_end` hook.

## Changing the pipeline

- Adding a parameter: add it to `software_factory`, the steps that need it,
  `run.py`, `snapshot.yaml` and the flag table in `README.md`.
- Adding a step that runs the agent: declare
  `secrets=["github", "claude"]`, call `run_agent(session, prompt,
  model=agent_model)` and read the result file. `run_agent` already logs
  model, tokens and cost as step metadata.
- Adding a step that touches the checkout: take `workspace`, `repo` and
  `branch`, and open the session with `attach_or_recreate`.
- Changing the loop shape: update "Bounded fix loop" in `README.md`.

## Verifying changes

There are no unit tests for this example, the sandbox and agent cannot run
in CI. Verify with:

```bash
cd examples/software_factory
ruff format . && ruff check .
MYPYPATH=. mypy --explicit-package-bases factory_utils.py pipeline.py run.py models.py
```

Then do a real run against a scratch branch, see "Run It" in `README.md`.
Use the local sandbox flavor for a quick check, a containerized flavor to
exercise `attach(...)`. Answer both gates within their timeout when running
with the local orchestrator.
