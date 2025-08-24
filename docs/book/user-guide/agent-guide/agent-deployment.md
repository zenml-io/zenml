---
description: Deploy your winning agent configuration with observability and continuous improvement.
---

# Production & deployment

You've systematically developed agents ([Chapter 1](agent-fundamentals.md)) and now it's time to deploy these agents in production while maintaining the same systematic approach for monitoring and improvement.

## Deploying Your Winning Configuration

From Chapter 1, you now have systematically developed agent configurations:

```python
# From Chapter 1 - you have systematically developed configurations
agent_configs = complete_agent_development_pipeline(config, test_queries)
# Result: Tracked experiments with different approaches
```

Now deploy this configuration while maintaining ZenML integration.

## Deploying Your Agent

Here's how to deploy your systematically developed agent from Chapter 1 while maintaining ZenML integration:

```python
# production_server.py
from fastapi import FastAPI
from zenml.client import Client

# Load your agent implementation from Chapter 1
from agent_implementation import (
    run_direct_llm_agent,
    run_framework_agent, 
    run_custom_agent
)

app = FastAPI()

def get_production_setup():
    """Load agent implementation and configuration from ZenML."""
    
    client = Client()
    model = client.get_model("customer_support_agent")
    production_version = model.get_model_version("production")
    
    # Load artifacts stored in Chapter 1
    config = production_version.load_artifact("agent_configuration")
    prompts = production_version.load_artifact("agent_prompts")
    
    # Choose which agent implementation to use
    agent_type = config.get("agent_type", "direct")
    if agent_type == "direct":
        agent_func = run_direct_llm_agent
    elif agent_type == "framework":
        agent_func = run_framework_agent
    else:
        agent_func = run_custom_agent
    
    return agent_func, config, prompts, production_version.version

@app.post("/chat")
async def chat_endpoint(query: str):
    """Production endpoint running your systematically developed agent."""
    
    try:
        agent_func, config, prompts, version = get_production_setup()
        
        # Run your actual agent code with ZenML-managed configuration
        response = agent_func(
            query=query,
            config=config,
            prompts=prompts
        )
        
        # Log interaction for evaluation
        # You can use langfuse, langsmith or any tool you prefer
        log_production_interaction({
            "query": query,
            "response": response,
            "agent_version": version,
            "timestamp": datetime.now()
        })
        
        return {"response": response}
        
    except Exception as e:
        return {"error": "Agent temporarily unavailable"}

@app.get("/health")
async def health_check():
    """Validate deployment and ZenML connectivity."""
    
    try:
        _, config, _, version = get_production_setup()
        return {
            "status": "healthy",
            "agent_version": version,
            "agent_type": config.get("agent_type", "direct")
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

Deploy this however you prefer - locally, in containers, or on cloud platforms:

```bash
# Local development
python production_server.py

# Docker deployment  
docker build -t my-agent . && docker run -p 8000:8000 my-agent

# Cloud deployment (AWS ECS, Google Cloud Run, etc.)
# Use your organization's deployment pipeline
```

### Configuration Management with ZenML Artifacts

As shown above, loading configuration artifacts is a common pattern—and you can apply the same approach to other components such as prompts, tool definitions, or any agent resource. By storing each as a ZenML artifact, you ensure reproducibility and complete lineage for every part of your agent pipeline.

```python
from zenml.client import Client
from zenml import step, pipeline
from typing_extensions import Annotated

@step
def store_agent_prompts() -> Annotated[Dict[str, str], "agent_prompts"]:
    """Store agent prompts as versioned artifacts."""
    
    prompts = {
        "system_prompt": """You are a helpful customer support assistant.
        Always be polite and try to resolve customer issues efficiently.
        If you cannot help, escalate to a human agent.""",
        
        "tool_selection_prompt": """Given the customer query, determine which tools to use.
        Available tools: search_knowledge_base, create_ticket, transfer_to_human.""",
        
        "summary_prompt": """Summarize this customer interaction in 2-3 sentences.
        Include the issue, resolution, and customer satisfaction."""
    }
    
    return prompts

@step  
def store_agent_config() -> Annotated[Dict[str, Any], "agent_configuration"]:
    """Store complete agent configuration."""
    
    config = {
        "model": "gpt-4",
        "temperature": 0.1,
        "max_tokens": 1000,
        "timeout": 30,
        "retry_attempts": 3,
        "tools_enabled": ["knowledge_search", "ticket_creation"],
        "fallback_enabled": True
    }
    
    return config

@pipeline
def agent_configuration_pipeline() -> None:
    """Create versioned agent configuration artifacts."""
    
    # Store prompts and config as separate artifacts
    prompts = store_agent_prompts()
    config = store_agent_config()
    
    # These are automatically versioned and tracked by ZenML

# Run this pipeline when you update prompts/config
agent_configuration_pipeline()
```

### Loading Configuration in Production

```python
from zenml.client import Client

def get_production_agent_config():
    """Load production configuration with full ZenML lineage."""
    
    client = Client()
    
    # Get the production model version
    model = client.get_model("customer_support_agent")
    production_version = model.get_model_version("production")
    
    # Load individual artifacts
    prompts = production_version.load_artifact("agent_prompts")
    config = production_version.load_artifact("agent_configuration")
    
    return {
        "prompts": prompts,
        "config": config,
        "version": production_version.version,
        "deployed_at": production_version.created,
        "lineage": production_version.metadata
    }

@app.post("/chat")
async def production_endpoint(query: str):
    """Production endpoint using ZenML-managed prompts and config."""
    
    # Load current production configuration
    production_setup = get_production_agent_config()
    prompts = production_setup["prompts"]
    config = production_setup["config"]
    
    # Use versioned prompts in your agent
    response = openai_client.chat.completions.create(
        model=config["model"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
        messages=[
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": query}
        ]
    )
    
    # Log which configuration version was used
    return {
        "response": response.choices[0].message.content,
        "config_version": production_setup["version"],
        "model_used": config["model"]
    }
```

### Prompt Versioning and A/B Testing

```python
@pipeline
def prompt_ab_test_pipeline() -> None:
    """Create A/B test versions of prompts."""
    
    # Version A - Current prompt
    @step
    def create_prompt_variant_a() -> Annotated[str, "system_prompt_v1"]:
        return """You are a helpful customer support assistant.
        Always be polite and try to resolve customer issues efficiently."""
    
    # Version B - More detailed prompt
    @step  
    def create_prompt_variant_b() -> Annotated[str, "system_prompt_v2"]:
        return """You are an expert customer support assistant with deep product knowledge.
        Begin each response by acknowledging the customer's concern.
        Provide step-by-step solutions when possible.
        Always ask if there's anything else you can help with."""
    
    prompt_a = create_prompt_variant_a()
    prompt_b = create_prompt_variant_b()

def deploy_prompt_variant(variant: str, traffic_split: float = 0.5):
    """Deploy specific prompt variant with traffic splitting."""
    
    client = Client()
    
    if variant == "A":
        artifact_name = "system_prompt_v1"
    else:
        artifact_name = "system_prompt_v2"
    
    # Get the specific prompt version
    artifact = client.get_artifact_version(artifact_name, version="latest")
    
    # Update production deployment with traffic split
    update_production_prompt(artifact.load(), traffic_split)
```

### Configuration Rollback and Updates

```python
def rollback_to_previous_config():
    """Rollback to previous configuration version."""
    
    client = Client()
    model = client.get_model("customer_support_agent")
    
    # Get previous production version
    versions = model.list_model_versions()
    previous_version = versions[1]  # Second most recent
    
    # Rollback
    previous_version.set_stage("production")
    
    print(f"Rolled back to version {previous_version.version}")
    restart_production_deployment()

def update_production_config(new_version: str):
    """Promote new version to production."""
    
    client = Client()
    model = client.get_model("customer_support_agent")
    
    # Promote new version
    new_model_version = model.get_model_version(new_version)
    new_model_version.set_stage("production")
    
    # Validate configuration before deployment
    config = new_model_version.load_artifact("agent_configuration")
    prompts = new_model_version.load_artifact("agent_prompts")
    
    if validate_configuration(config, prompts):
        restart_production_deployment()
        print(f"Successfully deployed version {new_version}")
    else:
        print("Configuration validation failed, aborting deployment")
```

## Next Steps

Your agents are now deployed in production with proper observability and monitoring. The traces and logs you're collecting will be essential for Chapter 3, where we'll use this production data to systematically evaluate and improve your agents.

Key data being collected:
- **User interactions** and agent responses
- **Performance metrics** (response times, success rates)
- **Error patterns** and failure modes
- **Configuration lineage** connecting to your ZenML development experiments

In [Chapter 3](agent-evaluation.md), you'll learn how to systematically analyze this production data to identify improvement opportunities and create a continuous feedback loop back to your ZenML development process.