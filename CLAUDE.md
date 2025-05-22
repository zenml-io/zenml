# ZenML Claude Code Guidelines

This document provides guidance for Claude Code when working with the ZenML codebase. ZenML is an extensible, open-source MLOps framework for creating production-ready ML pipelines.

## Project Structure

- `/src/zenml/` - Core source code
  - `/alerters/` - Alerting system implementations
  - `/annotators/` - Data annotation tool integrations
  - `/artifact_stores/` - Artifact storage implementations
  - `/cli/` - Command-line interface
  - `/code_repositories/` - Code repository integrations
  - `/config/` - Configuration system
  - `/container_registries/` - Container registry implementations
  - `/data_validators/` - Data validation implementations
  - `/experiment_trackers/` - Experiment tracking integrations
  - `/feature_stores/` - Feature store integrations
  - `/image_builders/` - Image building functionality
  - `/integrations/` - External tool integrations
  - `/io/` - File I/O and filesystem utilities
  - `/logging/` - Logging utilities
  - `/materializers/` - Artifact serialization/deserialization
  - `/metadata/` - Metadata management
  - `/model/` - Model-related functionality
  - `/model_deployers/` - Model deployment implementations
  - `/model_registries/` - Model registry implementations
  - `/orchestrators/` - Pipeline execution orchestrators
  - `/pipelines/` - Core pipeline functionality
  - `/services/` - Services implementation
  - `/stack/` - Stack components management
  - `/step_operators/` - Step operator implementations
  - `/steps/` - Pipeline step definitions
  - `/utils/` - Utility functions
  - `/zen_server/` - ZenML server implementation
  - `/zen_stores/` - Storage implementations
- `/tests/` - Test suite (unit, integration)
- `/docs/` - Documentation
- `/examples/` - Example projects (IMPORTANT: Do not modify directly - this folder is updated by CI from other repositories)
- `/scripts/` - Development utilities

## Code Style & Quality Standards

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

### Testing Requirements
- Most new code requires test coverage
  - key exceptions are when the code involves integrations with external
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

### When Implementing Features
- Study existing similar implementations first
- Follow the established patterns in the codebase
- Keep backward compatibility in mind
- Add appropriate error handling
- Document public APIs thoroughly

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
  - **Fast CI**: Runs automatically on all PRs
  - **Full CI**: Includes more extensive tests but requires manual triggering
- To run the full test suite:
  1. Add the label `run-slow-ci` to your PR
  2. Find and restart the "ci-slow" job
- If your changes touch integrations, you'll maybe want to run the full CI
- CI environments have all dependencies installed that many tests require
- Check the GitHub Actions logs to debug any CI failures

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