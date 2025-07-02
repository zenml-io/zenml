"""Steps for simulating LLM responses to prompts."""

from typing import Annotated, List, Optional

from zenml import step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.logger import get_logger
from zenml.prompts.prompt import Prompt

logger = get_logger(__name__)


@step
def simulate_llm_response(
    prompt: Prompt, query: Optional[str] = None
) -> Annotated[
    str, ArtifactConfig(name="llm_response", tags=["response", "simulation"])
]:
    """Simulate an LLM response to demonstrate prompt functionality."""
    # Use provided query or default from prompt variables
    if query is None:
        query = prompt.variables.get(
            "question", "What are the benefits of microservices?"
        )

    # Try to format the prompt
    try:
        formatted_prompt = prompt.format()
        logger.info(
            f"Successfully formatted prompt: {formatted_prompt[:100]}..."
        )
    except Exception as e:
        logger.warning(f"Could not format prompt: {e}")
        formatted_prompt = prompt.template

    # Simulate different responses based on prompt characteristics
    if prompt.task == "question_answering":
        if prompt.prompt_strategy == "structured":
            response = generate_structured_response(prompt, query)
        elif prompt.prompt_strategy == "conversational":
            response = generate_conversational_response(prompt, query)
        elif prompt.prompt_strategy == "pros_cons":
            response = generate_pros_cons_response(prompt, query)
        else:
            response = generate_direct_response(prompt, query)

    elif prompt.task == "conversation":
        response = generate_conversational_response(prompt, query)

    elif prompt.task == "interview":
        response = generate_interview_response(prompt, query)

    elif prompt.task == "analysis":
        response = generate_analysis_response(prompt, query)

    else:
        response = generate_default_response(prompt, query)

    # Add simulation metadata to response
    response += f"\n\n---\n*Simulated response using {prompt.prompt_type} prompt with {prompt.prompt_strategy} strategy*"
    response += f"\n*Temperature: {prompt.model_config_params.get('temperature', 'default') if prompt.model_config_params else 'default'}*"
    response += f"\n*Max tokens: {prompt.model_config_params.get('max_tokens', 'default') if prompt.model_config_params else 'default'}*"

    logger.info(f"Generated response of {len(response)} characters")
    return response


@step
def simulate_multiple_responses(
    prompts: List[Prompt],
) -> Annotated[
    List[str],
    ArtifactConfig(
        name="multiple_responses", tags=["responses", "comparison"]
    ),
]:
    """Simulate responses for multiple prompts."""

    responses = []
    for i, prompt in enumerate(prompts):
        logger.info(
            f"Simulating response for prompt variant {i + 1}/{len(prompts)}"
        )
        response = simulate_llm_response.entrypoint(prompt)
        responses.append(response)

    logger.info(f"Generated {len(responses)} responses for comparison")
    return responses


def generate_structured_response(prompt: Prompt, query: str) -> str:
    """Generate a structured academic-style response."""
    return f"""**Analysis of Microservices Architecture Benefits**

1. **Definition and Context**
Microservices architecture is a software design approach where applications are built as a collection of loosely coupled, independently deployable services.

2. **Key Benefits with Explanations**
- **Scalability**: Individual services can be scaled based on demand
- **Technology Diversity**: Teams can choose optimal tools for each service
- **Fault Isolation**: Failures in one service don't cascade to others
- **Independent Development**: Teams can work autonomously on different services

3. **Supporting Evidence**
Industry leaders like Netflix, Amazon, and Uber have successfully implemented microservices to handle massive scale and complexity.

4. **Potential Limitations**
- Increased operational complexity
- Network latency between services
- Data consistency challenges

5. **Conclusion**
Microservices offer significant benefits for large-scale applications but require careful consideration of trade-offs."""


def generate_conversational_response(prompt: Prompt, query: str) -> str:
    """Generate a conversational-style response."""
    return f"""Hey! Great question about microservices! 🚀

So here's the thing - microservices are pretty awesome for a few key reasons:

**Main points:**
- You can scale individual parts of your app independently (super helpful!)
- Different teams can use different tech stacks for different services
- If one service goes down, the rest keep working
- Faster development cycles since teams aren't stepping on each other

**Real example:** Think about Netflix - they have hundreds of microservices. When their recommendation engine needs updating, they don't have to touch their video streaming service. Pretty cool, right?

**Why it matters:** As companies grow, monolithic apps become nightmares to maintain. Microservices let you break things down into manageable pieces.

The main trade-off? It's more complex to set up initially, but the long-term benefits are usually worth it for bigger projects."""


def generate_pros_cons_response(prompt: Prompt, query: str) -> str:
    """Generate a pros and cons analysis."""
    return f"""**Analysis: Microservices Architecture Benefits**

**PROS:**
1. **Independent Scaling** - Scale only the services that need it, saving resources
2. **Technology Flexibility** - Use the best tool for each specific job
3. **Fault Tolerance** - Service failures are isolated and don't crash the entire system
4. **Team Autonomy** - Different teams can work independently with minimal coordination
5. **Deployment Speed** - Deploy individual services without affecting others

**CONS:**
1. **Operational Complexity** - More services mean more monitoring, logging, and debugging
2. **Network Overhead** - Communication between services adds latency and potential failure points
3. **Data Management** - Distributed data consistency becomes challenging
4. **Testing Complexity** - Integration testing across multiple services is more difficult
5. **Initial Setup Cost** - Requires significant upfront investment in infrastructure

**CONCLUSION:**
Microservices are excellent for large, complex applications with multiple teams, but may be overkill for smaller projects. The benefits typically outweigh the costs for organizations at scale."""


def generate_interview_response(prompt: Prompt, query: str) -> str:
    """Generate an expert interview-style response."""
    return f"""From my 15 years in enterprise architecture, I can tell you that microservices have been a game-changer.

The biggest win? **Independent scalability**. I've seen systems where one service handles 10x more traffic than others. With monoliths, you'd have to scale everything. With microservices, you scale what you need.

**Technology diversity** is another huge advantage. My team uses Go for high-performance services, Python for ML pipelines, and Node.js for real-time features. Try doing that with a monolith!

**Fault isolation** saved us countless times. When our recommendation service went down, users could still browse and purchase. Revenue kept flowing.

But here's the thing - it's not all sunshine. The **operational overhead** is real. You need solid DevOps practices, monitoring, and service mesh. We went from managing 3 deployments to 50+.

My advice? Start with a monolith, then extract services as you identify clear boundaries. Don't go microservices just because it's trendy - do it when you have the problems microservices solve."""


def generate_analysis_response(prompt: Prompt, query: str) -> str:
    """Generate an analytical response."""
    return f"""**Comprehensive Analysis: Microservices Architecture Benefits**

**Executive Summary:**
Microservices architecture provides significant advantages for scalable, maintainable software systems through service decomposition and independence.

**Key Benefits Analysis:**

1. **Scalability & Performance**
   - Horizontal scaling of individual services
   - Resource optimization based on service-specific needs
   - Improved overall system performance

2. **Development Velocity**
   - Parallel development across teams
   - Reduced code conflicts and dependencies
   - Faster feature delivery cycles

3. **Technical Flexibility**
   - Polyglot programming environments
   - Service-specific technology optimization
   - Easier adoption of new technologies

4. **Operational Resilience**
   - Failure isolation and system stability
   - Independent deployment and rollback
   - Reduced blast radius of issues

**Risk Assessment:**
- Medium complexity overhead
- Requires mature DevOps practices
- Initial investment in infrastructure

**Recommendation:**
Adopt microservices for systems with clear service boundaries, multiple development teams, and scaling requirements."""


def generate_direct_response(prompt: Prompt, query: str) -> str:
    """Generate a direct, concise response."""
    return f"""**Main Benefits of Microservices Architecture:**

• **Independent Scaling** - Scale services individually based on demand
• **Technology Choice** - Use different technologies for different services  
• **Fault Isolation** - Service failures don't crash the entire system
• **Team Independence** - Teams can develop and deploy autonomously
• **Faster Deployment** - Deploy changes to individual services quickly

**Key Trade-off:** Increased operational complexity in exchange for flexibility and scalability.

**Best For:** Large applications with multiple teams and varying performance requirements."""


def generate_default_response(prompt: Prompt, query: str) -> str:
    """Generate a default response when prompt type is unclear."""
    return f"""Based on your question about microservices architecture, here are the key benefits:

1. **Scalability**: Services can be scaled independently
2. **Flexibility**: Different technologies can be used for different services
3. **Reliability**: Fault tolerance through service isolation
4. **Development Speed**: Teams can work independently
5. **Maintenance**: Easier to update and maintain individual services

These benefits make microservices particularly valuable for large, complex applications with multiple engineering teams."""
