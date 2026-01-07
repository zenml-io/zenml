# ZenML Pipeline Canvas Rendering Fixes - Implementation Summary

## Overview

This document summarizes the fixes implemented to resolve two critical issues in the ZenML pipeline DAG canvas:

1. **Node positioning misalignment** - Nodes collapsing to the left while arrows float to the right
2. **Missing `load_prompts` step** - Steps with named input slots disappearing from the DAG

## Root Causes Identified

### Issue 1: Node Positioning Misalignment

**Root Cause**: `RankRow` was using Ink's unreliable absolute positioning (`position="absolute"` with `left={node.x}`). While `layout.ts` correctly computed `node.x` coordinates and `ArrowRow` used character-based spacing to honor these coordinates, `RankRow` relied on Ink's layout engine to apply absolute offsets, which often fails in terminal environments.

**Symptom**: Nodes rendered at the left margin regardless of computed `x` position, while arrows remained positioned using the correct `node.x` values, creating visual misalignment.

### Issue 2: `load_prompts` Step Disappearing

**Root Cause**: The canvas had no JSON parser to convert ZenML step-run JSON into `PipelineConfig`. The graph construction likely only recognized specific input slot names (`queries`, `results`), ignoring named input slots like `single_agent_prompt`, `specialist_general_prompt`, etc. This caused `load_prompts` to have no edges and be filtered out as "disconnected."

**Symptom**: When `load_prompts` outputs were consumed via named input slots (not `queries`/`results`), the edges were never created, leaving the node disconnected.

---

## Fixes Implemented

### Fix 1: Replace RankRow Absolute Positioning with Character-Based Spacing

**File**: `claude-canvas/canvas/src/canvases/pipeline.tsx`
**Component**: `RankRow` function (lines ~276-313)

**Changes**:
- Removed: `<Box position="absolute" left={node.x} top={0}>`
- Implemented: `flexDirection="row"` container with explicit spacer `<Text>` segments
- Algorithm:
  1. Maintain `cursorX` tracking column position after previous node
  2. For each node, compute `gap = max(0, node.x - cursorX)`
  3. Render `<Text>{" ".repeat(gap)}</Text>` to position nodes
  4. Wrap `NodeComponent` in `<Box flexShrink={0} width={node.width} height={node.height}>`
  5. Update `cursorX = node.x + node.width`

**Key Props**:
- `flexDirection="row"` - Horizontal flex layout
- `flexWrap="nowrap"` - Prevent wrapping if row exceeds width
- `flexShrink={0}` on node wrapper - Preserve computed node dimensions

**Impact**: Nodes and arrows now use identical coordinate system (character-based spacing), ensuring perfect alignment.

---

### Fix 2: Implement ZenML Step-Run JSON Parser with Artifact Version ID Matching

**New Files**:
1. `claude-canvas/canvas/src/canvases/pipeline/zenml/types.ts` - Type definitions and validators
2. `claude-canvas/canvas/src/canvases/pipeline/zenml/parser.ts` - Main parsing logic
3. `claude-canvas/canvas/src/canvases/pipeline/zenml/__tests__/parser.test.ts` - Regression tests

**Modified Files**:
- `claude-canvas/canvas/src/canvases/pipeline.tsx` - Integrated parser in `handleUpdate`

**Core Algorithm**:

#### 1. Recursive Artifact Version ID Extraction
```typescript
function extractArtifactVersionIds(value: unknown): string[]
```
- Recursively traverses arbitrary nested structures
- Extracts all artifact version IDs regardless of slot names or nesting depth
- Uses weak set to track visited objects and prevent infinite loops

#### 2. Flatten Artifact Versions from Slots
```typescript
function flattenArtifactVersions(slots: Record<string, unknown>): ZenMLArtifactVersion[]
```
- Converts input/output slot records to artifact version objects
- Uses structural checks (`has id` and `has body`) to identify artifact versions
- Works with any slot name

#### 3. Build Producer Map by Artifact Version ID
```typescript
producedByArtifactVersionId: Map<string, { stepRunId, outputSlot, artifactName, artifactUri }>
```
- Index all produced artifact version IDs
- Key: artifact version ID (globally unique)
- Value: Producer step metadata

#### 4. Create Edges by Matching Artifact IDs
For each consumer step:
- Extract all artifact version IDs from inputs (via `extractArtifactVersionIds`)
- Look up each artifact ID in producer map
- Create `PipelineEdge` from producer to consumer
- Edge label: producer artifact name (or output slot if name unavailable)
- Deduplicate edges by `${from}::${to}::${label}`

#### 5. Never Filter Nodes by Connectivity
- All parsed steps become nodes, even if disconnected
- Edges are only omitted if producer/consumer doesn't exist
- Prevents legitimate steps from disappearing due to parsing gaps

**Type Guard for Integration**:
```typescript
function isPipelineConfig(value: unknown): value is PipelineConfig
```
- Allows `PipelineCanvas.handleUpdate` to accept both:
  - Pre-built `PipelineConfig` objects (tests/demos)
  - Raw ZenML step-run JSON (production IPC data)

**Integration in Pipeline Canvas**:
```typescript
const handleUpdate = useCallback((newConfig: unknown) => {
  if (isPipelineConfig(newConfig)) {
    setConfig(newConfig);
  } else {
    // Extract step runs from common payload patterns
    const stepRuns = extractStepRuns(newConfig);
    if (stepRuns) {
      setConfig(buildPipelineConfigFromStepRuns(stepRuns));
    }
  }, []);
```

**Impact**:
- `load_prompts` is now correctly identified as a node
- Edges are created via artifact version IDs, not slot names
- All steps remain in the DAG regardless of input slot naming

---

### Fix 3: Eliminate Artifact Node Overlap

**File**: `claude-canvas/canvas/src/canvases/pipeline/layout.ts`
**Function**: `positionArtifactNodes` (lines ~499-525)

**Changes**:
- Old behavior: All artifacts for same `(from,to)` pair positioned at identical `x`, causing complete overlap
- New behavior: Group artifacts by `${from}::${to}`, distribute horizontally

**Algorithm**:
1. Create map: `fromToKey` → `ArtifactNode[]`
2. For each group:
   - Calculate total group width: `sum(widths) + gaps`
   - Compute `connectionX`: midpoint between source and target nodes
   - Position group centered on `connectionX`
   - Distribute artifacts left-to-right with 2-char gap between

**Code Structure**:
```typescript
for (const [fromToKey, group] of artifactsByFromTo.entries()) {
  const widthByIndex = group.map(a => calculateArtifactWidth(a.name));
  const totalGroupWidth = sum(widths) + gaps;
  const startX = connectionX - floor(totalGroupWidth / 2);

  for (let i = 0; i < group.length; i++) {
    positioned.push({
      ...group[i],
      x: startX + sum(widths[0..i]) + i * gap,
      y, width, height
    });
  }
}
```

**Impact**: Multiple artifacts on a single edge are now visible and readable instead of overlapping.

---

## Test Coverage

**File**: `claude-canvas/canvas/src/canvases/pipeline/zenml/__tests__/parser.test.ts`

**Key Tests**:
1. **Named Input Slots** - Verifies `load_prompts` → `run_architecture_comparison` edge is created via:
   - `single_agent_prompt` (via `agent_prompt` input slot)
   - `specialist_general_prompt` (via `specialist_prompt` input slot)
   - `critic_prompt` (via `critic` input slot)
   - All connected despite different slot names

2. **Nested Artifact ID Extraction** - Tests `extractArtifactVersionIds` finds IDs in:
   - Direct objects: `{ artifact_version_id: "..." }`
   - Arrays: `[{ artifactVersionId: "..." }]`
   - Nested structures: `{ nested: { artifact_version_id: "..." } }`

3. **Disconnected Node Preservation** - Verifies all steps appear as nodes, even if:
   - No edges reference them
   - Input artifact IDs don't exist in any producer

4. **Type Guard Accuracy** - Confirms `isPipelineConfig`:
   - Returns `true` for valid `PipelineConfig` objects
   - Returns `false` for raw ZenML step-run JSON
   - Distinguishes by presence of all required fields

---

## Verification Checklist

- [x] `RankRow` uses `flexDirection="row"` with explicit spacer segments
- [x] `NodeComponent` wrapped in `<Box flexShrink={0} width height>`
- [x] Parser recursively extracts artifact version IDs from any nesting
- [x] Edges created via artifact version ID matching (slot-name agnostic)
- [x] No nodes filtered based on connectivity during parsing
- [x] `load_prompts` node appears in `config.nodes`
- [x] Edges created for all `load_prompts` outputs (single_agent, specialist_general, critic, etc.)
- [x] Artifact nodes grouped per `(from,to)` edge and distributed horizontally
- [x] Type guard distinguishes `PipelineConfig` vs raw JSON
- [x] Parser handles common ZenML API response shapes (step_runs, stepRuns, items, data, body.step_runs)
- [x] Regression tests cover named input slots scenario

---

## Files Modified

### Initial Implementation (Commit 1)
```
claude-canvas/canvas/src/canvases/pipeline.tsx
  - Updated RankRow component (flex row + spacers instead of absolute positioning)
  - Updated handleUpdate to use parser

claude-canvas/canvas/src/canvases/pipeline/layout.ts
  - Updated positionArtifactNodes (grouping + horizontal distribution)

claude-canvas/canvas/src/canvases/pipeline/zenml/types.ts
  - NEW: ZenML JSON type definitions and validators

claude-canvas/canvas/src/canvases/pipeline/zenml/parser.ts
  - NEW: Step-run JSON parser with artifact version ID matching

claude-canvas/canvas/src/canvases/pipeline/zenml/__tests__/parser.test.ts
  - NEW: Regression tests for named input slots scenario
```

### Post-Implementation Refinements (Commit 2)
```
claude-canvas/canvas/src/canvases/pipeline/zenml/types.ts
  - Extended ZenMLArtifactVersion to accept top-level uri/artifact fields
  - Improved isZenMLArtifactVersion to check both nested and top-level locations
  - Updated getZenMLArtifactName/getZenMLArtifactUri to try both field locations

claude-canvas/canvas/src/canvases/pipeline/zenml/parser.ts
  - Enhanced buildPipelineConfigFromStepRuns producer extraction
  - Now uses extractArtifactVersionIds on ALL outputs first
  - Enriches metadata from full artifact versions when available
  - Handles both lightweight refs and full-featured artifact objects

claude-canvas/canvas/src/canvases/pipeline.tsx
  - Enhanced ArrowRow with artifact connector lines
  - Groups artifacts by (from,to) edge pair
  - Draws horizontal lines linking artifact groups to target arrows
  - Respects selection highlighting and canvas width
```

---

## Design Principles

### 1. Coordinate System Consistency
Both node rendering (`RankRow`) and arrow rendering (`ArrowRow`) now use identical character-based spacing. No reliance on Ink's unreliable absolute positioning.

### 2. Slot-Name Agnostic Edge Building
The parser uses artifact version IDs as the universal edge key, making graph construction robust to:
- Unknown input slot names
- Dynamic slot naming
- Named inputs like prompts, not just query/result patterns

### 3. Preserve All Data
No nodes are filtered during parsing based on edge connectivity. This allows:
- Visualizing disconnected components
- Preventing silent data loss
- Making parsing gaps visible during debugging

### 4. Type Safety
Type guards (`isPipelineConfig`, `isZenMLStepRun`, `isZenMLArtifactVersion`) ensure:
- Correct payload detection at integration boundary
- Structural validation without strict schema enforcement
- Graceful handling of API variation

---

## Post-Implementation Improvements (Applied)

### Issue: Missing `load_prompts` Outputs

**Diagnosis**: Producer extraction was too strict—it only accepted artifact versions with full nested structure (`body.uri` AND `body.artifact.name`). Lightweight output refs like `{ artifact_version_id: "..." }` were never indexed, so downstream consumers couldn't form edges.

**Solution**:
- Modified `buildPipelineConfigFromStepRuns` to use `extractArtifactVersionIds(outputValue)` on ALL outputs first
- Creates producer mappings even for lightweight refs
- Then enriches with metadata when full artifact version objects are available
- Producer map now includes both lightweight and full-featured output shapes

**Result**: All `load_prompts` outputs now generate producer mappings, enabling complete fan-out to downstream steps.

### Issue: Orphaned Artifact Labels

**Diagnosis**: Artifacts were positioned correctly but had no visual connection to edges. The renderer doesn't draw full routed polylines (would be too complex for terminal), only vertical arrows under nodes. Artifacts positioned mid-edge looked disconnected.

**Solution**:
- Added artifact grouping in `ArrowRow` by `${from}::${to}` key
- Draw horizontal connector lines from artifact group's span to target node's arrow column
- Visual connection makes artifacts appear anchored to edges
- Respects selection highlighting and canvas width constraints

**Result**: Artifacts no longer appear orphaned; visual connector lines anchor them to their edges.

### Issue: Type Tolerance

**Diagnosis**: `ZenMLArtifactVersion` type and validators were too strict about nested structure. Different ZenML API versions may return `uri` and `artifact` fields at top level instead of nested under `body`.

**Solution**:
- Extended `ZenMLArtifactVersion` type to accept both nested and top-level fields
- Improved `isZenMLArtifactVersion` heuristic to check either location
- Updated `getZenMLArtifactName` and `getZenMLArtifactUri` to check both locations

**Result**: Parser tolerates multiple ZenML payload shapes, improving robustness across API versions.

---

## Future Improvements (Optional Enhancements)

1. **Artifact Count Limiting** (Optional polish)
   - Cap inline artifacts displayed per edge
   - Add "+N more" synthetic labels for large artifact sets
   - Mentioned in colleague's document as bonus feature

2. **Status Mapping Enhancement**
   - Map ZenML-specific statuses (cached, skipped) to UI states
   - Currently maps to simple 4-state model (pending/running/completed/failed)

3. **Error Boundary**
   - Add error handling in parser for malformed payloads
   - Surface parsing errors in UI

4. **Performance Optimization**
   - Memoize parser result if step-run JSON received frequently
   - Cache artifact version ID lookups for large pipelines

5. **Bare ID Detection** (Edge case handling)
   - Extend `tryGetArtifactVersionId` with safe heuristic for bare `{ id }` objects
   - Current implementation requires at least a URI or artifact name hint
   - If real payloads contain bare IDs, add conservative detection

---

## Testing the Fix

### Minimal Reproduction
Create a pipeline with:
1. `load_prompts` step outputting 3+ named artifacts
2. `run_architecture_comparison` step consuming via named input slots
3. Additional steps with direct edges (queries/results pattern)

**Before Fix**:
- Nodes left-aligned, arrows floating to the right
- `load_prompts` missing from DAG

**After Fix**:
- Nodes and arrows perfectly aligned
- All 5+ steps visible
- Multiple artifacts between steps readable

### Run Tests
```bash
cd claude-canvas/canvas
npm test src/canvases/pipeline/zenml/__tests__/parser.test.ts
```

---

## Implementation Notes

- **No breaking changes** - Parser is purely additive; existing `PipelineConfig` objects still work
- **Backward compatible** - `handleUpdate` still accepts pre-built configs via type guard
- **Deterministic** - Character-based spacing and artifact version ID matching produce identical results across runs
- **Minimal dependencies** - Parser uses only built-in TypeScript/JavaScript, no new external packages
