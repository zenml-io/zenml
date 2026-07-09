---
name: field-descriptions
description: Write or review Pydantic `Field(description=...)` text for ZenML stack component configs. Use when adding, editing, or reviewing config fields in `src/zenml/integrations/*/flavors/` or any `StackComponentConfig` subclass, or when `scripts/validate_descriptions.py` fails.
---

# Field Description Standards

When adding or modifying Field descriptions in stack component configs:

## Template Structure

```
{Purpose statement}. {Valid values/format}. {Example(s)}. {Additional context if needed}.
```

## Core Requirements

1. **Purpose**: Clearly state what the field controls or does
2. **Format**: Specify expected value format (URL, path, enum, etc.)
3. **Examples**: Provide at least one concrete example
4. **Constraints**: Include any limitations or requirements

## Quality Standards

- Minimum 30 characters
- Use action words (controls, configures, specifies, determines)
- Include concrete examples with realistic values
- Avoid vague language ("thing", "stuff", "value", "setting")
- Don't start with "The" or end with periods
- Be specific about valid formats and constraints

## Example Field Descriptions

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

## Validation

- Run `python scripts/validate_descriptions.py` to check description quality
- All descriptions must pass validation before merging
- Add validation to CI pipeline to prevent regressions
