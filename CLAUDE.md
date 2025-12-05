# ZenML Claude Code Guidelines

This document provides guidance for Claude Code when working with the ZenML codebase. ZenML is an extensible, open-source MLOps framework for creating production-ready ML pipelines.

## Project Structure

- `/src/zenml/` - Core source code
- `/tests/` - Test suite (unit, integration)
- `/docs/` - Documentation
- `/examples/` - Example projects (IMPORTANT: Do not modify directly - this folder is updated by CI from other repositories)
- `/scripts/` - Development utilities

Use filesystem navigation tools to explore the codebase structure as needed.

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
  - Runs mypy type checking on the codebase
  - Note: Full mypy check is slow on the entire codebase
  - For faster checks, run mypy directly on specific files: `mypy src/zenml/path/to/file.py`
- The primary code style is enforced by ruff, configured in `pyproject.toml`
- YAML formatting uses yamlfix: `yamlfix .github -v`

### Python Standards
- Use Python 3.9+ compatible code
- Follow Google Python style for docstrings
- Type hint all function parameters and return values
- Use descriptive variable names and documentation
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

**Example:** `requires_resources_in_orchestration_environment` in `base_orchestrator.py:495-514`

```python
# This is a @staticmethod on BaseOrchestrator, not a standalone util
@staticmethod
def requires_resources_in_orchestration_environment(step: "Step") -> bool:
    """Checks if the orchestrator should run this step on special resources."""
    if step.config.step_operator:
        return False
    return not step.config.resource_settings.empty
```

This method could be a global util, but it's placed on the class because:
- All orchestrator subclasses frequently need it
- Subclasses can call `self.requires_resources_in_orchestration_environment(step)` without imports
- It's conceptually tied to orchestrator behavior

**When to use utils files:**
- Truly generic functions used across unrelated modules
- Functions that don't logically belong to any class
- Pure utility functions (string manipulation, date formatting, etc.)

**Key utils locations:**
- `src/zenml/utils/` — General utilities
- `src/zenml/orchestrators/utils.py` — Orchestrator-specific utilities
- `src/zenml/orchestrators/step_run_utils.py` — Step execution utilities
- `src/zenml/orchestrators/publish_utils.py` — Status/metadata publishing

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

### FastAPI Agent Profile
- ZenML OSS FastAPI work demands senior-level proficiency across FastAPI, SQLModel, SQLAlchemy 2.0, and modern Pydantic v2 patterns; study existing routers and services before proposing changes.
- Favor object-oriented extensions over scattering helpers—extend service/repository classes or introduce cohesive new ones, and rely on dependency injection rather than module-level singletons.
- Keep all shared state inside FastAPI's dependency system or app factory; never introduce fresh global variables outside the initializer.
- Use descriptive auxiliary-verb-prefixed names and lower_snake_case paths (for example `routers/manage_invitation.py`, `services/issue_token.py`) so reviewers immediately understand intent.
- Apply the Receive an Object, Return an Object (RORO) convention on public interfaces to keep payloads self-documenting and testable.

### FastAPI Project Structure
- Each FastAPI package must expose a router entry point plus clearly separated sub-routes, utilities, static assets, and schema/model definitions; keep imports explicit via named exports.
- Co-locate Pydantic request/response models with their consuming routes, and keep reusable business logic inside services or repositories accessed through dependency injection.
- Name directories/files with verbs or nouns that communicate behavior (e.g., `routers/register_user.py`, `services/create_invitation.py`) so navigation stays predictable.

### FastAPI Error Handling & Validation
- Lead with guard clauses in routes, dependencies, and services—validate payloads, auth context, and resources early; prefer early returns and keep the happy path last.
- Skip redundant `else` blocks after returns; log context-rich errors and surface user-safe details while retaining debug information in structured logs.
- Define custom exception types or factories so middleware can map them to consistent JSON payloads with trace metadata.
- Raise `HTTPException` (with precise status codes and detail strings) for expected errors, and push unexpected failures through middleware that centralizes logging, metrics, and alerting.
- Model inputs/outputs with Pydantic BaseModel derivatives to keep validation explicit and documentation synchronized automatically.

### Testing Requirements
- Most new code requires test coverage
  - Key exceptions are when the code involves integrations with external
    services. (in those cases we generally test things extensively locally and
    in the CI. So the developer might have to run things or set things up
    locally first.)
- Tests live in the `/tests/` folder with structure loosely mirroring the main codebase
- Unit tests go in `/tests/unit/`
- Integration tests go in `/tests/integration/`

#### Running Tests
- Do NOT try to run the entire test suite locally - many tests require special environments
- Run targeted tests for the specific components you've changed:
  - `pytest tests/unit/path/to/test_file.py`
  - `pytest tests/unit/path/to/test_file.py::test_specific_function`
- For full coverage, use CI (see CI section below)
- Some tests use: `bash scripts/test-coverage-xml.sh` (but this won't run all tests)

## Dependencies & Runtime Constraints
- Align contributions with the FastAPI + Pydantic v2 + SQLAlchemy 2.0 + SQLModel stack defined for ZenML OSS; confirm any new dependency in `pyproject.toml` before adoption.
- The OSS runtime forbids async I/O in Claude-authored code even though FastAPI supports it—implement synchronous `def` handlers and delegate background/long-running work to workers or dependency-injected services; this supersedes generic async advice found elsewhere.
- Prefer dependency injection over module-level singletons for clients, caches, and repositories so state management stays testable.
- Cache static or frequently accessed data (e.g., dependency-scoped in-memory caches) and lazy-load heavyweight resources to control cold-start latency.
- Document minimum supported versions when modifying dependency-heavy paths and explain performance trade-offs in PRs when serialization or caching strategies change.

## Development Workflow

### Prerequisites
- Set up a Python environment with ZenML dev dependencies
- Install ZenML in development mode: `pip install -e ".[dev]"`
- Most scripts require these dependencies to be available
- ZenML recommends using `uv` for Python package installation in local environments
  - `uv` is also used in CI workflows
  - It resolves dependencies more quickly and reliably than pip
  - It can resolve dependency conflicts that pip sometimes struggles with or takes a long time to resolve

### Environment Variables
- Several environment variables are useful during ZenML development:
  - `ZENML_DEBUG=true`: Enables verbose debug logging
  - `ZENML_LOGGING_VERBOSITY=INFO`: Controls logging verbosity
  - `ZENML_ANALYTICS_OPT_IN=false`: Disables analytics during development
  - `MLSTACKS_ANALYTICS_OPT_OUT=true`: Disables MLStacks analytics
  - `AUTO_OPEN_DASHBOARD=false`: Prevents automatic dashboard opening
  - `ZENML_ENABLE_RICH_TRACEBACK=false`: Disables rich traceback formatting
  - `TOKENIZERS_PARALLELISM=false`: Avoids tokenizers parallelism warnings

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

### Security Guidelines
- **NEVER** commit secrets, API keys, tokens, or passwords
- Use environment variables or ZenML's secret management for sensitive data
- Review changes for accidental credential exposure before committing
- If you accidentally commit secrets, notify the team immediately
- Follow the principle of least privilege when implementing access controls
- Validate and sanitize all user inputs

### Database and Migration Guidelines
- Database schema changes require Alembic migrations
- Create migrations with descriptive names: `alembic revision -m "Add X to Y table"`
- Test upgrade path: `alembic upgrade head` (downgrade testing is optional—ZenML doesn't support downgrades in most cases)
- Never modify existing migrations that are already on main/develop branches
- Always consider backward compatibility for rolling deployments
- Include both schema changes and data migrations when needed
- Run `scripts/check-alembic-branches.sh` to verify migration consistency

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

### When Implementing Features
- Study existing similar implementations first
- Follow the established patterns in the codebase
- Keep backward compatibility in mind
- Add appropriate error handling
- Document public APIs thoroughly

### Field Description Standards
When adding or modifying Field descriptions in stack component configs:

#### Template Structure
```
{Purpose statement}. {Valid values/format}. {Example(s)}. {Additional context if needed}.
```

#### Core Requirements
1. **Purpose**: Clearly state what the field controls or does
2. **Format**: Specify expected value format (URL, path, enum, etc.)
3. **Examples**: Provide at least one concrete example
4. **Constraints**: Include any limitations or requirements

#### Quality Standards
- Minimum 30 characters
- Use action words (controls, configures, specifies, determines)
- Include concrete examples with realistic values
- Avoid vague language ("thing", "stuff", "value", "setting")
- Don't start with "The" or end with periods
- Be specific about valid formats and constraints

#### Example Field Descriptions
```python
# Good examples:
instance_type: Optional[str] = Field(
    None,
    description="AWS EC2 instance type for step execution. Must be a valid "
    "SageMaker-supported instance type. Examples: 'ml.t3.medium' (2 vCPU, 4GB RAM), "
    "'ml.m5.xlarge' (4 vCPU, 16GB RAM). Defaults to ml.m5.xlarge for training steps"
)

path: str = Field(
    description="Root path for artifact storage. Must be a valid URI supported by the "
    "artifact store implementation. Examples: 's3://my-bucket/artifacts', "
    "'/local/storage/path', 'gs://bucket-name/zenml-artifacts'. Path must be accessible "
    "with configured credentials"
)

synchronous: bool = Field(
    True,
    description="Controls whether pipeline execution blocks the client. If True, "
    "the client waits until all steps complete. If False, returns immediately and "
    "executes asynchronously. Useful for long-running production pipelines"
)
```

#### Validation
- Run `python scripts/validate_descriptions.py` to check description quality
- All descriptions must pass validation before merging
- Add validation to CI pipeline to prevent regressions

### When Fixing Bugs
- Add regression tests that would have caught the bug
- Understand root cause before implementing fix
- Document the fix in commit messages

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

### Pipeline Architecture
- Pipelines are collections of steps
- Steps produce and consume artifacts
- Artifacts are serialized/deserialized by materializers
- Pipelines are executed by orchestrators
- Stack components provide functionality like storage, orchestration, etc.

### Key Abstractions
- `BaseComponent` - Base for stack components
- `BasePipeline` - Pipeline definition
- `BaseStep` - Step implementation
- `BaseMaterializer` - Artifact serialization
- `BaseOrchestrator` - Pipeline execution

## Common Tasks

### Adding New Integrations
1. Create integration package in `/src/zenml/integrations/`
2. Implement required abstractions and register flavors
3. Add tests in `/tests/integrations/`
4. Add documentation in `/docs/book/component-guide/`

### Modifying Core Functionality
1. Understand the impact on existing components
2. Maintain backward compatibility where possible
3. Add comprehensive test coverage
4. Update type hints and documentation

## Task Planning Approach

When tackling complex tasks:
1. Break down the task into smaller sub-tasks
2. Research existing implementations in the codebase
3. Plan approach before implementation
4. Test incrementally as you implement
5. Document design decisions in code comments

## Expert Tips

- ZenML follows a plugin architecture - study how components are registered
- API stability is important - don't break public interfaces
- Review similar PRs for implementation patterns
- Pipeline execution is complex - test thoroughly when modifying
- Centralize FastAPI logging, tracing, and unexpected error handling inside middleware; measure latency/throughput for new endpoints, cache static payloads, lazy-load heavyweight resources, and articulate serialization trade-offs in PR notes.

### Summary Checklist for PR Reviewers

Quick reference for common review concerns. Detailed explanations live in the nested AGENTS.md files.

- [ ] **Integration PRs:** No library imports in flavor files (`src/zenml/integrations/AGENTS.md`)
- [ ] **Orchestrator PRs:** Verify `get_orchestrator_run_id` is unique per run but same for all steps (`src/zenml/orchestrators/AGENTS.md`)
- [ ] **Filter model changes:** Check corresponding client method is updated (`src/zenml/models/AGENTS.md`)
- [ ] **Private method changes:** Check all internal usages (see "Private Methods" above)
- [ ] **Import checking:** No `zen_server` imports from outside `zen_server` (`src/zenml/zen_server/AGENTS.md`)
- [ ] **Import checking:** No direct SQL imports from outside `zen_stores` (`src/zenml/zen_stores/schemas/AGENTS.md`)
- [ ] **Model changes:** Adding properties OK, deleting/making optional is breaking (`src/zenml/models/AGENTS.md`)
- [ ] **Dependency bumps:** If dropping old version support, it's a breaking change (`src/zenml/integrations/AGENTS.md`)

## Documentation Guidelines

### Structure
- Documentation files live in `docs/book/`
- Multiple sections each have their own `toc.md` file for navigation
- Assets (images, etc.) belong in a `.gitbook` folder at the same level as the relevant `toc.md`
- When adding or removing pages, update the appropriate `toc.md` file

### Format and Style
- ZenML uses GitBook for documentation
- Include metadata fields at the top of documentation pages (follow existing patterns)
- Documentation should be readable and conversational
- Use consistent formatting with existing documentation
- Avoid overusing bullet points or other formatting elements
- Prioritize readability and clarity over excessive structure
- Include appropriate cross-references to related documentation

### Content Standards
- Clear, concise language
- Code examples for APIs
- Explanation of concepts
- Usage patterns and best practices
- Match tone and style with existing documentation

---

*This document is maintained to help Claude Code work effectively with the
ZenML codebase. For human contributors, see CONTRIBUTING.md.*
