---
name: zenml-quick-wins
description: >-
  Implements ZenML quick wins to enhance MLOps workflows. Investigates codebase 
  and stack configuration, recommends high-priority improvements, and implements 
  metadata logging, experiment tracking, alerts, scheduling, secrets management, 
  tags, git hooks, HTML reports, and Model Control Plane setup.
  Use when: user wants to improve their ZenML setup, asks about MLOps best practices,
  mentions "quick wins", wants to enhance pipelines, or needs help with ZenML features
  like experiment tracking, alerting, scheduling, or model governance.
---

# ZenML Quick Wins Implementation

Guides users through discovering and implementing high-impact ZenML features that take ~5 minutes each. Investigates current setup, recommends priorities, and implements chosen improvements.

## Workflow Overview

```
┌─────────────────────┐
│  1. INVESTIGATE     │  Understand current stack + codebase
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  2. RECOMMEND       │  Prioritize quick wins based on findings
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  3. IMPLEMENT       │  Apply selected quick wins
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  4. VERIFY          │  Confirm implementation works
└─────────────────────┘
```

---

## Phase 1: Investigation

Run these commands to understand the current ZenML setup:

```bash
# Core stack info
zenml status
zenml stack list --output=json
zenml stack describe --output=json

# Component details
zenml experiment-tracker list 2>/dev/null || echo "No experiment trackers"
zenml alerter list 2>/dev/null || echo "No alerters configured"
zenml secret list 2>/dev/null || echo "No secrets or no access"
zenml code-repository list 2>/dev/null || echo "No code repos connected"
zenml model list 2>/dev/null || echo "No models registered"

# Recent runs (check for metadata usage)
zenml pipeline runs list --size=5 --output=json 2>/dev/null
```

### Codebase Analysis

Look for these patterns in Python files:

| Pattern | Indicates | Quick Win Opportunity |
|---------|-----------|----------------------|
| `@pipeline` without `tags=` | No tagging | #9 Tags |
| `@step` without `log_metadata` | No metadata | #1 Metadata |
| No `HTMLString` imports | No HTML reports | #11 Reports |
| No `Model()` usage | No model governance | #12 Model Control Plane |
| Hardcoded credentials | Security risk | #7 Secrets |
| No `Schedule` imports | Manual runs | #5 Scheduling |

### MCP Server Check

If ZenML MCP server is available, use it for deeper exploration:

```bash
# Check if zenml MCP tools are available
# If yes, use them to query pipelines, runs, artifacts
```

---

## Phase 2: Recommendation

### Quick Wins Catalog

| # | Quick Win | Complexity | Impact | Prerequisites |
|---|-----------|------------|--------|---------------|
| 1 | [Metadata logging](quick-wins-catalog.md#1-metadata-logging) | ⭐ | 🔥🔥🔥 | None |
| 2 | [Experiment comparison](quick-wins-catalog.md#2-experiment-comparison-zenml-pro) | ⭐ | 🔥🔥 | #1 + Pro |
| 3 | [Autologging](quick-wins-catalog.md#3-autologging-experiment-trackers) | ⭐⭐ | 🔥🔥 | Exp tracker |
| 4 | [Slack/Discord alerts](quick-wins-catalog.md#4-alerts-slackdiscord) | ⭐⭐ | 🔥🔥 | Slack/Discord |
| 5 | [Cron scheduling](quick-wins-catalog.md#5-cron-scheduling) | ⭐⭐ | 🔥🔥🔥 | Orchestrator |
| 6 | [Warm pools](quick-wins-catalog.md#6-warm-pools--persistent-resources) | ⭐ | 🔥🔥 | SageMaker/Vertex |
| 7 | [Secrets management](quick-wins-catalog.md#7-secrets-management) | ⭐⭐ | 🔥🔥🔥 | None |
| 8 | [Local smoke tests](quick-wins-catalog.md#8-local-smoke-tests) | ⭐⭐ | 🔥🔥 | Docker |
| 9 | [Tags](quick-wins-catalog.md#9-tags) | ⭐ | 🔥🔥 | None |
| 10 | [Git repo hooks](quick-wins-catalog.md#10-git-repository-hooks) | ⭐⭐ | 🔥🔥🔥 | GitHub/GitLab |
| 11 | [HTML reports](quick-wins-catalog.md#11-html-reports) | ⭐ | 🔥🔥 | None |
| 12 | [Model Control Plane](quick-wins-catalog.md#12-model-control-plane) | ⭐⭐ | 🔥🔥🔥 | None |
| 13 | [Parent Docker images](quick-wins-catalog.md#13-parent-docker-images) | ⭐⭐⭐ | 🔥🔥 | Container reg |
| 14 | [ZenML docs MCP server](quick-wins-catalog.md#14-zenml-docs-mcp-server) | ⭐ | 🔥🔥 | IDE with MCP |
| 15 | [CLI export formats](quick-wins-catalog.md#15-cli-export-formats) | ⭐ | 🔥 | None |

### Prioritization Matrix

**Start here (foundational):**
1. **#1 Metadata** — Foundation for everything else
2. **#9 Tags** — Organization from day one
3. **#7 Secrets** — Security baseline

**Next tier (observability):**
4. **#12 Model Control Plane** — Governance foundation
5. **#10 Git hooks** — Reproducibility
6. **#3 Autologging** or **#11 HTML reports**

**Operations tier:**
7. **#5 Scheduling** — Automation
8. **#4 Alerts** — Awareness
9. **#8 Smoke tests** — Faster iteration

**Advanced:**
10. **#6 Warm pools**, **#13 Parent images** — Performance optimization

**Developer experience:**
11. **#14 ZenML docs MCP** — Better IDE assistance
12. **#15 CLI export** — Scripting/automation

Ask the user which quick wins they want to implement based on their findings and priorities.

---

## Phase 3: Implementation

See [quick-wins-catalog.md](quick-wins-catalog.md) for detailed implementation guides for each quick win.

### Implementation Checklist Pattern

For each quick win, follow this pattern:

```
- [ ] Verify prerequisites met
- [ ] Implement the change
- [ ] Test the implementation
- [ ] Document what was done
```

---

## Phase 4: Verification

After implementing, verify with:

```bash
# Check stack configuration
zenml stack describe

# Run a test pipeline (if applicable)
python your_pipeline.py

# Verify in dashboard (ZenML Pro)
# Check metadata, tags, model versions appear correctly
```

---

## Troubleshooting & Documentation

### When to Use Web Search

If implementation fails or documentation seems outdated:
1. Search `site:docs.zenml.io <topic>` for latest docs
2. Check specific component documentation

### Install ZenML Docs MCP Server

For better IDE assistance during implementation:

**Claude Code (VS Code):**
```bash
claude mcp add zenmldocs --transport http https://docs.zenml.io/~gitbook/mcp
```

**Cursor:**
```json
{
  "mcpServers": {
    "zenmldocs": {
      "transport": {
        "type": "http",
        "url": "https://docs.zenml.io/~gitbook/mcp"
      }
    }
  }
}
```

### Key Documentation Links

- Metadata: https://docs.zenml.io/concepts/metadata
- Tags: https://docs.zenml.io/concepts/tags
- Models: https://docs.zenml.io/concepts/models
- Secrets: https://docs.zenml.io/concepts/secrets
- Scheduling: https://docs.zenml.io/how-to/steps-pipelines/scheduling
- Alerters: https://docs.zenml.io/stacks/stack-components/alerters
- Experiment Trackers: https://docs.zenml.io/stacks/stack-components/experiment-trackers
- Code Repositories: https://docs.zenml.io/user-guides/production-guide/connect-code-repository
- Containerization: https://docs.zenml.io/concepts/containerization
- Visualizations: https://docs.zenml.io/concepts/artifacts/visualizations

---

## Quick Reference

### Minimal Metadata Example
```python
from zenml import step, log_metadata

@step
def train_model(data):
    # ... training code ...
    log_metadata({"accuracy": 0.95, "loss": 0.05, "epochs": 10})
    return model
```

### Minimal Tags Example
```python
from zenml import pipeline

@pipeline(tags=["experiment", "v2"])
def my_pipeline():
    ...
```

### Minimal Model Registration
```python
from zenml import pipeline, Model

model = Model(name="my_classifier", tags=["production"])

@pipeline(model=model)
def training_pipeline():
    ...
```
