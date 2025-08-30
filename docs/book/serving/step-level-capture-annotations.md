# Step-Level Capture Annotations

ZenML's pipeline serving system supports fine-grained capture control through step-level annotations. This allows you to specify exactly which inputs and outputs should be captured, logged, or persisted as artifacts, providing precise control over data privacy and storage costs.

## Overview

Step-level capture annotations use Python's `typing.Annotated` to specify capture behavior for individual parameters and return values. These annotations work alongside and can override pipeline-level capture policies.

## Basic Usage

### Input Annotations

Control how input parameters are captured in run metadata:

```python
from typing import Annotated
from zenml.serving.capture import Capture

@step
def process_data(
    # Never capture this sensitive parameter
    secret_key: Annotated[str, Capture("none")],
    
    # Always capture this public parameter
    config: Annotated[dict, Capture("full")],
    
    # Regular parameter - uses pipeline policy
    data: str
) -> str:
    return process_with_key(data, secret_key, config)
```

### Output Annotations

Control how outputs are captured and persisted:

```python
@step  
def analyze_data(data: str) -> Annotated[dict, Capture("full", artifacts="sampled")]:
    """Always capture output previews, but only persist artifacts for sampled runs."""
    return {
        "analysis": analyze(data),
        "confidence": 0.95,
        "timestamp": datetime.now()
    }
```

## Capture Modes

### Available Modes

- `"none"` - Never capture this value
- `"metadata"` - Create run records but no payload capture  
- `"errors_only"` - Only capture on step failures
- `"sampled"` - Capture based on sampling rate
- `"full"` - Always capture this value

### Examples by Mode

```python
# Sensitive data - never captured
@step
def handle_credentials(
    password: Annotated[str, Capture("none")]
) -> str:
    return authenticate(password)

# Error diagnostics - only captured on failures  
@step
def risky_operation(data: str) -> Annotated[dict, Capture("errors_only")]:
    if "error" in data:
        raise ValueError("Processing failed")
    return {"status": "success"}

# Performance monitoring - sampled capture
@step  
def expensive_computation(
    data: str
) -> Annotated[dict, Capture("sampled", sample_rate=0.1)]:
    result = expensive_analysis(data)
    return {"result": result, "metrics": get_performance_metrics()}

# Critical outputs - always captured
@step
def generate_report(
    data: str  
) -> Annotated[str, Capture("full", artifacts="full")]:
    return create_detailed_report(data)
```

## Artifact Control

Control which outputs are persisted as ZenML artifacts:

```python
@step
def process_images(
    images: List[str]
) -> Annotated[dict, Capture("full", artifacts="errors_only")]:
    """
    Always capture output previews, but only persist large image 
    artifacts when processing fails for debugging.
    """
    processed = []
    for img in images:
        processed.append(process_image(img))
    
    return {
        "processed_images": processed,
        "count": len(processed),
        "processing_time": measure_time()
    }
```

### Artifact Modes

- `"none"` - Never persist as artifacts
- `"errors_only"` - Only persist on step failures  
- `"sampled"` - Persist based on sampling
- `"full"` - Always persist as artifacts

## Advanced Configuration

### Custom Settings

```python
@step
def process_large_data(
    data: str
) -> Annotated[dict, Capture(
    mode="full",
    max_bytes=64000,  # Custom truncation limit
    redact=["internal_id", "temp_token"],  # Custom redaction
    artifacts="sampled",
    sample_rate=0.2  # Custom sampling rate
)]:
    return {
        "result": analyze(data),
        "internal_id": "temp_12345", 
        "temp_token": "abc123",
        "large_payload": generate_large_result()
    }
```

### Multiple Outputs

For steps returning dictionaries, annotations apply to the entire output:

```python
@step
def multi_output_step(data: str) -> Annotated[dict, Capture("sampled")]:
    return {
        "primary_result": process_primary(data),
        "secondary_result": process_secondary(data),
        "metadata": {"version": "1.0"}
    }
    # All outputs follow the same capture policy
```

## Precedence Rules

Capture settings are resolved with the following precedence (highest to lowest):

1. **Per-call override** (API request `capture_override`)
2. **Step annotation** (most specific)  
3. **Pipeline settings** (`serving.capture` in pipeline config)
4. **Endpoint default** (dashboard/CLI configuration)
5. **Global off-switch** (`ZENML_SERVING_CREATE_RUNS=false`)

### Example Precedence

```python
# Step annotation
@step  
def my_step(
    data: Annotated[str, Capture("none")]  # Step-level: never capture
) -> str:
    return process(data)

# Pipeline configuration
@pipeline(settings={"serving": {"capture": {"mode": "full"}}})  # Pipeline-level: always capture
def my_pipeline():
    result = my_step(data="input")
    return result

# API call
POST /execute {
    "parameters": {"data": "input"},
    "capture_override": {"mode": "sampled"}  # Request-level: sampled capture
}
```

In this example:
- The API call's `capture_override` would take precedence over all other settings
- If no request override, the step annotation (`"none"`) would take precedence over the pipeline setting
- The global off-switch always forces mode to `"none"` regardless of other settings

## Best Practices

### Privacy by Default

```python
@step
def handle_user_data(
    # Explicitly mark PII as never captured
    email: Annotated[str, Capture("none")],
    user_id: Annotated[str, Capture("none")],
    
    # Public configuration can be captured
    settings: Annotated[dict, Capture("full")]
) -> Annotated[str, Capture("metadata")]:  # Only capture run record, not content
    return process_user_request(email, user_id, settings)
```

### Cost Optimization

```python
@step
def expensive_ml_model(
    model_input: str
) -> Annotated[dict, Capture("sampled", artifacts="none", sample_rate=0.05)]:
    """
    Sample 5% of runs for monitoring, but don't persist large model outputs 
    as artifacts to save storage costs.
    """
    prediction = large_model.predict(model_input)
    return {
        "prediction": prediction,
        "confidence_scores": model.get_confidence(),
        "model_version": "v2.1.0"
    }
```

### Error Diagnostics

```python
@step
def data_validation(
    raw_data: Annotated[str, Capture("errors_only")]
) -> Annotated[dict, Capture("errors_only", artifacts="errors_only")]:
    """
    Only capture inputs/outputs when validation fails for debugging.
    """
    try:
        validated_data = validate(raw_data)
        return {"status": "valid", "data": validated_data}
    except ValidationError as e:
        # Input and output will be captured due to error
        return {"status": "invalid", "error": str(e), "raw_data": raw_data}
```

## Environment Variables

Control annotation behavior globally:

```bash
# Disable all run creation (overrides all annotations)
export ZENML_SERVING_CREATE_RUNS=false

# Set default endpoint policy  
export ZENML_SERVING_CAPTURE_DEFAULT=metadata
export ZENML_SERVING_CAPTURE_ARTIFACTS=none
export ZENML_SERVING_CAPTURE_SAMPLE_RATE=0.1

# Custom redaction fields
export ZENML_SERVING_CAPTURE_REDACT=password,secret,token,key
```

## Migration from Pipeline-Level Policies

Existing pipeline-level capture settings continue to work. Annotations provide additional control:

```python
# Before: Pipeline-level only
@pipeline(settings={"serving": {"capture": {"mode": "full"}}})
def old_pipeline():
    return process_step()

# After: Mixed approach with fine-grained control
@pipeline(settings={"serving": {"capture": {"mode": "metadata"}}})  # Conservative default
def new_pipeline():
    # Override for specific sensitive steps
    sensitive_result = sensitive_step(secret_data=Annotated[str, Capture("none")])
    
    # Override for important outputs
    report = generate_report() -> Annotated[str, Capture("full", artifacts="full")]
    
    return report
```

## Troubleshooting

### Annotations Not Working

1. **Check import**: Ensure `from zenml.serving.capture import Capture`
2. **Verify syntax**: Use `Annotated[Type, Capture(...)]` format
3. **Check logs**: Look for parsing warnings in DirectExecutionEngine logs

### Unexpected Capture Behavior

1. **Verify precedence**: Remember request overrides beat annotations
2. **Check global off-switch**: `ZENML_SERVING_CREATE_RUNS=false` disables everything
3. **Validate sampling**: Sampled mode uses deterministic hashing based on job ID

### Performance Impact

- Annotation parsing happens once during engine initialization
- Runtime overhead is minimal - just dictionary lookups
- Most expensive operations (artifact persistence) are controlled by the annotations