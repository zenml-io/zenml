# ZenML Developer Tools

A collection of developer tools for managing ZenML workspaces and running pipelines during development, including a CLI and GitHub workflow integration.

## Authentication

The CLI tool requires authentication to access the ZenML Cloud API. You have two options:

```bash
# Option 1: Using client credentials (for CI/CD)
export CLOUD_STAGING_CLIENT_ID="your-client-id"
export CLOUD_STAGING_CLIENT_SECRET="your-client-secret"

# Option 2: Using ZenML's authentication (for local development)
# First login with: zenml login --pro-api-url https://staging.cloudapi.zenml.io
# Then use zen-dev commands which will use your existing ZenML auth
```

## Workspace Management Commands

### Build Docker images

```bash
# Build a ZenML image
./zen-dev build --repo zenmldocker

# Build a ZenML server image
./zen-dev build --server --repo zenmldocker

# Build with a custom tag
./zen-dev build --repo zenmldocker --tag v1.0

# Build and push
./zen-dev build --repo zenmldocker --push
```

`--repo` can also be set as an environment variable as `DEV_DOCKER_REPO`.
`--tag` defaults to the sluggified branch name.

### Deploy a workspace

```bash
# Create a new workspace with the latest ZenML version
./zen-dev deploy --organization 0000000-0000-0000-000000

# Specify custom Docker image and Helm chart version
./zen-dev deploy --workspace my-workspace --zenml-version 0.81.0 --docker-image zenmldocker/zenml-server:custom-tag --helm-version 0.36.0
```

`--organization` can also be set as an environment variable as `DEV_ORGANIZATION_ID`.
`--workspace` defaults to the sluggied branch name.
`--zenml-version` defaults to the verions in the `VERSION` file.

### Update a workspace

```bash
# Update an existing workspace with a new ZenML version
./zen-dev update --workspace my-workspace --zenml-version 0.82.0

# Update with a custom Docker image
./zen-dev update --workspace my-workspace --zenml-version 0.82.0 --docker-image zenmldocker/zenml-server:custom-tag
```

`--workspace` defaults to the sluggied branch name.

### Get environment information

```bash
# Display current git branch, slugified name, and ZenML version
./zen-dev info
```

### GitHub Actions authentication

```bash
# For GitHub Actions workflows only
# Outputs values in GitHub Actions output format
./zen-dev gh-action-login
```

### Destroy a workspace

```bash
# Destroy a workspace (with confirmation prompt)
./zen-dev destroy --workspace my-workspace

# Force destruction without confirmation
./zen-dev destroy --workspace my-workspace --force
```

## Dev Pipelines

The dev pipelines system allows you to run multiple pipelines with different configurations in a ZenML workspace.

### Pipeline Configuration

Create or modify the configuration in `dev/dev_pipelines_config.yaml`. The configuration format allows you to define pipelines with multiple stack and parameter combinations:

```yaml
pipeline_name:
  # Optional command to run (defaults to "python run.py")
  command: "python custom_script.py"

  # Define stacks with optional requirements files
  stacks:
    default: null  # null means no specific requirements
    aws: requirements_aws.txt  # path to requirements file
    gcp: requirements_gcp.txt

  # Define parameter sets
  params:
    default:  # default parameter set
      batch_size: 32
      epochs: 10
    small:  # alternative parameter set
      batch_size: 16
      epochs: 5

another_pipeline:
  stacks:
    default:
  params:
    config_a:
      config_file: "config_a.yaml"
    config_b:
      config_file: "config_b.yaml"
```

Each pipeline can have:
- An optional `command` to execute (defaults to `python run.py`)
- Multiple `stacks` with optional requirements files
- Multiple parameter sets under `params`

For each pipeline, the system will generate all valid combinations of stack and parameter sets, which can be run individually or as a group.


### GitHub PR Comment Commands

You can trigger pipelines directly from PR comments using the following commands:

```
# Run all pipelines with all configurations
!run

# Run a specific pipeline with all its configurations
!run pipeline_name

# Run a specific pipeline with a specific stack
!run pipeline_name:aws

# Run a specific pipeline with a specific stack and parameter set
!run pipeline_name:aws::small
```

Other available commands:
```
# Deploy a workspace for the current PR branch
!deploy

# Update the workspace for the current PR branch
!update

# Destroy the workspace for the current PR branch
!destroy

# Get the status of the workspace for the current PR branch
!status
```

### Adding Dev Pipelines

To add a new dev pipeline:

1. Create a directory in `dev/pipelines/your_pipeline_name/`
2. Add your pipeline code and a `run.py` file as the entry point
3. Add the pipeline configuration to `dev/dev_pipelines_config.yaml`
4. Commit and push your changes
5. Trigger the pipeline with a PR comment: `!run your_pipeline_name`

## Workflow Implementation Details

The system uses several components:

1. `./zen-dev`: CLI tool for workspace management and authentication
2. `dev/dev_pipelines_config_parser.py`: Generates pipeline configurations
3. `.github/workflows/pr-dev-assistant.yml`: Processes PR comments and triggers pipelines
4. `.github/workflows/run-dev-pipeline.yml`: Reusable workflow for running a pipeline

When a user comments on a PR with a command like `!run`, the system:
1. Authenticates with the workspace
2. Creates/Reuses a service account for running pipelines
3. Parses the command to determine which pipelines to run
4. Generates a matrix of configurations
5. Runs each configuration as a separate job

## Examples

### Complete Development Workflow

1. **Create a PR with your changes**

2. **Deploy a workspace for your branch**:
   Comment on the PR:
   ```
   !deploy
   ```

3. **Update the workspace after making changes**:
   Comment on the PR:
   ```
   !update
   ```

4. **Run all pipelines to verify functionality**:
   Comment on the PR:
   ```
   !run
   ```

5. **Run a specific pipeline configuration**:
   Comment on the PR:
   ```
   !run my_pipeline:aws::small
   ```

6. **Clean up when done**:
   Comment on the PR:
   ```
   !destroy
   ```