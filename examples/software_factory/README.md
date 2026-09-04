# Software Factory Pipeline

Turn a GitHub issue into a reviewed pull request. A dynamic ZenML pipeline drives a coding agent (the `claude` CLI) through plan, implementation, tests, review and a fix loop, running every command inside a ZenML [Sandbox](../../docs/book/component-guide/sandboxes/README.md) and pausing for a human at two points with `zenml.wait(...)`.

**ZenML version**: 0.96+ (Python 3.10+)

## 🎯 What You'll Learn

- Build a `@pipeline(dynamic=True)` that drives an agent CLI through a multi-stage workflow with plain Python control flow
- Run commands in a `Sandbox` stack component, stream the agent's output into the step logs, and reconnect to one live session across steps with `attach(...)`
- Pause a run with `zenml.wait(...)` for a plan approval and a deploy approval
- Pass secrets into the sandbox for single commands without leaving them in the checkout or the logs
- Bound a test, review and fix loop with `id=` on repeated step invocations
- Publish the pipeline as a snapshot that anyone can trigger from the ZenML server

## 🔁 The Flow

```
issue ──▶ write_plan ──▶ [plan_review] ──▶ open_workspace ──▶ implement ──▶ run_tests ──▶ review ──┐
                                                                 ▲                               │
                                                                 └────────── fix ◀── rejected ◀──┘
                                                                                        approved │
                                                                                                 ▼
                                                                  deploy ◀── [deploy_approval] ◀── close_workspace
```

| Step | Sandbox | What it does | Output |
|---|---|---|---|
| `write_plan` | own session | Clones the base branch, asks the agent for a plan | `plan` (Markdown) |
| `open_workspace` | creates the shared session | Checks out or creates the target branch, commits the plan as `spec/plans/<branch>.md`, pushes | `workspace`, `base_branch` |
| `implement` | attach | Agent makes the changes, step commits, pushes and opens a draft pull request | `pr` |
| `run_tests` | attach | Runs `test_command` in the checkout, skipped when unset | `tests` |
| `review` | attach | Agent reviews the diff against the issue, plan and test report, only when tests passed | `verdict` |
| `fix` | attach | Agent addresses test failures and review comments, step commits and pushes | `pr` |
| `close_workspace` | attach | Destroys the shared session | |
| `deploy` | own session | Marks the pull request ready for review, a stand-in for a real deployment | |

The loop over `run_tests`, `review` and `fix` runs at most `max_fix_iterations` times and stops early on an approved review.

## 📋 Prerequisites

### ZenML server and stack

A ZenML server (`zenml login --local` or `zenml login <workspace>` for ZenML Pro) and a stack with a sandbox component. The agent and every git command run inside the sandbox, so the sandbox needs `git`, `gh`, the `claude` CLI, Python and `pytest`.

**Containerized flavors** (Docker, Kubernetes, Modal) support `attach(...)`, so one sandbox session is shared across the steps of a run. Build the image from the `Dockerfile` in this directory and register the flavor without an image, `run.py` sets the image per run through step settings:

```bash
docker build -t <registry>/software-factory-sandbox .
docker push <registry>/software-factory-sandbox

zenml sandbox register agent-sandbox --flavor=docker
zenml stack update --sandbox agent-sandbox
```

The image runs as a non-root user because the `claude` CLI refuses `--dangerously-skip-permissions` as root. `run.py` defaults to the published `michaelzenml/software-factory-sandbox:latest`, pass `--sandbox-image` to use your own build.

**Local flavor**, for trying the example out. It has no isolation and no `attach(...)`, so every step re-clones the branch. The `claude` CLI reads its login from the user keychain and needs the `USER` variable in the session, which the default forwarded set does not include:

```bash
zenml sandbox register agent-sandbox --flavor=local --forward_env=true
zenml stack update --sandbox agent-sandbox
```

### Secrets

The pipeline reads two ZenML secrets. Their key names matter, the steps look them up as environment variables.

| Secret | Key | Value | Used for |
|---|---|---|---|
| `github` | `GITHUB_TOKEN` | A GitHub token that can clone, push and open pull requests on the target repository. A fine-grained token with `Contents: read and write` and `Pull requests: read and write` on that repository is enough. | `git clone`, `fetch`, `push`, `ls-remote` and the `gh pr` calls |
| `claude` | `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` | Either a long-lived login token from `claude setup-token` (Claude subscription) or an Anthropic API key | Every agent invocation |

```bash
zenml secret create github --GITHUB_TOKEN=<token>
zenml secret create claude --CLAUDE_CODE_OAUTH_TOKEN=<token>
```

Add `--private` to keep a secret visible to your user only. On ZenML Pro that is the right default for personal tokens.

The steps declare the secrets with `@step(secrets=["github", "claude"])`, which turns the keys into environment variables of the step process. From there the token reaches the sandbox only for the duration of single commands: the GitHub token as git config environment variables on each git call and as `GH_TOKEN` on each `gh` call, the Claude variables on each agent call. The checkout never contains a credential, so the agent cannot push, and the sandbox log shows commands without secrets. On the local flavor the `claude` secret can be skipped because the CLI uses the keychain login.

## 🏃 Run It

```bash
cd examples/software_factory
pip install -r requirements.txt

python run.py \
  --repo owner/name \
  --issue "Add a health check endpoint." \
  --target-branch feature/health-check \
  --base-branch develop \
  --test-command "uv run pytest tests/unit -q" \
  --max-fix-iterations 2
```

| Flag | Meaning |
|---|---|
| `--repo` | Repository as `owner/name` |
| `--issue`, `--issue-file` | The issue description, inline or from a file |
| `--target-branch` | Branch to work on. Created from the base branch if it does not exist, checked out if it does |
| `--base-branch` | Branch the work starts from and the pull request targets. The repository's default branch if omitted |
| `--test-command` | Shell command run in the checkout after each implementation. Tests are skipped if omitted |
| `--max-fix-iterations` | Upper bound for the test, review and fix loop |
| `--sandbox-image` | Container image for the sandbox sessions of this run |

The run prints a dashboard URL. It stops twice for you:

1. `plan_review` after the plan is written. The plan is attached to the wait condition. Answer with `{"approved": true, "feedback": ""}` to continue, `approved: false` ends the run.
2. `deploy_approval` after the loop settles. The wait condition carries the pull request URL, the last test report and the last review verdict. Answer `true` to mark the pull request ready for review.

Resolve them in the dashboard or from the CLI:

```bash
zenml pipeline runs wait-conditions resolve --run <RUN_ID_OR_NAME> --interactive
```

Each gate polls for 60 seconds and then pauses the run. ZenML Pro resumes a paused run when the condition is resolved, on an OSS server run `zenml pipeline runs resume <RUN_ID_OR_NAME>` afterwards.

## 📸 Trigger It From the Server

A snapshot packages the pipeline, its code and the stack so runs can be started from the dashboard, the CLI or the REST API without a local checkout. `snapshot.yaml` holds placeholder parameters and the sandbox image setting, edit the sandbox component name in it, then:

```bash
cd examples/software_factory
zenml pipeline snapshot create pipeline.software_factory \
  --name software-factory \
  --config snapshot.yaml \
  --stack <your-stack> \
  --replace
```

Trigger a run with real parameters from the CLI:

```bash
cat > run.yaml <<'EOF'
parameters:
  repo: owner/name
  issue: Add a health check endpoint.
  target_branch: feature/health-check
  base_branch: develop
  test_command: uv run pytest tests/unit -q
EOF

zenml pipeline snapshot run software-factory --config run.yaml
```

From Python, for instance from a webhook handler that receives GitHub issues:

```python
from zenml.client import Client

Client().trigger_pipeline(
    snapshot_name_or_id="software-factory",
    run_configuration={
        "parameters": {
            "repo": "owner/name",
            "issue": issue_body,
            "target_branch": f"issue/{issue_number}",
            "base_branch": "develop",
        }
    },
)
```

Or from any system with a ZenML API token:

```bash
curl -X POST "<ZENML_SERVER_URL>/api/v1/pipeline_snapshots/<SNAPSHOT_ID>/runs" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"run_configuration": {"parameters": {"repo": "owner/name", "issue": "...", "target_branch": "issue/42"}}}'
```

The dashboard's snapshot page offers the same run dialog with editable parameters.

## 🏗️ What's Inside

```
📁 software_factory/
├── pipeline.py        - Step definitions and the dynamic pipeline
├── factory_utils.py   - Sandbox, git, gh and agent CLI helpers shared by the steps
├── models.py          - Pydantic models: PRRef, TestReport, ReviewVerdict, Review
├── run.py             - CLI entrypoint
├── snapshot.yaml      - Parameters and settings for creating a snapshot
├── Dockerfile         - Sandbox image
├── requirements.txt
└── README.md
```

## 🔑 Key Concepts

### One shared sandbox session per run

`open_workspace` clones the repository once and returns the session id as an artifact. Every later step that touches the checkout calls `attach_or_recreate(workspace, repo, branch)`, which reattaches to that session and resets it to the pushed branch:

```python
def attach_or_recreate(workspace: str, repo: str, branch: str) -> SandboxSession:
    try:
        session = attach_sandbox(workspace)
    except (KeyError, RuntimeError):
        session = active_sandbox().create_session(destroy_on_exit=True)
        clone_repo(session, repo, ref=branch)

    run_command(session, ["git", "fetch", "origin"], env=git_auth_env())
    run_command(session, ["git", "checkout", branch])
    run_command(session, ["git", "reset", "--hard", f"origin/{branch}"])
    return session
```

Every mutating step commits and pushes before returning, so the branch on GitHub stays the source of truth and the shared session is only an optimization. If the session died between steps, the fallback clones the pushed branch into a fresh session that destroys itself when the step is done. The `on_end` pipeline hook destroys the shared session when a run fails or is stopped.

### Bounded fix loop with deterministic step ids

Each invocation inside the loop carries an explicit `id=`, so a resumed run matches the same step runs:

```python
for attempt in range(max_fix_iterations):
    tests = run_tests(..., id=f"run_tests_{attempt}")
    verdict = None
    if tests.load().passed:
        verdict = review(..., tests=tests, id=f"review_{attempt}")
        if verdict.load().approved:
            break
    pr = fix(..., tests=tests, verdict=verdict, id=f"fix_{attempt}")
```

### The agent result-file contract

Prompts that expect a structured result end with the same instruction, and the step reads the file back from the checkout after the agent exits:

```python
prompt = f"...\nWrite your result to the file .factory/plan.md relative to the repository root."
run_agent(session, prompt)
plan = read_repo_file(session, ".factory/plan.md")
```

`.factory/` is excluded from git through `.git/info/exclude`, so review verdicts and summaries never end up in a commit. The plan is the exception: `open_workspace` commits it as `spec/plans/<branch>.md`, with slashes in the branch name replaced by dashes, so the pull request carries it as a file. The pull request body is the agent's own summary of the changes plus links to the plan and the ZenML run.

### Streaming agent output

The agent runs with `--output-format stream-json`, and `run_agent` renders each event into the step log as it happens:

```
[tool] Read plugins/packages/evaluator/src/kitaru_evaluator/deterministic.py
[tool] Bash uv run pytest -q plugins/tests/evaluators/test_deterministic.py
[assistant] Removed both provenance results from every bundle, updating the tests next.
[result] success after 14 turns
```

## 📚 Learn More

- [Sandboxes](https://docs.zenml.io/component-guide/sandboxes)
- [Wait for external input and resume](https://docs.zenml.io/how-to/steps-pipelines/wait_resume)
- [Snapshots](https://docs.zenml.io/how-to/snapshots/snapshots)
- [Hooks](https://docs.zenml.io/how-to/steps-pipelines/hooks)
- [Dynamic pipelines](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines)
