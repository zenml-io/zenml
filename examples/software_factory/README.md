# Software Factory Pipeline

Turn a GitHub issue into a reviewed pull request. A dynamic ZenML pipeline drives a coding agent (the `claude` CLI) through plan, implementation, tests, review and a bounded fix loop. Every command runs inside a ZenML [Sandbox](../../docs/book/component-guide/sandboxes/README.md), and the run pauses for a human at two points with `zenml.wait(...)`.

**ZenML version**: 0.96+ (Python 3.10+)

## 🎯 What You'll Learn

- Drive an agent CLI through a multi-stage workflow with plain Python control flow in a `@pipeline(dynamic=True)`
- Run commands in a `Sandbox` stack component, stream the agent's output into the step logs, and share one live session across steps with `attach(...)`
- Pause a run with `zenml.wait(...)` for a plan approval and a deploy approval
- Pass secrets into the sandbox per command, so they never land in the checkout or the logs
- Bound a test, review and fix loop with `id=` on repeated step invocations
- Record which model the agent used, how many tokens it consumed and what it cost, per step
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
| `write_plan` | own session | Clones the base branch, asks the agent for a plan | `plan` (Markdown), `plan_preview` (HTML) |
| `open_workspace` | creates the shared session | Checks out or creates the target branch, commits the plan as `spec/plans/<branch>.md`, pushes | `workspace`, `base_branch` |
| `implement` | attach | Agent makes the changes, step commits, pushes and opens a draft pull request | `pr` |
| `run_tests` | attach | Runs `test_command` in the checkout, skipped when unset | `tests` |
| `review` | attach | Agent reviews the diff against the issue, plan and test report, only when tests passed | `verdict` |
| `fix` | attach | Agent addresses test failures and review comments, step commits and pushes | `pr` |
| `close_workspace` | attach | Destroys the shared session | |
| `deploy` | own session | Marks the pull request ready for review, a stand-in for a real deployment | |

The loop stops on an approved review or after `max_fix_iterations` fixes. Tests and review run once more than fixes, so the last fix is always tested before the deploy gate.

## 📋 Setup

### 1. ZenML server

Log in to a ZenML server: `zenml login --local` for a local one, or `zenml login <workspace>` for ZenML Pro. Then pick or create a project:

```bash
zenml project set default
```

### 2. Sandbox image

The sandbox needs `git`, `gh`, the `claude` CLI, Python, `pytest` and `uv`. The `Dockerfile` in this directory builds such an image. It runs as a non-root user because the `claude` CLI refuses `--dangerously-skip-permissions` as root. Build it for the platform of your cluster nodes and push it to a registry the sandbox can pull from:

```bash
cd examples/software_factory
docker buildx build --platform linux/amd64 -t <registry>/software-factory-sandbox:latest --push .
```

### 3. Sandbox component and stack

Register a sandbox component without an image and add it to your stack. The image is passed per run, so one component serves any pipeline:

```bash
zenml sandbox register agent-sandbox --flavor=docker
zenml stack update --sandbox agent-sandbox
```

Use `--flavor=kubernetes` (with `--kubernetes_namespace=...` and a service connector) or `--flavor=modal` in the same way. See the [sandbox flavors](https://docs.zenml.io/component-guide/sandboxes) for their options. The containerized flavors (Docker, Kubernetes, Modal) support `attach(...)`, so one sandbox session is shared across the steps of a run.

`run.py --sandbox-image <image>` puts the image into the pipeline settings under the key `sandbox:<component name>`, and `snapshot.yaml` carries the same setting for snapshots. Replace `agent-sandbox` in `snapshot.yaml` with the name of your sandbox component.

**Local flavor**, for trying the example out on your machine without a container. It has no isolation and no `attach(...)`, so every step re-clones the branch, and it ignores the image. The `claude` CLI, `git` and `gh` must be installed locally. The CLI needs the `USER` variable, which the default forwarded set does not include:

```bash
zenml sandbox register agent-sandbox --flavor=local --forward_env=true
zenml stack register software-factory -o default -a default --sandbox agent-sandbox --set
```

### 4. Secrets

The steps declare `@step(secrets=["github", "claude"])`. ZenML turns the keys of those two secrets into environment variables of the step process, so the secret names and key names must match exactly.

**GitHub.** Create a token that can clone, push and open pull requests on the target repository. A [fine-grained token](https://github.com/settings/personal-access-tokens/new) with `Contents: read and write` and `Pull requests: read and write` on that repository is enough. If you use the `gh` CLI, the token from `gh auth token` works as well, as long as it has the `repo` scope.

```bash
zenml secret create github --private --GITHUB_TOKEN=<token>
```

**Claude.** Either a long-lived login token for a Claude subscription, or an Anthropic API key. For the login token, run this on your own machine, complete the browser flow and copy the token it prints:

```bash
claude setup-token
zenml secret create claude --private --CLAUDE_CODE_OAUTH_TOKEN=<token>
```

For an API key instead:

```bash
zenml secret create claude --private --ANTHROPIC_API_KEY=<key>
```

`--private` keeps a secret visible to your user only. On ZenML Pro that is the right default for personal tokens.

The steps pass the tokens into the sandbox only for the duration of single commands: the GitHub token as git config environment variables on each git call and as `GH_TOKEN` on each `gh` call, the Claude variables on each agent call. The checkout never contains a credential, so the agent cannot push, and the sandbox log shows commands without secrets.

## 🏃 Run It

```bash
cd examples/software_factory
pip install -r requirements.txt

python run.py \
  --repo owner/name \
  --issue "Add a health check endpoint." \
  --test-command "uv run pytest tests/unit -q" \
  --sandbox-image <registry>/software-factory-sandbox:latest
```

Only the repository, the issue and the sandbox image are required. Everything else has a default:

| Flag | Meaning |
|---|---|
| `--repo` | Repository as `owner/name` |
| `--issue`, `--issue-file` | The issue description, inline or from a file. The first line becomes the pull request title |
| `--target-branch` | Branch to work on. Created from the base branch if it does not exist, checked out if it does. Derived from the issue title if omitted, for example `factory/add-health-check-endpoint` |
| `--base-branch` | Branch the work starts from and the pull request targets. The repository's default branch if omitted |
| `--test-command` | Shell command run in the checkout after each implementation. Tests are skipped if omitted |
| `--max-fix-iterations` | Upper bound for fix rounds, 2 by default. Zero means test and review only |
| `--agent-model` | Model alias or id for the agent, `sonnet` by default. Try `opus` or a full model id |
| `--gate-timeout` | Seconds each approval gate waits for an answer before the run is paused, 10 minutes by default |
| `--sandbox-image` | Container image for the sandbox sessions of this run. Ignored by the local flavor |

The run prints a dashboard URL. It stops twice for you:

1. `plan_review` after the plan is written. The plan is attached to the wait condition, and the `plan_preview` artifact of `write_plan` shows it rendered. Answer with `{"approved": true, "feedback": ""}` to continue, `approved: false` ends the run.
2. `deploy_approval` after the loop settles. The question states what the agent cost across the run, and the wait condition carries the pull request URL, the last test report, the last review verdict and the summed agent usage. Answer `true` to mark the pull request ready for review.

Resolve them in the dashboard or from the CLI:

```bash
zenml pipeline runs wait-conditions resolve --run <RUN_ID_OR_NAME> --interactive
```

Each gate polls for `gate_timeout` seconds and then pauses the run. ZenML Pro resumes a paused run when the condition is resolved, on an OSS server run `zenml pipeline runs resume <RUN_ID_OR_NAME>` afterwards. With the local orchestrator there is no process left to resume, so answer the gates within the 60 seconds or raise `timeout` in `pipeline.py`.

## 📸 Trigger It From the Server

A snapshot packages the pipeline, its code and the stack so runs can be started from the dashboard, the CLI or the REST API without a local checkout. `snapshot.yaml` holds the parameters shown in the run dialog and the sandbox image setting. Only `repo` and `issue` need a real value per run. Put your image and sandbox component name in it, then:

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
        }
    },
)
```

Or from any system with a ZenML API token:

```bash
curl -X POST "<ZENML_SERVER_URL>/api/v1/pipeline_snapshots/<SNAPSHOT_ID>/runs" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"run_configuration": {"parameters": {"repo": "owner/name", "issue": "..."}}}'
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
├── AGENTS.md          - Conventions for coding agents that change this example
├── requirements.txt
└── README.md
```

## 🔑 How It Works

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

Each invocation inside the loop carries an explicit `id=`, so a resumed run matches the same step runs. The loop runs one test and review round more than fixes, so it never ends on an untested fix:

```python
for attempt in range(max_fix_iterations + 1):
    tests = run_tests(..., id=f"run_tests_{attempt}")
    verdict = None
    if tests.load().passed:
        verdict = review(..., tests=tests, id=f"review_{attempt}")
        if verdict.load().approved:
            break
    if attempt == max_fix_iterations:
        break
    pr = fix(..., tests=tests, verdict=verdict, id=f"fix_{attempt}")
```

### The agent result-file contract

Prompts that expect a structured result end with the same instruction, and the step reads the file back from the checkout after the agent exits:

```python
prompt = f"...\nWrite your result to the file .factory/plan.md relative to the repository root."
run_agent(session, prompt, model=agent_model)
plan = read_repo_file(session, ".factory/plan.md")
```

`.factory/` is excluded from git through `.git/info/exclude`, so review verdicts and summaries never end up in a commit. The plan is the exception: `open_workspace` commits it as `spec/plans/<branch>.md`, with slashes in the branch name replaced by dashes, so the pull request carries it as a file. The pull request body is the agent's own summary of the changes plus links to the plan and the ZenML run.

### Streaming agent output and usage metadata

The agent runs with `--output-format stream-json`, and `run_agent` renders each event into the step log as it happens. The final `result` event carries the model, turn count, token counts, cost and duration, which `run_agent` logs as step metadata under `agent`, visible on the step's Metadata tab in the dashboard. Before the deploy gate, the pipeline sums these across all steps and logs the result on the run under `agent_total`:

```
[tool] Read examples/software_factory/pipeline.py
[tool] Bash python -m py_compile examples/software_factory/*.py
[assistant] Both edge cases are fixed, updating the README next.
[result] success after 12 turns
Agent used claude-sonnet-5 for 12 turns, 41 input / 3120 output tokens, $0.42, 98.3s.
```

## 🔧 Troubleshooting

- **`No active project is configured` or the wrong stack is used when running `run.py`.** A `.zen/` directory in a parent folder holds a repository-level ZenML config that overrides your global one, and this repository's `examples/` folder may have one from earlier experiments. Run `zenml project set ...` and `zenml stack set ...` from inside `examples/software_factory`, or delete the stale `examples/.zen` directory.
- **`claude` exits immediately in the sandbox.** The CLI refuses `--dangerously-skip-permissions` as root, so the image must run as a non-root user. On the local flavor make sure `--forward_env=true` is set so the CLI sees `USER` and finds its login.
- **The first attach after a long step fails with a 401 on EKS.** The cached Kubernetes client carries a short-lived token. `attach_sandbox` drops the cached client before every attach as a workaround.
- **`No Sandbox component in the active stack`.** Add one with `zenml stack update --sandbox <name>`, see [Setup](#3-sandbox-component-and-stack).

## 📚 Learn More

- [Sandboxes](https://docs.zenml.io/component-guide/sandboxes)
- [Wait for external input and resume](https://docs.zenml.io/how-to/steps-pipelines/wait_resume)
- [Snapshots](https://docs.zenml.io/how-to/snapshots/snapshots)
- [Hooks](https://docs.zenml.io/how-to/steps-pipelines/hooks)
- [Dynamic pipelines](https://docs.zenml.io/how-to/steps-pipelines/dynamic_pipelines)
- [Metadata](https://docs.zenml.io/how-to/metadata/metadata)
