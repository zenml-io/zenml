#!/bin/bash
set -uo pipefail

# Script to test all tutorial pipelines from the vscode-tutorial-extension repo
# This script should be run from the root of the ZenML repository
# 
# The script:
# 1. Discovers all pipeline Python files in the tutorial repo
# 2. Runs each pipeline from the repository root (required for hardcoded paths)
# 3. Uses a 5-minute timeout per pipeline to prevent hanging
# 4. Reports detailed results and fails if any pipeline fails

echo "🚀 Starting tutorial pipeline tests..."

# Validate tutorial repository structure exists
if [ ! -d "tutorial-repo" ]; then
    echo "❌ Error: tutorial-repo directory not found"
    exit 1
fi

if [ ! -d "tutorial-repo/pipelines" ]; then
    echo "❌ Error: pipelines directory not found in tutorial repository"
    exit 1
fi

# Change to the tutorial repository directory
cd tutorial-repo

echo "📁 Current directory: $(pwd)"

# Verify utils.py exists (required by most pipelines)
if [ ! -f "utils.py" ]; then
    echo "⚠️  WARNING: utils.py not found in tutorial repository root"
    echo "   Pipelines may fail to import utils module"
fi

echo "📋 Discovering pipeline files..."

# Define all pipeline files to test
PIPELINE_FILES=(
    "pipelines/caching/cache_pipeline.py"
    "pipelines/fanOut/fan_pipeline.py"
    "pipelines/helloWorld/hello_pipeline.py"
    "pipelines/metadata/meta_pipeline.py"
    "pipelines/parameters/param_pipeline.py"
    "pipelines/retries/robust_pipeline.py"
    "pipelines/stepIO/io_pipeline.py"
    "pipelines/tagging/tagged_pipeline.py"
    "pipelines/visualizations/viz_pipeline.py"
    "pipelines/yamlConfig/yaml_pipeline.py"
)

echo "📊 Found ${#PIPELINE_FILES[@]} pipeline files to test"

# Initialize counters
PASSED=0
FAILED=0
FAILED_PIPELINES=()

# Run each pipeline
for pipeline in "${PIPELINE_FILES[@]}"; do
    if [ -f "$pipeline" ]; then
        echo ""
        echo "🔍 Testing pipeline: $pipeline"
        echo "----------------------------------------"
        
        if timeout 300 env PYTHONPATH="$(pwd):${PYTHONPATH:-}" python "$pipeline"; then
            echo "✅ PASSED: $pipeline"
            ((PASSED++))
        else
            echo "❌ FAILED: $pipeline"
            ((FAILED++))
            FAILED_PIPELINES+=("$pipeline")
        fi
    else
        echo "⚠️  WARNING: Pipeline file not found: $pipeline"
        ((FAILED++))
        FAILED_PIPELINES+=("$pipeline (not found)")
    fi
done

echo ""
echo "📈 SUMMARY"
echo "=========================================="
echo "Total pipelines tested: $((PASSED + FAILED))"
echo "Passed: $PASSED"
echo "Failed: $FAILED"

if [ $FAILED -gt 0 ]; then
    echo ""
    echo "❌ FAILED PIPELINES:"
    for failed_pipeline in "${FAILED_PIPELINES[@]}"; do
        echo "  - $failed_pipeline"
    done
    echo ""
    echo "💥 Tutorial pipeline tests FAILED!"
    exit 1
else
    echo ""
    echo "🎉 All tutorial pipeline tests PASSED!"
    exit 0
fi