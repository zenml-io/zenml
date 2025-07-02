# ZenML Prompt Abstraction Example

This example demonstrates ZenML's powerful **Prompt abstraction** for LLMOps workflows, showcasing how to treat prompts as first-class versioned artifacts.

## Overview

The Prompt abstraction enables:
- **Versioning & Comparison**: Compare results of different prompt versions
- **Easy Pipeline Rerunning**: Use ExternalArtifact to run pipelines with different prompts
- **Rich Visualizations**: HTML visualizations in the ZenML dashboard
- **Single Configurable Class**: One abstraction handles all prompt types

## Quick Start

```bash
# Install requirements
pip install -r requirements.txt

# Initialize ZenML (if not already done)
zenml init

# Run the basic pipeline
python run_basic.py

# Run the comparison pipeline
python run_comparison.py

# Run with external prompt
python run_external.py
```

## Project Structure

```
prompt_example/
├── README.md              # This file
├── requirements.txt       # Dependencies
├── run_basic.py          # Basic prompt usage
├── run_comparison.py     # Prompt A/B testing
├── run_external.py       # External artifact usage
├── pipelines/
│   ├── basic_pipeline.py     # Simple prompt pipeline
│   ├── comparison_pipeline.py # A/B testing pipeline
│   └── evaluation_pipeline.py # Evaluation pipeline
├── steps/
│   ├── prompt_creation.py    # Prompt creation steps
│   ├── llm_simulation.py     # LLM response simulation
│   ├── evaluation.py         # Evaluation steps
│   └── comparison.py         # Comparison steps
└── configs/
    ├── basic_config.yaml     # Basic pipeline config
    └── comparison_config.yaml # Comparison config
```

## Key Features Demonstrated

### 1. Prompt Versioning & Metadata
- Automatic versioning of prompt templates
- Rich metadata extraction for searchability
- Lineage tracking and evolution

### 2. A/B Testing & Comparison
- Create multiple prompt variants
- Compare performance metrics
- Identify best-performing prompts

### 3. External Artifact Integration
- Easy pipeline rerunning with new prompts
- Dashboard integration for prompt selection
- Version control and rollback

### 4. Rich Visualizations
- HTML visualizations with syntax highlighting
- Variable analysis and completion status
- Performance metrics display

## Usage Scenarios

### Basic Prompt Creation

```python
from zenml.prompts.prompt import Prompt
from zenml.artifacts.artifact_config import ArtifactConfig

@step
def create_qa_prompt() -> Annotated[Prompt, ArtifactConfig(name="qa_prompt_v1")]:
    return Prompt(
        template="Answer this question: {question}",
        variables={"question": "What is machine learning?"},
        task="question_answering",
        description="Basic Q&A prompt"
    )
```

### Prompt Comparison

```python
@pipeline
def comparison_pipeline():
    # Create variants
    prompt_v1 = create_basic_prompt()
    prompt_v2 = create_enhanced_prompt()
    
    # Compare results
    comparison = compare_prompts(prompt_v1, prompt_v2)
```

### External Artifact Usage

```python
# Via code
new_prompt = ExternalArtifact(value=Prompt(...))

# Via dashboard - select existing prompt artifact
# Via CLI - upload new prompt file
```

## Dashboard Integration

The example demonstrates how prompts appear in the ZenML dashboard:

1. **Artifact View**: Rich HTML visualizations showing:
   - Template with variable highlighting
   - Configuration and metadata
   - Performance metrics
   - Example outputs

2. **Comparison View**: Side-by-side comparison of:
   - Different prompt versions
   - Performance metrics
   - Configuration differences

3. **Pipeline View**: Clear artifact naming and tagging:
   - `ArtifactConfig` for descriptive names
   - Tags for filtering and search
   - Metadata for discovery

## Key Questions Answered

### How do I compare the result of two prompts?

1. **Create Variants**: Use `create_prompt_variants()` step
2. **Run Evaluation**: Use `evaluate_prompt_performance()` step  
3. **Compare Metrics**: Use ZenML Pro experiment comparison
4. **View Results**: Dashboard visualization shows differences

### How do I rerun a pipeline easily with a different prompt?

1. **Code**: Use `ExternalArtifact(value=new_prompt)`
2. **Dashboard**: Select "Re-run pipeline" → Upload new prompt
3. **CLI**: Use artifact management commands

### How can I easily find Prompts in the DAG visualizer?

1. **Clear Naming**: `ArtifactConfig(name="descriptive_name")`
2. **Tags**: Add relevant tags for filtering
3. **Metadata**: Rich metadata makes prompts searchable
4. **Type**: Prompts are clearly marked as `ArtifactType.DATA`

## Next Steps

1. Run the examples to see prompt artifacts in action
2. Modify prompts and observe version tracking
3. Use the dashboard to compare different runs
4. Implement your own prompt evaluation metrics

For more details, see the individual pipeline and step files in this example. 