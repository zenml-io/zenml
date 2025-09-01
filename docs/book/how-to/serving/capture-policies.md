# Pipeline Serving Capture Policies

---

## Overview

Capture policies control what gets recorded when a served pipeline handles a request. ZenML supports five capture modes that provide different levels of observability while balancing privacy, performance, and storage costs.

Looking to learn how to run and consume the Serving API (sync, async, streaming), configure service options, and when to prefer Serving vs orchestrators? See the how-to guide: [Serving Pipelines](./serving.md).

### The Five Capture Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **`full`** | Records metadata, input/output payloads (with redaction/truncation), and persists artifacts | Development, debugging, comprehensive monitoring |
| **`sampled`** | Like `full`, but only for a fraction of invocations (controlled by `sample_rate`) | Production monitoring with controlled overhead |
| **`errors_only`** | Records metadata and persists artifacts only when steps fail | Minimal monitoring focused on error diagnosis |
| **`metadata`** | Records run/step metadata only; no payload previews or artifacts | Privacy-conscious monitoring |
| **`none`** | Records nothing for the invocation | Maximum privacy, zero observability overhead |

---

## Quick Start

The simplest way to configure capture policies is using the new flat `serving_capture` settings format at the pipeline or step level.

### Pipeline-Level Configuration

```python
from zenml import pipeline, step

@pipeline(settings={"serving_capture": {"mode": "full"}})  # default anyway
def my_pipeline(text: str) -> str: 
    return process_text(text)

@step(settings={"serving_capture": {"mode": "none"}})      # override for this step
def secret_step(sensitive_data: str) -> str:
    return process_sensitive(sensitive_data)
```

### Sampling for Production

```python
@pipeline(settings={"serving_capture": {"mode": "sampled", "sample_rate": 0.1}})
def my_pipeline(data: str) -> str:
    return process_data(data)
```

---

## Request-Level Overrides

You can override the global capture mode on a per-request basis:

```json
POST /invoke
{
  "parameters": {"text": "Hello world"},
  "capture_override": {"mode": "metadata"}
}
```

**Note:** Only `mode` and (if using sampled mode) `sample_rate` can be overridden at the request level in the simplified API.

---

## Fine-Grained Input/Output Control

### Option A: Settings Configuration (Pipeline or Step Level)

```python
@step(settings={"serving_capture": {
  "inputs": {"city": "full"},   # param-name → mode
  "outputs": "full"             # string applies to the default output
}})
def analyze_weather(city: str, token: str) -> str:
    return get_weather(city, token)

@step(settings={"serving_capture": {
  "inputs": {"city": "full", "token": "none"},
  "outputs": {"result": "sampled", "debug_info": "metadata"}
}})  
def analyze_detailed(city: str, token: str) -> Tuple[str, Dict[str, Any]]:
    return analyze_city(city, token)
```

### Option B: Python Type Annotations (Fallback)

When no settings-level per-value policies are defined, ZenML falls back to type annotations:

```python
from typing import Annotated
from zenml.deployers.serving import Capture

@step
def analyze_weather(
    city: Annotated[str, Capture.FULL],      # safe to log
    token: Annotated[str, Capture.OFF],     # never log  
) -> Annotated[str, Capture.SAMPLED()]:      # use global sampling
    return get_weather(city, token)
```

**Available `Capture` constants:**
- `Capture.FULL` - Always capture
- `Capture.OFF` - Never capture  
- `Capture.METADATA` - Metadata only
- `Capture.ERRORS_ONLY` - Only on failures
- `Capture.SAMPLED()` - Use global sampling decision

---

## Precedence Rules

### Global Mode (Coarse Control)
**Step.mode > Request.mode > Pipeline.mode > Default(`full`)**

### Per-Value Mode (Fine Control)  
**Step > Request (not supported yet) > Pipeline > Annotation > Derived from global mode**

**Important:** If a higher layer (Step or Pipeline settings) defines a per-value policy for a given input/output, annotations are ignored for that specific value.

---

## Artifacts Behavior

Artifacts are automatically derived from the capture mode:

| Capture Mode | Artifacts Behavior |
|--------------|-------------------|
| `full` | `artifacts=full` |  
| `sampled` | `artifacts=sampled` |
| `errors_only` | `artifacts=errors_only` |
| `metadata` | `artifacts=none` |
| `none` | `artifacts=none` |

Advanced users can still override the `artifacts` setting explicitly for backward compatibility.

---

## Privacy and Security Features

### Automatic Redaction

Sensitive fields are automatically redacted by default:

```python
# These field names are redacted by default (case-insensitive substring matching):
# password, token, key, secret, auth, credential, oauth, session, etc.
```

### Custom Redaction

```python
@pipeline(settings={"serving_capture": {
    "mode": "full",
    "redact": ["customer_id", "internal_code", "api_token"]
}})
def secure_pipeline(data: str) -> str:
    return process_data(data)
```

### Size Limits

Large payloads are automatically truncated (default: 256KB). You can customize this:

```python
@step(settings={"serving_capture": {
    "mode": "full", 
    "max_bytes": 64000
}})
def limited_capture_step(large_data: str) -> str:
    return process_large_data(large_data)
```

---

## Common Examples

### Privacy-Conscious Chat Agent

```python
@pipeline(settings={"serving_capture": {"mode": "metadata"}})
def chat_agent(message: str) -> str:
    return generate_response(message)
```

### Development/Debugging Pipeline

```python
@pipeline(settings={"serving_capture": {"mode": "full"}})
def experiment_pipeline(data: str) -> str:
    return process_experiment(data)
```

### Production with Balanced Observability

```python
@pipeline(settings={"serving_capture": {"mode": "sampled", "sample_rate": 0.05}})
def inference_pipeline(input_data: str) -> str:
    return run_inference(input_data)
```

### Per-Step Privacy Control

```python
@step(settings={"serving_capture": {"mode": "none"}})
def handle_pii(sensitive_data: str) -> str:
    return anonymize_data(sensitive_data)

@step(settings={"serving_capture": {
    "inputs": {"public_data": "full", "private_key": "none"},
    "outputs": "sampled",
    "sample_rate": 0.1
}})
def mixed_sensitivity_step(public_data: str, private_key: str) -> str:
    return process_mixed_data(public_data, private_key)
```

---

## Migration from Legacy Configuration

### Before (Legacy)
```python
@step(settings={"serving": {"capture": {"inputs": {"city": {"mode": "full"}}}}})
def process_step(city: str) -> str:
    return process_city(city)
```

### After (Simplified)
```python
@step(settings={"serving_capture": {"inputs": {"city": "full"}}})  
def process_step(city: str) -> str:
    return process_city(city)
```

The legacy nested format remains fully supported for backward compatibility.

---

## Best Practices

### 1. Start Conservative
Begin with `metadata` mode in production, then gradually increase capture as needed:

```python
@pipeline(settings={"serving_capture": {"mode": "metadata"}})
def production_pipeline(data: str) -> str:
    return process_data(data)
```

### 2. Use Sampling for Insights
For high-volume production pipelines, use sampling to balance observability with performance:

```python
@pipeline(settings={"serving_capture": {"mode": "sampled", "sample_rate": 0.01}})
def high_volume_pipeline(data: str) -> str:
    return process_data(data)
```

### 3. Secure Sensitive Steps
Always disable capture for steps handling sensitive data:

```python
@step(settings={"serving_capture": {"mode": "none"}})
def process_credentials(username: str, password: str) -> str:
    return authenticate(username, password)
```

### 4. Use Annotations for Convenience
Type annotations provide a clean way to mark individual parameters:

```python
from typing import Annotated
from zenml.deployers.serving import Capture

@step
def api_call(
    public_endpoint: Annotated[str, Capture.FULL],
    api_key: Annotated[str, Capture.OFF],
) -> Annotated[str, Capture.METADATA]:
    return call_api(public_endpoint, api_key)
```

### 5. Layer Your Privacy Controls
Use pipeline-level defaults with step-level overrides:

```python
@pipeline(settings={"serving_capture": {"mode": "metadata"}})  # Conservative default
def secure_pipeline(data: str) -> str:
    processed = secure_step(data)     # Inherits metadata mode
    result = debug_step(processed)    # Can override for debugging
    return result

@step(settings={"serving_capture": {"mode": "full"}})  # Override for debugging
def debug_step(data: str) -> str:
    return analyze_data(data)
```

---

## FAQ

### Q: Do annotations always apply?
**A:** No. Annotations only apply when there isn't a per-value policy set at the step or pipeline level for that specific input/output.

### Q: Can I override capture behavior per request?
**A:** Yes. Set `capture_override.mode` (and `sample_rate` if using sampled mode) in your request.

### Q: Do I need to configure artifacts separately?
**A:** No. Artifacts behavior follows the selected mode automatically. Advanced users can still override if needed.

### Q: What happens to large payloads?
**A:** They are automatically truncated to fit within size limits (default 256KB). The truncation is clearly marked in the stored metadata.

### Q: How do I completely disable capture for a deployment?
**A:** Set the environment variable `ZENML_SERVING_CREATE_RUNS=false` to disable all run creation and capture.

---

## Environment Configuration

You can set global defaults via environment variables:

```bash
export ZENML_SERVING_CAPTURE_DEFAULT=metadata
export ZENML_SERVING_CAPTURE_SAMPLE_RATE=0.05
export ZENML_SERVING_CAPTURE_MAX_BYTES=131072
export ZENML_SERVING_CAPTURE_REDACT=username,userid,internal_id
```

---

## Advanced Configuration

For power users who need more control, the legacy format supports additional options:

```python
@step(settings={"serving": {"capture": {
    "mode": "sampled",
    "sample_rate": 0.1,
    "artifacts": "errors_only",  # Override derived behavior
    "retention_days": 30,
    "max_bytes": 131072,
    "redact": ["custom_field", "another_field"]
}}})
def advanced_step(data: str) -> str:
    return process_data(data)
```

The simplified `serving_capture` format covers the most common use cases while the legacy format remains available for edge cases requiring fine-tuned control.
