# Phase C rollout checklist

This checklist keeps the merge-queue cutover separate from the CI code review.
Do not enable merge queue on `develop` until the validation PR is green and the
team has reviewed the rollout plan.

## Validation PR

1. Push the CI changes to a normal branch and open a PR into `develop`.
2. Confirm regular PR checks pass, especially `ci-fast-required`.
3. Manually run the new workflows from the PR branch:

   ```bash
   gh workflow run ci-medium.yml --ref <branch-name>
   gh workflow run develop-health-gate.yml --ref <branch-name>
   ```

4. Run the Modal lane locally against the same pushed branch if needed:

   ```bash
   export GITHUB_REPOSITORY=zenml-io/zenml
   export ZENML_CI_CHECKOUT_REF=<branch-name>
   export GITHUB_SHA=$(git rev-parse HEAD)

   tmp=$(mktemp)
   GITHUB_OUTPUT=$tmp uv run scripts/ci_modal_mysql_sandbox.py start

   server_url=$(grep '^server_url=' "$tmp" | cut -d= -f2-)
   server_username=$(grep '^server_username=' "$tmp" | cut -d= -f2-)
   sandbox_id=$(grep '^sandbox_id=' "$tmp" | cut -d= -f2-)

   export MODAL_CI_SERVER_URL="$server_url"
   export MODAL_CI_SERVER_USERNAME="$server_username"
   export MODAL_CI_SERVER_PASSWORD=$(uv run python - <<'PY'
   from scripts.ci_modal_mysql_sandbox import derive_server_password
   print(derive_server_password())
   PY
   )
   export ZENML_CI_TIER=medium

   uv run pytest tests/integration/functional/test_client.py \
     --environment remote-mysql-modal \
     --no-provision \
     -q

   uv run scripts/ci_modal_mysql_sandbox.py stop --sandbox-id "$sandbox_id"
   ```

5. Share these results in the PR description:
   - `ci-fast-required` result
   - manual `ci-medium.yml` run link
   - manual `develop-health-gate.yml` run link
   - local Modal smoke-test result

## Pre-cutover validation after merge

After the validation PR merges to `develop`, but before branch protection is
changed:

1. Run slow qualification on `develop`:

   ```bash
   gh workflow run ci-slow-develop.yml --ref develop -f git-ref=develop
   ```

2. Wait for the qualification Check Run to be published on the `develop` SHA.
3. Run the health gate from `develop`:

   ```bash
   gh workflow run develop-health-gate.yml --ref develop
   ```

4. Run medium CI from `develop`:

   ```bash
   gh workflow run ci-medium.yml --ref develop
   ```

## Admin cutover request

Only after the checks above are green, ask an admin to update `develop` branch
protection:

- Enable GitHub merge queue.
- Start with `max_group_size = 1` and `build_concurrency = 1`.
- Require exactly these aggregate checks:
  - `ci-fast-required`
  - `ci-medium-required`
  - `develop-health-gate`
- Do not require individual matrix jobs.
- Do not require slow CI on PRs.

## Rollback

If the queue blocks normal development:

1. Disable merge queue on `develop` branch protection.
2. Set the Modal kill switch if the issue is Modal-related:

   ```bash
   gh variable set ZENML_CI_MODAL_DISABLED --body true
   ```

3. Open a follow-up issue with failing queue run links and the rollback time.
