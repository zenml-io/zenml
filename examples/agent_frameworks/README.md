# Agent Frameworks Integration with ZenML

This directory contains examples of integrating various agent frameworks with ZenML pipelines. Each example demonstrates how to zenml-ify agent systems while maintaining clean, consistent patterns.

## 📋 Established Rules & Patterns

Based on our experience integrating multiple agent frameworks, here are the key rules and best practices:

### 1. 🔧 Environment Setup
- **Use `uv` for virtual environments**: `uv venv --python 3.11` in each folder
- **Use `uv` for package installation**: `uv pip install -r requirements.txt`
- **Install ZenML integrations**: `zenml integration install s3 aws -y --uv` (when needed)

### 2. 🎯 Input Handling
- **Use ExternalArtifact for inputs**: Instead of creating input steps, use `ExternalArtifact(value="query")` to pass data directly into pipelines
- **Simple string inputs**: Prefer natural language strings over complex Pydantic models for user inputs
- **Single test case**: Focus on one example per pipeline rather than loops over multiple inputs

### 3. 📦 Artifact Management  
- **Annotated artifacts**: ALL ZenML step outputs must use `Annotated[Type, "artifact_name"]`
- **Descriptive artifact names**: Use clear names like `"agent_results"`, `"formatted_response"`, `"travel_query"`
- **Consistent types**: Use appropriate Python types (str, Dict, List) with proper annotations

### 4. 🏗️ Pipeline Structure
Follow this three-step pattern for all agent integrations:

```python
@pipeline
def agent_pipeline() -> str:
    # 1. External artifact for input
    query = ExternalArtifact(value="Your query here")
    
    # 2. Agent execution step
    results = run_agent_system(query)
    
    # 3. Output formatting step  
    summary = format_results(results)
    
    return summary
```

### 5. 🔄 Agent Execution Patterns
- **Error handling**: Always wrap agent execution in try-catch blocks
- **Resource management**: Properly start/stop runtimes or connections
- **Async handling**: Use `asyncio.run()` for async agent frameworks within sync ZenML steps
- **API compatibility**: Check the correct methods for each framework (e.g., `agent()` vs `agent.run()`)

### 6. 📝 Code Quality
- **Concise code**: No unnecessary bloat, focus on core functionality
- **Proper imports**: Use absolute imports and correct module paths
- **Type hints**: Include proper type annotations for all functions
- **Documentation**: Clear docstrings explaining what each step does

### 7. ⚡ Testing & Execution
- **Single execution**: Test with one example rather than loops
- **Pipeline validation**: Ensure each step executes successfully
- **Artifact verification**: Check that artifacts are properly stored and retrievable
- **Performance**: Aim for reasonable execution times (under 30 seconds for examples)

## 🚀 Implemented Examples

### Microsoft Autogen (`autogen/`)
- **Multi-agent coordination**: Weather + attraction specialist agents
- **Async runtime management**: Proper setup and teardown of agent runtime
- **Complex data flow**: Structured travel planning with multiple data sources

### AWS Strands (`aws-strands/`)
- **Simple tool integration**: Weather checking tool with agent
- **Direct execution**: Callable agent interface (`agent(query)`)
- **Streamlined workflow**: Single agent, single tool, focused task

### CrewAI (`crewai/`)
- **Multi-agent crews**: Weather checker + travel advisor working together
- **Task coordination**: Sequential task execution with context passing
- **Parameter handling**: Proper `inputs` dictionary for crew kickoff

### Google ADK (`google-adk/`)
- **Tool integration**: Weather and time checking capabilities with real Google ADK
- **Gemini model**: Uses gemini-1.5-flash-latest for agent responses
- **Multi-tool agent**: Single agent with multiple tool capabilities

## 📋 Implementation Checklist

When adding a new agent framework:

- [ ] Create `uv venv --python 3.11` environment
- [ ] Install requirements with `uv pip install -r requirements.txt`
- [ ] Install ZenML integrations as needed
- [ ] Create `pipeline.py` with three-step structure
- [ ] Use `ExternalArtifact` for input data
- [ ] Annotate all step outputs properly
- [ ] Add comprehensive error handling
- [ ] Test with single example execution
- [ ] Verify artifacts are stored correctly
- [ ] Update this README with framework-specific notes

## 🔍 Framework-Specific Notes

### Autogen
- Requires async runtime setup and proper agent registration
- Use `await Agent.register()` for agent registration
- Handle message serialization properly
- Resource cleanup is critical (runtime start/stop)

### AWS Strands
- Agent is callable directly: `agent(query)`
- Simple tool integration with `@tool` decorator
- Streaming responses need `str()` conversion

### CrewAI
- Use `crew.kickoff(inputs={"param": "value"})` for execution
- Set reasonable `max_iter` values to prevent timeouts
- Verbose mode can be disabled for cleaner logs
- Handle tool iteration limits gracefully

### Google ADK
- Agent is callable directly: `agent(query)` 
- Tools are passed as list during initialization
- Requires `google-genai` to be installed first to resolve dependencies
- Uses Gemini models for LLM capabilities

## 🎯 Future Frameworks

When adding new frameworks, follow the established patterns:
1. Study the framework's execution model
2. Identify the correct API methods
3. Handle async/sync execution properly  
4. Implement proper error handling
5. Use consistent artifact naming
6. Test thoroughly with ZenML integration

## 📚 Key Learnings

1. **ExternalArtifact eliminates unnecessary steps**: Don't create steps just to pass data
2. **Agent frameworks vary significantly**: Each has different APIs and execution models
3. **Error handling is crucial**: Agent execution can fail in many ways
4. **Resource management matters**: Proper cleanup prevents resource leaks
5. **Simple is better**: Focus on core functionality rather than complex features
6. **ZenML caching works well**: Leverage caching for development efficiency

---

*This documentation captures our experience integrating agent frameworks with ZenML. Update it as new patterns emerge or frameworks are added.*