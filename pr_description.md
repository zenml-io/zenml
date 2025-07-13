# Add Modal Orchestrator with step operator and orchestrator flavors

## 🚀 Overview

This PR adds a new **Modal orchestrator** integration to ZenML, enabling users to run complete ML pipelines on Modal's serverless cloud infrastructure with optimized performance and cost efficiency.

## 📋 What does this PR do?

### 🎯 New Modal Orchestrator
- **Complete Pipeline Execution**: New orchestrator flavor that executes entire ZenML pipelines on Modal's cloud platform
- **Dual Execution Modes**: Two execution modes optimized for different use cases:
  - **`pipeline` (default)**: Runs entire pipeline in single Modal sandbox for maximum speed and cost efficiency
  - **`per_step`**: Runs each step separately for granular control, debugging, and resource optimization
- **Persistent Apps Architecture**: Implements warm container reuse with persistent Modal apps for faster execution
- **Advanced Resource Configuration**: Full support for GPU, CPU, memory settings with intelligent defaults and validation
- **Flexible Authentication**: Modal token support with fallback to default Modal CLI authentication

### 🛠️ Technical Implementation

**File Structure:**
```
src/zenml/integrations/modal/
├── orchestrators/                           # New directory
│   ├── __init__.py
│   ├── modal_orchestrator.py               # Main orchestrator implementation
│   ├── modal_orchestrator_entrypoint.py    # Pipeline execution logic
│   ├── modal_orchestrator_entrypoint_configuration.py  # Configuration
│   └── modal_sandbox_executor.py           # Sandbox execution logic
├── flavors/
│   ├── modal_orchestrator_flavor.py        # New orchestrator flavor
│   └── __init__.py                          # Updated exports
├── utils.py                                 # Shared utilities
└── __init__.py                              # Updated with orchestrator registration
```

**Key Features:**
- **Pipeline-First Design**: Uses `PipelineEntrypointConfiguration` for optimal performance
- **Smart Resource Management**: Automatic fallbacks and intelligent defaults
- **Cost Optimization**: Persistent apps with warm containers minimize cold starts
- **Stack Validation**: Ensures remote artifact store and container registry compatibility
- **Comprehensive Error Handling**: Detailed logging and error reporting with helpful suggestions

### 🔧 Enhanced Step Operator
- **Unified Utilities**: Step operator now uses shared utilities for consistency
- **Improved Resource Handling**: Better GPU, CPU, and memory configuration
- **Enhanced Authentication**: Consistent authentication patterns across components

### 📖 Documentation & Examples

**New Documentation:**
- Complete Modal orchestrator guide (`docs/book/component-guide/orchestrators/modal.md`)
- Updated orchestrator overview with Modal entry
- Enhanced step operator documentation with comparison guide

**Usage Examples:**
```python
from zenml import pipeline
from zenml.integrations.modal.flavors import ModalOrchestratorSettings
from zenml.config import ResourceSettings

# Simple GPU pipeline
@pipeline(
    settings={
        "orchestrator": ModalOrchestratorSettings(gpu="A100"),
        "resources": ResourceSettings(gpu_count=1)
    }
)
def my_pipeline():
    # Your pipeline steps here
    pass

# Advanced per-step execution with mixed resources
@pipeline(
    settings={
        "orchestrator": ModalOrchestratorSettings(
            execution_mode="per_step",
            gpu="T4",  # Default GPU
            max_parallelism=3
        )
    }
)
def mixed_resource_pipeline():
    preprocess_data()  # CPU-only
    train_model()      # A100 GPU
    evaluate_model()   # T4 GPU
```

## 🎯 Why this approach?

1. **Performance**: Running entire pipelines in single sandboxes eliminates inter-step overhead
2. **Cost Efficiency**: Fewer container spawns = lower costs on Modal's platform
3. **Flexibility**: Two execution modes serve distinct use cases effectively
4. **ZenML Native**: Leverages ZenML's existing pipeline configuration patterns
5. **User Experience**: Clean API with intelligent defaults and comprehensive validation

## 🔄 Modal Orchestrator vs Step Operator

| Feature | Modal Step Operator | Modal Orchestrator |
|---------|-------------------|-------------------|
| **Execution Scope** | Individual steps only | Entire pipeline |
| **Orchestration** | Local ZenML | Remote Modal |
| **Resource Flexibility** | Per-step resources | Pipeline-wide + per-step (per_step mode) |
| **Cost Model** | Pay per step execution | Pay per pipeline execution |
| **Setup Complexity** | Simple | Requires remote ZenML |
| **Best For** | Hybrid workflows, selective GPU usage | Full cloud execution, production |

## 📊 Key Benefits

### 🚀 Performance
- **Fast Execution**: Persistent apps eliminate deployment overhead
- **Pipeline Mode**: Single sandbox execution for maximum speed
- **Per-Step Mode**: Parallel execution with configurable concurrency

### 💰 Cost Optimization
- **Serverless Model**: Pay only for actual execution time
- **Resource Efficiency**: Right-size resources per execution mode
- **Warm Containers**: Persistent apps reduce cold start costs

### 🔧 Developer Experience
- **Simple Configuration**: Uses standard ZenML patterns
- **Comprehensive Validation**: Helpful error messages and suggestions
- **Flexible Authentication**: Multiple authentication options
- **Rich Documentation**: Complete setup and usage guides

## 🛡️ Breaking Changes

**None** - This is a new integration that doesn't affect existing functionality.

## 📦 Dependencies

- Adds `modal>=0.64.49,<1` requirement to Modal integration
- No new dependencies for core ZenML

## 🧪 Testing

- Updated existing Modal step operator tests
- Integration tests for new orchestrator components
- Validation of resource configuration logic

## 🔗 Related

- Integrates seamlessly with existing ZenML stack architecture
- Follows same patterns as other ZenML orchestrators (GCP Vertex, Kubernetes)
- Compatible with all existing ZenML components (artifact stores, container registries, etc.)

---

**Ready for Review**: This PR is ready for comprehensive review and testing. The Modal orchestrator provides a powerful new option for running ZenML pipelines on serverless infrastructure with excellent performance and cost characteristics.