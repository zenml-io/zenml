#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Comprehensive example demonstrating ZenML's Prompt abstraction for LLMOps workflows.

This example showcases the power of ZenML's Prompt abstraction - a single configurable
class that can handle any prompt use case through configuration rather than inheritance.
"""

from datetime import datetime
from typing import Annotated, Any, Dict, List, Tuple

from zenml import pipeline, step
from zenml.logger import get_logger
from zenml.prompts.prompt import Prompt

logger = get_logger(__name__)


# ========================
# Prompt Creation Steps
# ========================


@step
def create_qa_prompt() -> Annotated[Prompt, "question_answering_prompt"]:
    """Create a sophisticated question-answering prompt with few-shot examples."""
    return Prompt(
        template="""You are an expert {domain} analyst. Answer the following question with detailed analysis.

Context: {context}

Examples:
{examples}

Question: {question}

Provide a comprehensive answer with:
1. Direct answer
2. Supporting evidence
3. Confidence level
4. Sources if applicable

Answer:""",
        prompt_type="user",
        task="question_answering",
        domain="technical",
        prompt_strategy="few_shot",
        variables={
            "domain": "software engineering",
            "context": "Technical documentation and best practices",
        },
        examples=[
            {
                "question": "What are the benefits of microservices architecture?",
                "answer": "Microservices offer scalability, technology diversity, and fault isolation...",
            },
            {
                "question": "How do you implement CI/CD best practices?",
                "answer": "CI/CD best practices include automated testing, deployment pipelines...",
            },
        ],
        instructions="Always provide evidence-based answers with confidence levels",
        model_config_params={
            "temperature": 0.3,
            "max_tokens": 500,
            "top_p": 0.9,
        },
        target_models=["gpt-4", "claude-3"],
        min_tokens=100,
        max_tokens=500,
        expected_format="structured_response",
        version="1.0.0",
        tags=["qa", "technical", "expert"],
        description="Expert Q&A prompt with few-shot examples and structured output",
        created_at=datetime.now(),
    )


@step
def create_summarization_prompt() -> Annotated[Prompt, "summarization_prompt"]:
    """Create a domain-specific summarization prompt."""
    return Prompt(
        template="""Summarize the following {content_type} for a {audience} audience.

Content:
{content}

Requirements:
- Length: {summary_length}
- Focus on: {focus_areas}
- Format: {output_format}

Summary:""",
        prompt_type="user",
        task="summarization",
        domain="business",
        prompt_strategy="direct",
        variables={
            "content_type": "technical document",
            "audience": "executive",
            "summary_length": "3-5 bullet points",
            "focus_areas": "key decisions and impact",
            "output_format": "bullet points",
        },
        instructions="Keep language clear and business-focused",
        model_config_params={"temperature": 0.2, "max_tokens": 300},
        target_models=["gpt-4", "claude-3"],
        expected_format="markdown",
        version="2.1.0",
        tags=["summarization", "business", "executive"],
        description="Executive summarization prompt for technical content",
    )


@step
def create_creative_prompt() -> Annotated[Prompt, "creative_writing_prompt"]:
    """Create a creative writing prompt with chain-of-thought reasoning."""
    return Prompt(
        template="""You are a creative writing assistant. Help create a {content_type} in the {genre} genre.

Theme: {theme}
Setting: {setting}
Mood: {mood}

Let's think step by step:

1. Character Development:
   - Who are the main characters?
   - What are their motivations?

2. Plot Structure:
   - What is the central conflict?
   - How does it resolve?

3. Creative Elements:
   - What makes this story unique?
   - How can we enhance the {mood} mood?

Now, create the {content_type}:""",
        prompt_type="user",
        task="creative_writing",
        domain="creative",
        prompt_strategy="chain_of_thought",
        variables={
            "content_type": "short story",
            "genre": "science fiction",
            "theme": "artificial intelligence",
            "setting": "near future",
            "mood": "thoughtful",
        },
        instructions="Use vivid imagery and focus on character development",
        model_config_params={
            "temperature": 0.8,
            "max_tokens": 1000,
            "top_p": 0.95,
        },
        target_models=["gpt-4", "claude-3"],
        expected_format="narrative",
        version="1.0.0",
        tags=["creative", "writing", "storytelling"],
        description="Chain-of-thought creative writing prompt",
    )


@step
def create_system_prompt() -> Annotated[Prompt, "ai_assistant_system"]:
    """Create a system prompt for an AI assistant."""
    return Prompt(
        template="""You are {assistant_name}, a helpful AI assistant specialized in {specialization}.

Your core principles:
1. {principle_1}
2. {principle_2}  
3. {principle_3}

Communication style: {communication_style}
Expertise level: {expertise_level}
Response format: {response_format}

Remember to always:
- Verify information when possible
- Acknowledge limitations
- Provide helpful follow-up questions
- Maintain {tone} tone""",
        prompt_type="system",
        task="assistant_configuration",
        domain="ai_assistant",
        prompt_strategy="direct",
        variables={
            "assistant_name": "TechExpert",
            "specialization": "software development and architecture",
            "principle_1": "Provide accurate, evidence-based information",
            "principle_2": "Explain complex concepts clearly",
            "principle_3": "Suggest best practices and alternatives",
            "communication_style": "professional yet approachable",
            "expertise_level": "senior developer",
            "response_format": "structured with examples",
            "tone": "helpful and encouraging",
        },
        instructions="This system prompt configures the AI assistant's behavior and expertise",
        version="1.2.0",
        tags=["system", "assistant", "configuration"],
        description="System prompt for technical AI assistant",
    )


# ========================
# Prompt Enhancement Steps
# ========================


@step
def enhance_prompt_with_context(
    base_prompt: Prompt,
    context_data: str = "Additional technical context about microservices and cloud architecture",
) -> Annotated[Prompt, "enhanced_prompt"]:
    """Enhance a prompt with context injection capabilities."""

    # Add context template for dynamic context injection
    enhanced = base_prompt.with_context_template(
        "Context: {context}\n\nAdditional Background: {background}\n\nQuery: {query}"
    )

    # Add performance tracking
    enhanced = enhanced.log_performance(
        {"accuracy": 0.92, "response_time": 1.8, "user_satisfaction": 4.7}
    )

    # Create a variant for A/B testing
    variant = enhanced.create_variant(
        name="Context-Enhanced Variant",
        version="1.1.0",
        metadata={"test_group": "A", "enhancement": "context_injection"},
    )

    logger.info(
        f"Enhanced prompt with context capabilities: {variant.get_summary()}"
    )
    return variant


@step
def create_prompt_variants(
    base_prompt: Prompt,
) -> Annotated[List[Prompt], "prompt_variants"]:
    """Create multiple variants of a prompt for comparison."""

    variants = []

    # Variant 1: More formal tone
    formal_variant = (
        base_prompt.for_domain("academic")
        .with_instructions(
            "Use formal academic language and provide scholarly references"
        )
        .with_model_config(temperature=0.1)
    )
    formal_variant = formal_variant.update_version("1.0.1-formal")
    variants.append(formal_variant)

    # Variant 2: Conversational tone
    casual_variant = (
        base_prompt.for_domain("general")
        .with_instructions(
            "Use conversational language and provide practical examples"
        )
        .with_model_config(temperature=0.7)
    )
    casual_variant = casual_variant.update_version("1.0.1-casual")
    variants.append(casual_variant)

    # Variant 3: Concise responses
    concise_variant = base_prompt.with_model_config(
        max_tokens=200
    ).with_instructions("Provide concise, direct answers with key points only")
    concise_variant = concise_variant.update_version("1.0.1-concise")
    variants.append(concise_variant)

    logger.info(f"Created {len(variants)} prompt variants for comparison")
    return variants


# ========================
# LLM Simulation Steps
# ========================


@step
def simulate_llm_response(
    prompt: Prompt, query: str = "What are the key benefits of microservices?"
) -> str:
    """Simulate an LLM response to demonstrate prompt functionality."""

    # Format the prompt with the query
    try:
        prompt.format(question=query, query=query)

        # Simulate different responses based on prompt configuration
        if prompt.task == "question_answering":
            response = f"""Based on the context and examples provided:

1. **Direct Answer**: Microservices architecture offers several key benefits including scalability, technology diversity, and fault isolation.

2. **Supporting Evidence**: 
   - Independent scaling of services based on demand
   - Ability to use different technologies for different services
   - Failure in one service doesn't cascade to others

3. **Confidence Level**: High (85%) - based on industry best practices and documented case studies

4. **Sources**: Enterprise architecture patterns, cloud-native development guidelines

*[Simulated response based on {prompt.prompt_type} prompt with {prompt.prompt_strategy} strategy]*"""

        elif prompt.task == "summarization":
            response = f"""**Executive Summary:**

• **Scalability**: Services can be scaled independently based on demand
• **Technology Diversity**: Teams can choose optimal tools for each service  
• **Fault Isolation**: System resilience through independent service failures
• **Development Speed**: Parallel development and deployment capabilities
• **Business Impact**: Faster time-to-market and improved system reliability

*[{prompt.variables.get("summary_length", "Standard")} format for {prompt.variables.get("audience", "general")} audience]*"""

        elif prompt.task == "creative_writing":
            response = f"""**Step-by-step Analysis:**

1. **Character Development**: An AI researcher grappling with ethical implications...

2. **Plot Structure**: Central conflict between innovation and responsibility...  

3. **Creative Elements**: Unique perspective on consciousness and humanity...

**The Story:**

In the year 2035, Dr. Sarah Chen stood before her latest creation - an AI that claimed to dream. As she watched the neural patterns flicker across her screen, she wondered: at what point does artificial intelligence become artificial consciousness?

*[Creative response using {prompt.prompt_strategy} approach with {prompt.variables.get("mood", "neutral")} mood]*"""

        else:
            response = f"Response generated using {prompt.prompt_type} prompt for {prompt.task} task"

        return response

    except Exception as e:
        return f"Error formatting prompt: {str(e)}"


@step
def evaluate_prompt_performance(
    prompt: Prompt, response: str, query: str
) -> Annotated[Dict[str, float], "evaluation_metrics"]:
    """Evaluate prompt performance with various metrics."""

    # Simulate evaluation metrics based on response characteristics
    metrics = {
        "response_length": len(response),
        "estimated_tokens": len(response.split()),
        "completeness_score": 0.85 if len(response) > 100 else 0.60,
        "relevance_score": 0.90 if prompt.task in response.lower() else 0.70,
        "format_compliance": 1.0
        if prompt.expected_format
        and prompt.expected_format in response.lower()
        else 0.80,
    }

    # Task-specific metrics
    if prompt.task == "question_answering":
        metrics.update(
            {
                "accuracy": 0.88,
                "confidence_provided": 1.0
                if "confidence" in response.lower()
                else 0.0,
                "evidence_provided": 1.0
                if "evidence" in response.lower()
                else 0.0,
            }
        )
    elif prompt.task == "summarization":
        metrics.update(
            {
                "conciseness": 0.92,
                "key_points_covered": 0.95,
                "audience_appropriate": 1.0
                if prompt.variables
                and prompt.variables.get("audience") in response.lower()
                else 0.80,
            }
        )
    elif prompt.task == "creative_writing":
        metrics.update(
            {
                "creativity": 0.87,
                "narrative_structure": 0.90,
                "mood_consistency": 1.0
                if prompt.variables
                and prompt.variables.get("mood") in response.lower()
                else 0.75,
            }
        )

    logger.info(f"Prompt evaluation completed: {metrics}")
    return metrics


# ========================
# Comparison and Analysis Steps
# ========================


@step
def compare_prompt_variants(
    variants: List[Prompt],
    base_query: str = "Explain microservices architecture",
) -> Annotated[Dict[str, Dict], "comparison_results"]:
    """Compare performance across different prompt variants."""

    comparison_results = {}

    for i, variant in enumerate(variants):
        variant_name = f"variant_{i + 1}_{variant.version}"

        # Simulate response for each variant
        response = simulate_llm_response(variant, base_query)
        metrics = evaluate_prompt_performance(variant, response, base_query)

        comparison_results[variant_name] = {
            "prompt_config": {
                "version": variant.version,
                "strategy": variant.prompt_strategy,
                "domain": variant.domain,
                "temperature": variant.model_config_params.get("temperature")
                if variant.model_config_params
                else None,
                "max_tokens": variant.model_config_params.get("max_tokens")
                if variant.model_config_params
                else None,
            },
            "response": response[:200] + "..."
            if len(response) > 200
            else response,
            "metrics": metrics,
            "summary": variant.get_summary(),
        }

    # Find best performing variant
    best_variant = max(
        comparison_results.keys(),
        key=lambda k: comparison_results[k]["metrics"].get(
            "completeness_score", 0
        ),
    )

    comparison_results["best_variant"] = best_variant
    comparison_results["analysis"] = {
        "total_variants": len(variants),
        "best_performing": best_variant,
        "comparison_completed": datetime.now().isoformat(),
    }

    logger.info(f"Prompt comparison completed. Best variant: {best_variant}")
    return comparison_results


@step
def analyze_prompt_lineage(
    prompts: List[Prompt],
) -> Annotated[Dict[str, Any], "lineage_analysis"]:
    """Analyze prompt evolution and lineage."""

    lineage_data = {
        "prompt_count": len(prompts),
        "versions": [p.version for p in prompts if p.version],
        "tasks": list(set([p.task for p in prompts if p.task])),
        "domains": list(set([p.domain for p in prompts if p.domain])),
        "strategies": list(
            set([p.prompt_strategy for p in prompts if p.prompt_strategy])
        ),
        "evolution_timeline": [],
    }

    # Track evolution
    for prompt in sorted(prompts, key=lambda p: p.created_at or datetime.min):
        lineage_data["evolution_timeline"].append(
            {
                "version": prompt.version,
                "task": prompt.task,
                "domain": prompt.domain,
                "created": prompt.created_at.isoformat()
                if prompt.created_at
                else None,
                "parent_id": prompt.parent_prompt_id,
                "summary": prompt.get_summary(),
            }
        )

    logger.info(
        f"Lineage analysis: {lineage_data['prompt_count']} prompts across {len(lineage_data['tasks'])} tasks"
    )
    return lineage_data


# ========================
# External Artifact Integration
# ========================


@step
def process_external_prompt(
    external_prompt: Prompt,
) -> Annotated[Tuple[str, Dict[str, float]], "external_prompt_results"]:
    """Process an external prompt artifact (demonstrates ExternalArtifact usage)."""

    logger.info(f"Processing external prompt: {external_prompt}")
    logger.info(f"Prompt summary: {external_prompt.get_summary()}")

    # Demonstrate dynamic formatting
    sample_query = "How do I implement a robust CI/CD pipeline?"

    try:
        external_prompt.format(
            question=sample_query, query=sample_query, content=sample_query
        )

        # Simulate response
        response = simulate_llm_response(external_prompt, sample_query)

        # Evaluate
        metrics = evaluate_prompt_performance(
            external_prompt, response, sample_query
        )

        logger.info(
            f"External prompt processed successfully with metrics: {metrics}"
        )
        return response, metrics

    except Exception as e:
        logger.warning(f"Error processing external prompt: {e}")
        return f"Error: {str(e)}", {"error": 1.0}


# ========================
# Main Pipeline
# ========================


@pipeline(name="prompt_abstraction_showcase")
def prompt_abstraction_pipeline() -> None:
    """Comprehensive pipeline showcasing ZenML's Prompt abstraction capabilities.

    This pipeline demonstrates:
    - Creating different types of prompts (Q&A, summarization, creative, system)
    - Enhancing prompts with context and performance tracking
    - Creating and comparing prompt variants
    - Analyzing prompt lineage and evolution
    - Processing external prompt artifacts
    - Comprehensive evaluation and comparison
    """

    # Create different types of prompts
    qa_prompt = create_qa_prompt()
    summary_prompt = create_summarization_prompt()
    creative_prompt = create_creative_prompt()
    system_prompt = create_system_prompt()

    # Enhance prompts with additional capabilities
    enhanced_qa = enhance_prompt_with_context(qa_prompt)

    # Create variants for comparison
    qa_variants = create_prompt_variants(qa_prompt)
    summary_variants = create_prompt_variants(summary_prompt)

    # Compare variants
    compare_prompt_variants(qa_variants)
    compare_prompt_variants(summary_variants)

    # Analyze lineage across all prompts
    all_prompts = [
        qa_prompt,
        summary_prompt,
        creative_prompt,
        system_prompt,
        enhanced_qa,
    ]
    analyze_prompt_lineage(all_prompts)

    # Process external prompt (demonstrates ExternalArtifact usage)
    # This can be passed from the CLI or dashboard
    process_external_prompt(qa_prompt)  # Using qa_prompt as example


if __name__ == "__main__":
    """Run the pipeline and demonstrate prompt capabilities."""

    logger.info("🚀 Starting ZenML Prompt Abstraction Showcase")

    # Run the pipeline
    pipeline = prompt_abstraction_pipeline()
    pipeline()

    logger.info("✅ Pipeline completed successfully!")

    # Demonstrate client-side prompt usage
    logger.info("\n📋 Demonstrating Prompt Abstraction Features:")

    # Create a comprehensive prompt
    demo_prompt = Prompt(
        template="Analyze the {analysis_type} for {subject} considering {factors}. Provide {output_format}.",
        prompt_type="user",
        task="analysis",
        domain="business",
        prompt_strategy="systematic",
        variables={
            "analysis_type": "performance metrics",
            "subject": "microservices architecture",
            "factors": "scalability, maintainability, cost",
            "output_format": "structured recommendations",
        },
        examples=[
            {
                "input": "performance analysis of API gateway",
                "output": "Structured performance evaluation with metrics and recommendations",
            }
        ],
        model_config_params={"temperature": 0.3, "max_tokens": 400},
        target_models=["gpt-4"],
        version="1.0.0",
        tags=["analysis", "business", "architecture"],
        description="Business analysis prompt with systematic approach",
    )

    # Demonstrate key features
    print("\n🎯 Prompt Summary:")
    print(f"   {demo_prompt}")

    print("\n📊 Detailed Summary:")
    for key, value in demo_prompt.get_summary().items():
        print(f"   {key}: {value}")

    print("\n✏️ Formatted Prompt:")
    print(f"   {demo_prompt.format()}")

    print("\n🔧 Model Compatibility:")
    print(f"   GPT-4: {demo_prompt.is_compatible_with_model('gpt-4')}")
    print(f"   Claude: {demo_prompt.is_compatible_with_model('claude-3')}")

    print("\n📈 Token Estimation:")
    print(f"   Estimated tokens: {demo_prompt.estimate_tokens()}")

    # Demonstrate variants and evolution
    variant = demo_prompt.for_task("evaluation").with_model_config(
        temperature=0.1
    )
    print("\n🧬 Created Variant:")
    print(f"   Task: {variant.task}")
    print(f"   Temperature: {variant.model_config_params.get('temperature')}")

    logger.info("\n🎉 Prompt Abstraction Demo Complete!")
    logger.info(
        """
    The ZenML Prompt abstraction provides:
    ✅ Single configurable class (no inheritance needed)
    ✅ Rich metadata and tracking capabilities
    ✅ Performance metrics and evaluation
    ✅ Variant creation and A/B testing
    ✅ Lineage tracking and versioning
    ✅ Context injection and formatting
    ✅ Model compatibility checking
    ✅ Seamless ZenML artifact integration
    ✅ Beautiful HTML visualizations
    ✅ ExternalArtifact support for easy pipeline reruns
    """
    )
