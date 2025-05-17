# AGENTS Instructions for ZenML Repository

## Formatting and Linting
- Run `bash scripts/format.sh` to autoformat the code using ruff and yamlfix.
- If `yamlfix` is unavailable, run `bash scripts/format.sh --no-yamlfix` and
  execute `yamlfix .github -v` separately to avoid CI errors.
- Run `bash scripts/run-ci-checks.sh` to perform linting and docstring checks.

## Testing
- Execute `bash scripts/test-coverage-xml.sh` to run the test suite. This is
  required before committing any changes.

## Documentation
- For user facing changes, update the documentation in `docs/` accordingly.
- Update `RELEASE_NOTES.md` with a concise entry summarizing your change.

## Pull Requests
- PRs should target the `develop` branch.
- Follow the template in `.github/pull_request_template.md` when creating a PR.
- Include a short summary of test results in the PR description.

## Style Notes
- The repository uses ruff and mypy as configured in `pyproject.toml`.
- Docstrings follow the Google style convention.
- Keep code modular and well named so that AI coding agents can navigate the
  repository effectively.
