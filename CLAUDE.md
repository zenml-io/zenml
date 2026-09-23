# ZenML Claude Code Guidelines

This document provides guidance for Claude Code when working with the ZenML codebase. ZenML is an extensible, open-source MLOps framework for creating production-ready ML pipelines.

## Use ZenML Docs via MCP
Claude Code can query ZenML documentation via the built-in GitBook MCP server: https://docs.zenml.io/~gitbook/mcp. This enables real-time, source-of-truth lookups from the docs while you code, reducing hallucinations and speeding up feature discovery.

Quick setup (CLI):
```bash
claude mcp add zenmldocs --transport http https://docs.zenml.io/~gitbook/mcp
```

Note: The MCP server indexes the latest released docs, not the develop branch. For full setup details and editor alternatives, see docs/book/reference/llms-txt.md.

## Code Style & Quality Standards

### Commenting policy — explain why, not what
- Use comments to document intent, trade‑offs, constraints, invariants, and tricky edge cases—i.e., why the code is this way—rather than narrating changes. Prefer self‑explanatory code; add comments only where extra context is needed. Write for a reader 6+ months later.
- Use for: complex logic/algorithms, non‑obvious design decisions, business rules/constraints, API purpose/contracts, edge cases.
- Avoid: change‑tracking comments ("Updated from previous version", "New implementation", "Changed to use X instead of Y", "Refactored this section").
- Avoid simple explanatory comments, where it is already clear from the code itself.
- Avoid useless one-line comments interleaved with code that merely narrate the implementation. Favor expressive names and small, focused functions.

  ```python
  # Bad
  x = x + 1  # increment x

  # Good
  count += 1
  ```

- Do not use multi-line banner comments to group classes/functions. Use a concise module-level docstring or split code into dedicated modules.

  ```python
  # Bad
  """
  ===== Dataset Loaders =====
  """
  class CSVLoader: ...
  class ParquetLoader: ...

  # Good (module-level docstring at top)
  """
  Dataset loaders used by data ingestion (CSV, Parquet).
  """
  class CSVLoader: ...
  class ParquetLoader: ...
  ```

### Formatting and Linting
- Format code with: `bash scripts/format.sh` (requires Python environment with dev dependencies)
  - Run this before every commit to ensure proper formatting
  - Automatically fixes and formats code using ruff and yamlfix
- Check code quality with: `bash scripts/lint.sh`
  - Unlike format.sh, this doesn't auto-fix issues
  - Runs Ruff, pydoclint (on `src/zenml tests/harness`), yamlfix, zizmor, and mypy
  - Note: Full mypy check is slow on the entire codebase
  - For faster checks, run mypy directly on specific files: `mypy src/zenml/path/to/file.py`

### Python Standards
- Follow Google Python style for docstrings. Include `Args`, `Returns`,
  `Yields`, and `Raises` sections whenever the function contract requires them;
  do not use a summary-only docstring to omit applicable sections.
- Type hint all function parameters and return values
- Keep function size manageable (aim for < 50 lines) though there are exceptions

#### Prefer typing over dynamic attribute checks
- Don't use getattr/hasattr for capability checks when static typing can express the contract
- Prefer Protocols/ABCs, Unions with isinstance narrowing, or typed adapters around untyped third-party objects
- If getattr/hasattr is unavoidable, isolate it in a small helper and expose a typed interface

Example:
```python
# Bad
if hasattr(handler, "close"):
    handler.close()

# Good
from typing import Protocol

class Closable(Protocol):
    def close(self) -> None: ...

def shutdown(h: Closable) -> None:
    h.close()
```

### Util Function Placement

When deciding whether to place a helper function in a utils file or on a class, follow these guidelines:

1. **If a method only makes sense within the context of a class** → Put it on the class
2. **If a static/util method is heavily used by subclasses** → Put it on the parent class

**Rationale for placing methods on classes:**
- Saves imports for users and subclasses
- Subclasses can simply call `self.something()` instead of finding and importing from a util file
- Keeps related functionality co-located

**Example:** `BaseOrchestrator.requires_resources_in_orchestration_environment` is a `@staticmethod` on the base class, not a global util, because every orchestrator subclass needs it and can call it via `self` without an import.

**When to use utils files:**
- Truly generic functions used across unrelated modules
- Functions that don't logically belong to any class
- Pure utility functions (string manipulation, date formatting, etc.)

### Private Methods and API Stability

Methods and functions starting with `_` (underscore) are **private** and should NOT be called from outside their class or module.

**The rule:**
- `_method()` on a class → only call from within that class
- `_function()` in a utils module → only call from within that module
- This isn't always consistently applied in the codebase, but it's the intended convention

**Backwards compatibility — case-by-case judgment:**

There are no strict written rules; evaluate each change individually:

| Symbol type | Part of public API? | Breaking change if modified? |
|-------------|---------------------|------------------------------|
| Classes/functions exported in `zenml.__init__` | ✅ Definitely public | ⚠️ Yes — requires deprecation |
| Public methods on those classes | ✅ Public | ⚠️ Yes — requires deprecation |
| Internal methods deep in the codebase (no underscore) | ❌ Not intended for users | ✅ No — update all internal usages |
| `_private_method()` | ❌ No | ✅ No — can change freely |

**When changing any non-underscore method:**
1. Check if the class/function is exported in `zenml.__init__` — if so, it's public API
2. Search for usages **within the ZenML codebase** (grep/find references)
3. Update all internal usages
4. For truly internal code not exported at the root, no deprecation needed

**Best practice for integrations (future-proofing):**

> ⚠️ **Integrations should avoid using ZenML private methods**

This is primarily a future concern: when integrations eventually move out of the main ZenML repo (external packages), mypy won't detect if a private method they depend on was changed, leading to silent breakage. Even while integrations live in-repo, using only public APIs is good practice and prepares for this transition.

```python
# Bad - integration code using private method
from zenml.orchestrators.base_orchestrator import BaseOrchestrator

class MyOrchestrator(BaseOrchestrator):
    def submit_pipeline(self, ...):
        self._some_private_helper()  # ❌ Don't do this

# Good - use only public methods or reimplement logic
class MyOrchestrator(BaseOrchestrator):
    def submit_pipeline(self, ...):
        self.public_method()  # ✅ Safe
```

### FastAPI Conventions
Router, service, error-handling, and validation conventions for the server live in `src/zenml/zen_server/AGENTS.md` and load automatically when you work in that directory.

### Testing Requirements
- Most new code requires test coverage
  - Key exceptions are when the code involves integrations with external
    services. (in those cases we generally test things extensively locally and
    in the CI. So the developer might have to run things or set things up
    locally first.)

#### Running Tests
- Do NOT try to run the entire test suite locally - many tests require special environments
- Run targeted tests for the specific components you've changed
- For full coverage, use CI (see CI section below)
- Some tests use: `bash scripts/test-coverage-xml.sh` (but this won't run all tests)

## Dependencies & Runtime Constraints
- Confirm any new dependency in `pyproject.toml` before adoption.
- When changing server framework (e.g., `fastapi`) or database library versions, check whether related OpenTelemetry SDK, exporter, and instrumentation dependencies also need updates. Breaking changes in instrumented libraries can require coordinated OTel updates. Keep OTel SDK/exporter versions aligned with the matching OpenTelemetry instrumentation beta line.
- The OSS runtime forbids async I/O in Claude-authored code even though FastAPI supports it—implement synchronous `def` handlers and delegate background/long-running work to workers or dependency-injected services; this supersedes generic async advice found elsewhere.
- Prefer dependency injection over module-level singletons for clients, caches, and repositories so state management stays testable.
- Document minimum supported versions when modifying dependency-heavy paths and explain performance trade-offs in PRs when serialization or caching strategies change.

## Development Workflow

### Prerequisites
- Set up a Python environment with ZenML dev dependencies
- Install ZenML in development mode: `pip install -e ".[dev]"`
- Most scripts require these dependencies to be available
- ZenML recommends using `uv` for Python package installation in local environments

### Environment Variables
- Several environment variables are useful during ZenML development:
  - `ZENML_LOGGING_VERBOSITY=DEBUG`: Controls logging verbosity
  - `AUTO_OPEN_DASHBOARD=false`: Prevents automatic dashboard opening
  - `ZENML_ENABLE_RICH_TRACEBACK=false`: Disables rich traceback formatting
  - `TOKENIZERS_PARALLELISM=false`: Avoids tokenizers parallelism warnings
- Always set the following environment variables:
  - `ZENML_ANALYTICS_OPT_IN=false`: Disables analytics during development
  - `ZENML_DEBUG=true`: Uses the development ZenML analytics server to avoid
    sending analytics to the official ZenML analytics server (IMPORTANT!). This
    must be set even if `ZENML_ANALYTICS_OPT_IN=true` because in a client-server
    setup, the server controls the client-side analytics opt-in status.


### Branch Management
- **IMPORTANT**: `develop` is our primary working branch, NOT `main`
- Always branch off `develop` for all changes
- All PRs should target the `develop` branch
- The `main` branch is only updated during the release process
- If working on a feature branch that's already based on `develop`, you may need to branch off that feature branch for related changes

### Making Changes
1. Run `bash scripts/format.sh` before every commit
2. Run targeted tests to verify changes (see above)
3. Update documentation for user-facing changes (or ensure that nothing was broken)
4. IMPORTANT: **Before opening a PR or making a large commit**, always run `/simplify` to review changed code for reuse opportunities, quality issues, and efficiency improvements. Fix any issues it finds before committing.

### Security Guidelines
- **NEVER** commit secrets, API keys, tokens, or passwords
- Review changes for accidental credential exposure before committing
- If you accidentally commit secrets, notify the team immediately

### Database and Migration Guidelines
- Schema changes require Alembic migrations. Never modify migrations already on `main`/`develop`. Full rules live in `src/zenml/zen_stores/migrations/AGENTS.md`.

### Commit Message Guidelines
- Write clear, descriptive commit messages explaining the "why" not just the "what"
- First line should be a concise summary (50 chars or less)
- Use imperative mood: "Add feature" not "Added feature"
- Reference issue numbers when applicable: "Fix user auth bug (#1234)"
- For multi-line messages, add a blank line after the summary
- Example:
  ```
  Add retry logic to artifact upload
  
  Previously, artifact uploads would fail immediately on network errors.
  This adds exponential backoff retry logic to handle transient failures.
  
  Fixes #1234
  ```

### Field Description Standards
Templates, the quality bar, and worked examples for Pydantic `Field(description=...)` text in stack component configs live in the `field-descriptions` skill. All descriptions must pass `python scripts/validate_descriptions.py` before merging.

### Pull Request Guidelines
- Use human-readable names for PRs (no prefixes like "feat:" or "doc:")
- Keep PR titles concise but descriptive
- Write comprehensive PR descriptions:
  - Clearly explain what the changes do
  - Mention why the changes are needed
  - Detail any important implementation decisions
  - Note any areas that need special reviewer attention
- Detailed PR descriptions help both reviewers and release note creation
- Use appropriate PR tags where applicable:
  - `internal`: For changes relevant only to ZenML team members
  - `documentation`: For changes related to documentation
  - `bug`: For bug fixes
  - `dependencies`: For dependency updates
  - `enhancement`: For new features or improvements
- **REQUIRED: Release Notes Labels** - Every PR must have exactly one of these labels:
  - `release-notes`: For user-facing features, significant updates, or changes that should appear in the changelog. Use this for new features, important bug fixes affecting users, API changes, or anything users should know about.
  - `no-release-notes`: For internal changes, CI fixes, refactoring, minor bug fixes, documentation-only changes, or anything that doesn't need to be surfaced to users.
  - The CI will block merging if neither label is present. When in doubt, use `no-release-notes` for internal/maintenance work.

### Continuous Integration
- ZenML uses a two-tier CI approach:
  - **Fast CI**: Runs automatically on all PRs (basic tests, linting, type checking)
  - **Full CI**: Includes integration tests, tutorial pipeline regression tests, and more extensive test coverage
- The `run-slow-ci` label triggers full CI testing
- Full CI is required before merging - maintainers will add the label if needed
- Tutorial pipeline testing runs all VSCode tutorial examples against the current branch to catch breaking changes
- If your changes touch integrations or core functionality, mention in the PR that full CI should be run
- CI failures will show in the PR checks - review logs to understand any issues

## Core Concepts

### Important Terminology
- The term "model" has multiple distinct meanings in the codebase:
  1. **Pydantic models**: Data structures used throughout the codebase (like `PipelineModel`)
  2. **ML models**: Actual machine learning models (PyTorch, sklearn, etc.)
  3. **ZenML models**: Namespaces that group artifacts, metadata, and other resources related to an ML model
- Be careful with these terms when reading/writing code to avoid confusion

## Summary Checklist for PR Reviewers

Quick reference for common review concerns. Detailed explanations live in the nested AGENTS.md files.

- [ ] **Integration PRs:** No library imports in flavor files (`src/zenml/integrations/AGENTS.md`)
- [ ] **Orchestrator PRs:** Verify `get_orchestrator_run_id` is unique per run but same for all steps (`src/zenml/orchestrators/AGENTS.md`)
- [ ] **Filter model changes:** Check corresponding client method is updated (`src/zenml/models/AGENTS.md`)
- [ ] **Private method changes:** Check all internal usages (see "Private Methods" above)
- [ ] **Import checking:** No `zen_server` imports from outside `zen_server` (`src/zenml/zen_server/AGENTS.md`)
- [ ] **Import checking:** No direct SQL imports from outside `zen_stores` (`src/zenml/zen_stores/schemas/AGENTS.md`)
- [ ] **Model changes:** Adding properties OK, deleting/making optional is breaking (`src/zenml/models/AGENTS.md`)
- [ ] **Dependency bumps:** If dropping old version support, it's a breaking change (`src/zenml/integrations/AGENTS.md`)
- [ ] **Scheduling changes:** Must span both legacy schedule and trigger stacks (CLI + client + server + models + schemas)
- [ ] **Step operator changes:** Check `BaseStepOperator`, `StepLauncher`, and at least one concrete integration

## Documentation Guidelines
Structure, GitBook conventions, `toc.md` handling, and link checking live in `docs/book/AGENTS.md` and load automatically when you work with files under `docs/book/`.

---

*This document is maintained to help Claude Code work effectively with the
ZenML codebase. For human contributors, see CONTRIBUTING.md.*
