# ZenML Dashboard Implementation Guide for Prompt Artifacts

This guide provides detailed instructions for implementing prompt visualization and comparison features in the ZenML dashboard.

## Overview

The ZenML Prompt abstraction already provides rich HTML visualizations through the `PromptMaterializer`. This guide shows how to enhance the dashboard to:

1. **Display Prompt Artifacts**: Rich visualization of prompt templates, variables, and metadata
2. **Compare Prompts**: Side-by-side comparison of different prompt versions
3. **Search & Filter**: Find prompts by task, domain, strategy, and performance metrics
4. **Pipeline Integration**: Clear visibility of prompts in DAG visualizer

## Current State

The dashboard already supports:
- ✅ HTML artifact visualization via `HTMLVisualization` component
- ✅ Artifact metadata display via `MetadataCards` component
- ✅ Artifact filtering and search capabilities
- ✅ Pipeline run comparison features

## Implementation Steps

### 1. Enhance Artifact Type Detection

**File:** `tmp/zenml-dashboard/src/components/ArtifactIcon.tsx`

```typescript
// Add prompt-specific icon handling
const getArtifactIcon = (artifactType: string, artifactName: string) => {
  // Check if artifact is a prompt based on materializer or name patterns
  if (artifactName.toLowerCase().includes('prompt') || 
      artifactType === 'prompt' ||
      metadata?.materializer_name === 'PromptMaterializer') {
    return <MessageSquare className="h-4 w-4" />; // Use appropriate prompt icon
  }
  // ... existing logic
}
```

### 2. Create Prompt-Specific Artifact Card

**New File:** `tmp/zenml-dashboard/src/components/artifacts/PromptArtifactCard.tsx`

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@zenml-io/react-component-library";
import { Badge } from "@zenml-io/react-component-library";

interface PromptArtifactCardProps {
  artifact: ArtifactVersion;
  metadata: Record<string, any>;
}

export function PromptArtifactCard({ artifact, metadata }: PromptArtifactCardProps) {
  const promptMetadata = metadata || {};
  
  return (
    <Card className="prompt-artifact-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          {artifact.name}
          <Badge variant="outline">{promptMetadata.version || 'v1.0.0'}</Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Task and Domain */}
        <div className="flex gap-2">
          {promptMetadata.task && (
            <Badge variant="secondary">{promptMetadata.task}</Badge>
          )}
          {promptMetadata.domain && (
            <Badge variant="outline">{promptMetadata.domain}</Badge>
          )}
          {promptMetadata.prompt_strategy && (
            <Badge variant="outline">{promptMetadata.prompt_strategy}</Badge>
          )}
        </div>
        
        {/* Description */}
        {promptMetadata.description && (
          <p className="text-sm text-muted-foreground">
            {promptMetadata.description}
          </p>
        )}
        
        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="font-medium">Template Length:</span>
            <span className="ml-1">{promptMetadata.template_length || 'N/A'} chars</span>
          </div>
          <div>
            <span className="font-medium">Variables:</span>
            <span className="ml-1">{promptMetadata.variable_count || 0}</span>
          </div>
          <div>
            <span className="font-medium">Target Models:</span>
            <span className="ml-1">{promptMetadata.target_models?.join(', ') || 'Any'}</span>
          </div>
          <div>
            <span className="font-medium">Complete:</span>
            <Badge variant={promptMetadata.variables_complete ? "default" : "destructive"}>
              {promptMetadata.variables_complete ? "Yes" : "No"}
            </Badge>
          </div>
        </div>
        
        {/* Performance Metrics if available */}
        {promptMetadata.performance_metrics && (
          <div className="border-t pt-4">
            <h4 className="font-medium mb-2">Performance</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {Object.entries(promptMetadata.performance_metrics).map(([key, value]) => (
                <div key={key}>
                  <span className="capitalize">{key.replace('_', ' ')}:</span>
                  <span className="ml-1 font-mono">{typeof value === 'number' ? value.toFixed(2) : value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Tags */}
        {promptMetadata.tags && promptMetadata.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {promptMetadata.tags.map((tag: string) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### 3. Enhance Artifact List View

**File:** `tmp/zenml-dashboard/src/app/artifacts/page.tsx`

```typescript
// Replace the Pro promotion with actual artifact management
import { ArtifactsList } from "@/components/artifacts/ArtifactsList";
import { PromptFilter } from "@/components/artifacts/PromptFilter";

export default function ArtifactsPage() {
  return (
    <div className="layout-container space-y-5 py-5">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Artifacts</h1>
        <PromptFilter />
      </div>
      
      <ArtifactsList />
    </div>
  );
}
```

### 4. Create Prompt Filtering Component

**New File:** `tmp/zenml-dashboard/src/components/artifacts/PromptFilter.tsx`

```typescript
import { Input } from "@zenml-io/react-component-library";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@zenml-io/react-component-library";

interface PromptFilterProps {
  onFilterChange: (filters: PromptFilters) => void;
}

interface PromptFilters {
  search: string;
  task: string;
  domain: string;
  strategy: string;
}

export function PromptFilter({ onFilterChange }: PromptFilterProps) {
  const [filters, setFilters] = useState<PromptFilters>({
    search: '',
    task: '',
    domain: '',
    strategy: ''
  });

  const updateFilter = (key: keyof PromptFilters, value: string) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  return (
    <div className="flex gap-4 items-center">
      <Input
        placeholder="Search prompts..."
        value={filters.search}
        onChange={(e) => updateFilter('search', e.target.value)}
        className="w-64"
      />
      
      <Select value={filters.task} onValueChange={(value) => updateFilter('task', value)}>
        <SelectTrigger className="w-48">
          <SelectValue placeholder="Filter by task" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="">All Tasks</SelectItem>
          <SelectItem value="question_answering">Question Answering</SelectItem>
          <SelectItem value="conversation">Conversation</SelectItem>
          <SelectItem value="analysis">Analysis</SelectItem>
          <SelectItem value="summarization">Summarization</SelectItem>
        </SelectContent>
      </Select>
      
      <Select value={filters.domain} onValueChange={(value) => updateFilter('domain', value)}>
        <SelectTrigger className="w-48">
          <SelectValue placeholder="Filter by domain" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="">All Domains</SelectItem>
          <SelectItem value="technical">Technical</SelectItem>
          <SelectItem value="business">Business</SelectItem>
          <SelectItem value="academic">Academic</SelectItem>
          <SelectItem value="creative">Creative</SelectItem>
        </SelectContent>
      </Select>
      
      <Select value={filters.strategy} onValueChange={(value) => updateFilter('strategy', value)}>
        <SelectTrigger className="w-48">
          <SelectValue placeholder="Filter by strategy" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="">All Strategies</SelectItem>
          <SelectItem value="direct">Direct</SelectItem>
          <SelectItem value="structured">Structured</SelectItem>
          <SelectItem value="conversational">Conversational</SelectItem>
          <SelectItem value="few_shot">Few Shot</SelectItem>
          <SelectItem value="chain_of_thought">Chain of Thought</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
```

### 5. Enhance DAG Visualizer for Prompts

**File:** `tmp/zenml-dashboard/src/components/dag-visualizer/` (various files)

```typescript
// Add prompt-specific node styling
const getNodeStyle = (artifact: ArtifactVersion) => {
  const metadata = artifact.metadata || {};
  
  if (metadata.materializer_name === 'PromptMaterializer' || 
      artifact.name.toLowerCase().includes('prompt')) {
    return {
      ...defaultStyle,
      border: '2px solid #8B5CF6', // Purple border for prompts
      backgroundColor: '#F3E8FF', // Light purple background
      '&:hover': {
        backgroundColor: '#E9D5FF'
      }
    };
  }
  
  return defaultStyle;
};

// Add prompt information to node tooltips
const PromptNodeTooltip = ({ artifact }) => {
  const metadata = artifact.metadata || {};
  
  return (
    <div className="prompt-tooltip">
      <h4 className="font-bold">{artifact.name}</h4>
      <div className="space-y-1 text-sm">
        <div>Task: {metadata.task || 'Unknown'}</div>
        <div>Strategy: {metadata.prompt_strategy || 'Direct'}</div>
        <div>Variables: {metadata.variable_count || 0}</div>
        <div>Template: {metadata.template_length || 0} chars</div>
        {metadata.performance_metrics?.overall_quality && (
          <div>Quality: {(metadata.performance_metrics.overall_quality * 100).toFixed(1)}%</div>
        )}
      </div>
    </div>
  );
};
```

### 6. Create Prompt Comparison View

**New File:** `tmp/zenml-dashboard/src/components/artifacts/PromptComparison.tsx`

```typescript
import { Card, CardContent, CardHeader, CardTitle } from "@zenml-io/react-component-library";
import { Badge } from "@zenml-io/react-component-library";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@zenml-io/react-component-library";

interface PromptComparisonProps {
  prompts: ArtifactVersion[];
}

export function PromptComparison({ prompts }: PromptComparisonProps) {
  return (
    <div className="prompt-comparison">
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {prompts.map((prompt, index) => (
          <PromptComparisonCard key={prompt.id} prompt={prompt} index={index} />
        ))}
      </div>
      
      <div className="mt-8">
        <ComparisonChart prompts={prompts} />
      </div>
    </div>
  );
}

function PromptComparisonCard({ prompt, index }: { prompt: ArtifactVersion; index: number }) {
  const metadata = prompt.metadata || {};
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          Prompt {index + 1}
          <Badge variant="outline" className="ml-2">{metadata.version}</Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        <Tabs defaultValue="config" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="config">Config</TabsTrigger>
            <TabsTrigger value="template">Template</TabsTrigger>
            <TabsTrigger value="metrics">Metrics</TabsTrigger>
          </TabsList>
          
          <TabsContent value="config" className="space-y-2">
            <div className="text-sm">
              <div><strong>Task:</strong> {metadata.task}</div>
              <div><strong>Domain:</strong> {metadata.domain}</div>
              <div><strong>Strategy:</strong> {metadata.prompt_strategy}</div>
              <div><strong>Temperature:</strong> {metadata.temperature || 'Default'}</div>
            </div>
          </TabsContent>
          
          <TabsContent value="template" className="space-y-2">
            <div className="text-sm font-mono bg-gray-50 p-3 rounded">
              {metadata.template_preview || 'Template preview not available'}
            </div>
            <div className="text-xs text-muted-foreground">
              {metadata.template_length} characters, {metadata.variable_count} variables
            </div>
          </TabsContent>
          
          <TabsContent value="metrics" className="space-y-2">
            {metadata.performance_metrics ? (
              <div className="space-y-2">
                {Object.entries(metadata.performance_metrics).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="capitalize">{key.replace('_', ' ')}:</span>
                    <span className="font-mono">
                      {typeof value === 'number' ? value.toFixed(2) : value}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">No metrics available</div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
```

### 7. Add Search and Discovery Features

**Enhancement to existing search components:**

```typescript
// Add prompt-specific search filters to global search
const promptSearchFilters = {
  artifacts: {
    prompts: {
      materializer: 'PromptMaterializer',
      metadata_keys: [
        'task',
        'domain', 
        'prompt_strategy',
        'target_models',
        'performance_metrics'
      ]
    }
  }
};

// Add prompt template search
const searchPromptTemplates = (query: string, artifacts: ArtifactVersion[]) => {
  return artifacts.filter(artifact => {
    const metadata = artifact.metadata || {};
    if (metadata.materializer_name !== 'PromptMaterializer') return false;
    
    const searchTerms = query.toLowerCase().split(' ');
    const searchableText = [
      artifact.name,
      metadata.description,
      metadata.task,
      metadata.domain,
      metadata.prompt_strategy,
      ...(metadata.tags || []),
      metadata.template_preview
    ].join(' ').toLowerCase();
    
    return searchTerms.every(term => searchableText.includes(term));
  });
};
```

## How to Use the Enhanced Dashboard

### 1. Viewing Prompt Artifacts

After running prompt pipelines:

1. **Navigate to Artifacts page** - See all prompt artifacts with rich metadata cards
2. **Click on a prompt** - View detailed HTML visualization with:
   - Template with variable highlighting
   - Configuration and model parameters
   - Performance metrics (if available)
   - Examples and instructions
   - Variable analysis

### 2. Comparing Prompts

1. **Pipeline Comparison**: Use ZenML Pro experiment comparison to compare runs with different prompts
2. **Artifact Comparison**: Select multiple prompt artifacts for side-by-side comparison
3. **Performance Analysis**: View metrics comparison charts and best performer identification

### 3. Finding Prompts in DAG

1. **Visual Distinction**: Prompt artifacts appear with purple styling in DAG visualizer
2. **Rich Tooltips**: Hover over prompt nodes to see task, strategy, and quality metrics
3. **Search Integration**: Use artifact search to find specific prompts by name, task, or domain
4. **Tag Filtering**: Filter pipeline runs by prompt-related tags

### 4. Pipeline Rerunning Workflow

1. **Select Pipeline Run**: Choose a completed run with prompt artifacts
2. **Click "Re-run"**: Dashboard shows rerun options
3. **Upload New Prompt**: Option to upload new prompt JSON file or select existing prompt
4. **Compare Results**: After completion, compare new run with original

## Technical Implementation Notes

### Data Flow

```
Prompt (Python) → PromptMaterializer → JSON + HTML → ZenML Store → Dashboard → Visualization
```

### Key Integration Points

1. **Artifact Metadata**: Dashboard reads metadata extracted by PromptMaterializer
2. **HTML Visualization**: Uses existing HTMLVisualization component for rich display
3. **Search Index**: Prompt metadata is indexed for fast search and filtering
4. **Comparison Engine**: Leverages existing experiment comparison infrastructure

### Performance Considerations

1. **Lazy Loading**: Load prompt visualizations on demand
2. **Metadata Caching**: Cache frequently accessed prompt metadata
3. **Search Optimization**: Index prompt-specific fields for fast search
4. **Template Preview**: Show truncated template previews in list views

## Summary

This implementation plan provides:

✅ **Rich Prompt Visualization** - Template highlighting, metadata display, performance metrics  
✅ **Easy Comparison** - Side-by-side prompt comparison with metrics  
✅ **Powerful Search** - Find prompts by task, domain, strategy, performance  
✅ **DAG Integration** - Clear prompt visibility in pipeline visualizer  
✅ **Rerun Workflows** - Easy pipeline rerunning with different prompts  

The beauty of this approach is that it leverages ZenML's existing visualization infrastructure while adding prompt-specific enhancements. The HTML materializer already provides rich visualizations - the dashboard just needs to surface and organize this information effectively.

All the core functionality for prompt artifacts already exists in the ZenML Prompt abstraction. This guide shows how to expose that power through an intuitive dashboard experience. 