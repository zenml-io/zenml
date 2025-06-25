# Dashboard Implementation Guide for Prompt Visualization

This guide shows how to implement prompt visualization and comparison features in the ZenML dashboard.

## Current Dashboard Integration

The ZenML Prompt abstraction already provides rich HTML visualizations through `PromptMaterializer`. The dashboard can display these automatically using the existing `HTMLVisualization` component.

## Key Implementation Areas

### 1. Prompt Artifact Detection

The dashboard should detect prompt artifacts and display them with special styling:

```typescript
// In ArtifactIcon.tsx
const isPromptArtifact = (artifact) => {
  return artifact.metadata?.materializer_name === 'PromptMaterializer' ||
         artifact.name.toLowerCase().includes('prompt');
};
```

### 2. Enhanced Artifact Cards

Create prompt-specific cards showing:
- Task type and domain
- Prompt strategy 
- Variable count and completion status
- Performance metrics
- Target models
- Tags

### 3. Filtering and Search

Add prompt-specific filters:
- Task type (question_answering, conversation, analysis, etc.)
- Domain (technical, business, academic, creative)  
- Strategy (direct, structured, few_shot, chain_of_thought)
- Performance metrics ranges

### 4. DAG Visualizer Integration

- Purple styling for prompt artifacts in DAG nodes
- Rich tooltips showing prompt metadata
- Variable completion indicators

### 5. Comparison Features

- Side-by-side prompt comparison
- Performance metrics comparison charts
- Template diff visualization
- A/B testing results

## HTML Visualization Features

The PromptMaterializer already generates rich HTML with:

### Template Display
- Syntax highlighting for variables (`{variable_name}`)
- Template structure visualization
- Character and word counts

### Configuration Panel
- Model parameters (temperature, max_tokens)
- Target models compatibility
- Expected format requirements

### Variable Analysis
- List of all template variables
- Default values display
- Completion status indicators

### Performance Metrics
- Quality scores and rankings
- Response characteristics
- Strategy effectiveness

### Examples Section
- Few-shot examples display
- Context templates
- Instructions formatting

## Implementation Steps

### Step 1: Enhance Artifact List

```typescript
// Add prompt filtering
const PromptFilter = () => (
  <div className="filter-bar">
    <Select placeholder="Task Type">
      <Option value="question_answering">Q&A</Option>
      <Option value="conversation">Chat</Option>
      <Option value="analysis">Analysis</Option>
    </Select>
    
    <Select placeholder="Strategy">
      <Option value="direct">Direct</Option>
      <Option value="structured">Structured</Option>
      <Option value="few_shot">Few-Shot</Option>
    </Select>
  </div>
);
```

### Step 2: Create Prompt Card Component

```typescript
const PromptCard = ({ artifact, metadata }) => (
  <Card className="prompt-card">
    <CardHeader>
      <Badge variant="prompt">{metadata.task}</Badge>
      <Badge variant="outline">{metadata.domain}</Badge>
    </CardHeader>
    
    <CardContent>
      <h3>{artifact.name}</h3>
      <p>{metadata.description}</p>
      
      <div className="metrics">
        <span>Variables: {metadata.variable_count}</span>
        <span>Length: {metadata.template_length}</span>
        {metadata.performance_metrics?.overall_quality && (
          <span>Quality: {(metadata.performance_metrics.overall_quality * 100).toFixed(1)}%</span>
        )}
      </div>
    </CardContent>
  </Card>
);
```

### Step 3: Enhance DAG Visualization

```typescript
// Add prompt node styling
const getNodeStyle = (artifact) => {
  if (isPromptArtifact(artifact)) {
    return {
      border: '2px solid #8B5CF6',
      backgroundColor: '#F3E8FF',
      '&:hover': { backgroundColor: '#E9D5FF' }
    };
  }
  return defaultStyle;
};

// Add rich tooltips
const PromptTooltip = ({ metadata }) => (
  <div className="prompt-tooltip">
    <div>Task: {metadata.task}</div>
    <div>Strategy: {metadata.prompt_strategy}</div>
    <div>Variables: {metadata.variable_count}</div>
    {metadata.performance_metrics?.overall_quality && (
      <div>Quality: {(metadata.performance_metrics.overall_quality * 100).toFixed(1)}%</div>
    )}
  </div>
);
```

### Step 4: Implement Comparison View

```typescript
const PromptComparison = ({ prompts }) => (
  <div className="comparison-grid">
    {prompts.map((prompt, i) => (
      <div key={i} className="comparison-card">
        <h3>Prompt {i + 1}</h3>
        
        <Tabs>
          <Tab label="Config">
            <ConfigDisplay prompt={prompt} />
          </Tab>
          <Tab label="Template">
            <TemplatePreview template={prompt.metadata.template_preview} />
          </Tab>
          <Tab label="Metrics">
            <MetricsDisplay metrics={prompt.metadata.performance_metrics} />
          </Tab>
        </Tabs>
      </div>
    ))}
  </div>
);
```

## User Workflows

### Viewing Prompts

1. **Navigate to Artifacts** → See prompt cards with key info
2. **Click prompt artifact** → View full HTML visualization
3. **Use filters** → Find prompts by task, domain, strategy
4. **Search templates** → Find prompts containing specific text

### Comparing Prompts

1. **Select multiple prompts** → Enable comparison mode
2. **View side-by-side** → Compare templates and configs
3. **Performance comparison** → Charts showing metrics differences
4. **Export comparison** → Save comparison results

### Pipeline Integration

1. **DAG View** → Prompts highlighted with purple styling
2. **Hover tooltips** → Quick prompt info without clicking
3. **Pipeline rerun** → Select different prompt artifacts
4. **Experiment tracking** → Compare runs with different prompts

## Benefits

### For Data Scientists
- Quick prompt performance comparison
- Easy A/B testing visualization
- Template evolution tracking
- Performance metrics at a glance

### For ML Engineers  
- Clear prompt artifact identification in pipelines
- Easy prompt swapping for pipeline reruns
- Integration with existing ZenML workflows
- Rich metadata for debugging

### For Teams
- Shared prompt library with search
- Performance leaderboards
- Collaborative prompt development
- Experiment result sharing

## Technical Notes

### Data Flow
```
Python Prompt → PromptMaterializer → JSON + HTML → ZenML Store → Dashboard
```

### Existing Components Used
- `HTMLVisualization` for rich prompt display
- `MetadataCards` for structured metadata
- `ArtifactIcon` for visual identification
- Experiment comparison for A/B testing

### New Components Needed
- `PromptFilter` for specialized filtering
- `PromptCard` for summary view
- `PromptComparison` for side-by-side comparison
- Enhanced DAG styling for prompt nodes

The beauty of this approach is that most visualization logic already exists in the PromptMaterializer HTML output. The dashboard just needs to surface and organize this information effectively! 