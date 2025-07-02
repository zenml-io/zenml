"""Steps for creating and managing prompts."""

from datetime import datetime
from typing import Annotated, List

from zenml import step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.logger import get_logger
from zenml.prompts.prompt import Prompt

logger = get_logger(__name__)


@step
def create_basic_prompt() -> Annotated[
    Prompt, ArtifactConfig(name="basic_qa_prompt", tags=["basic", "qa"])
]:
    """Create a basic question-answering prompt."""
    return Prompt(
        template="""You are a helpful AI assistant. Please answer the following question clearly and concisely.

Question: {question}

Answer:""",
        variables={
            "question": "What are the main benefits of using microservices architecture?"
        },
        task="question_answering",
        domain="technology",
        prompt_strategy="direct",
        model_config_params={
            "temperature": 0.3,
            "max_tokens": 300,
        },
        target_models=["gpt-4", "claude-3"],
        description="Basic Q&A prompt for technology questions",
        version="1.0.0",
        tags=["basic", "qa", "technology"],
        created_at=datetime.now(),
    )


@step
def create_prompt_variants(
    num_variants: int = 3,
) -> Annotated[
    List[Prompt],
    ArtifactConfig(name="prompt_variants", tags=["comparison", "variants"]),
]:
    """Create multiple prompt variants for comparison."""

    base_question = (
        "What are the main benefits of using microservices architecture?"
    )

    variants = []

    # Variant 1: Formal academic style
    if num_variants >= 1:
        formal_prompt = Prompt(
            template="""Please provide a comprehensive academic analysis of the following question:

Question: {question}

Your response should include:
1. Definition and context
2. Key benefits with explanations
3. Supporting evidence
4. Potential limitations
5. Conclusion

Analysis:""",
            variables={"question": base_question},
            task="question_answering",
            domain="academic",
            prompt_strategy="structured",
            model_config_params={"temperature": 0.1, "max_tokens": 500},
            description="Formal academic analysis prompt",
            version="1.0.0-formal",
            tags=["formal", "academic", "structured"],
            created_at=datetime.now(),
        )
        variants.append(formal_prompt)

    # Variant 2: Conversational style
    if num_variants >= 2:
        conversational_prompt = Prompt(
            template="""Hey! I'd love to hear your thoughts on this question: {question}

Feel free to share:
- Your main points
- Any examples you can think of
- Why you think this matters

What do you think?""",
            variables={"question": base_question},
            task="conversation",
            domain="general",
            prompt_strategy="conversational",
            model_config_params={"temperature": 0.7, "max_tokens": 300},
            description="Conversational style prompt",
            version="1.0.0-conversational",
            tags=["conversational", "casual", "friendly"],
            created_at=datetime.now(),
        )
        variants.append(conversational_prompt)

    # Variant 3: Bullet point style
    if num_variants >= 3:
        bullet_prompt = Prompt(
            template="""Question: {question}

Please provide a clear, bullet-point answer covering:
• Main benefits (3-5 points)
• Brief explanation for each
• One real-world example

Answer:""",
            variables={"question": base_question},
            task="question_answering",
            domain="business",
            prompt_strategy="structured",
            model_config_params={"temperature": 0.2, "max_tokens": 250},
            description="Bullet-point structured prompt",
            version="1.0.0-bullets",
            tags=["structured", "bullets", "concise"],
            created_at=datetime.now(),
        )
        variants.append(bullet_prompt)

    # Variant 4: Expert interview style
    if num_variants >= 4:
        expert_prompt = Prompt(
            template="""You are interviewing a senior software architect about: {question}

Interviewer: "Could you walk us through your perspective on this?"

Architect: "Absolutely. From my experience with enterprise systems, I can share several key insights:

""",
            variables={"question": base_question},
            task="interview",
            domain="expert",
            prompt_strategy="role_playing",
            model_config_params={"temperature": 0.4, "max_tokens": 400},
            description="Expert interview style prompt",
            version="1.0.0-expert",
            tags=["expert", "interview", "experience"],
            created_at=datetime.now(),
        )
        variants.append(expert_prompt)

    # Variant 5: Pros and cons style
    if num_variants >= 5:
        pros_cons_prompt = Prompt(
            template="""Analyze the following topic: {question}

Please provide a balanced analysis:

PROS:
1. 
2. 
3. 

CONS:
1. 
2. 
3. 

CONCLUSION:
""",
            variables={"question": base_question},
            task="analysis",
            domain="business",
            prompt_strategy="pros_cons",
            model_config_params={"temperature": 0.3, "max_tokens": 350},
            description="Pros and cons analysis prompt",
            version="1.0.0-pros-cons",
            tags=["analysis", "balanced", "pros-cons"],
            created_at=datetime.now(),
        )
        variants.append(pros_cons_prompt)

    logger.info(f"Created {len(variants)} prompt variants for comparison")
    return variants
