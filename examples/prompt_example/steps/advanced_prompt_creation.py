"""
Advanced Prompt Creation Steps

This module demonstrates sophisticated prompt creation capabilities:
- Multi-domain prompt templates
- Rich metadata and versioning
- Variable validation and optimization
- Template inheritance and composition
"""

from typing import Dict, List, Any, Annotated
from zenml import step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def create_customer_service_prompts() -> Annotated[
    List[Dict[str, Any]], 
    ArtifactConfig(name="customer_service_prompts", tags=["customer_service", "support"])
]:
    """Create a set of customer service prompt variants for A/B testing."""
    
    prompts = [
        {
            "id": "cs_basic_v1",
            "name": "Basic Customer Service",
            "template": """You are a customer service representative.

Customer Question: {question}
Context: {context}

Please provide a helpful response.""",
            "variables": {
                "question": "How do I return a damaged product?",
                "context": "Customer received broken item yesterday"
            },
            "metadata": {
                "domain": "customer_service",
                "complexity": "basic",
                "variable_count": 2,
                "template_length": 120,
                "use_case": "general_support",
                "tone": "professional",
                "response_format": "conversational"
            },
            "evaluation_criteria": ["helpfulness", "clarity", "professionalism", "accuracy"],
            "expected_performance": {
                "response_time": "< 2 seconds",
                "customer_satisfaction": "> 4.0/5.0",
                "resolution_rate": "> 80%"
            }
        },
        {
            "id": "cs_enhanced_v2", 
            "name": "Enhanced Customer Service with Context",
            "template": """You are a professional customer service specialist committed to excellent customer experiences.

Customer Information:
- Question: {question}
- Situation: {context}
- Customer Type: {customer_type}
- Previous Interactions: {interaction_history}

Instructions:
1. Show empathy and understanding
2. Provide clear, actionable solutions
3. Offer additional assistance
4. Maintain professional yet warm tone

Response:""",
            "variables": {
                "question": "How do I return a damaged product?",
                "context": "Customer received broken item yesterday",
                "customer_type": "Premium member",
                "interaction_history": "First time contacting support"
            },
            "metadata": {
                "domain": "customer_service", 
                "complexity": "enhanced",
                "variable_count": 4,
                "template_length": 380,
                "use_case": "premium_support",
                "tone": "empathetic_professional",
                "response_format": "structured"
            },
            "evaluation_criteria": ["helpfulness", "empathy", "professionalism", "completeness"],
            "expected_performance": {
                "response_time": "< 3 seconds",
                "customer_satisfaction": "> 4.5/5.0", 
                "resolution_rate": "> 90%"
            }
        },
        {
            "id": "cs_expert_v3",
            "name": "Expert Customer Service with Knowledge Base",
            "template": """You are an expert customer service representative with access to comprehensive product knowledge.

Customer Query Analysis:
- Primary Question: {question}
- Customer Context: {context}
- Product/Service: {product_category}
- Customer Tier: {customer_tier}
- Urgency Level: {urgency}

Knowledge Base Context: {knowledge_base_context}

Response Framework:
1. Acknowledge and validate the customer's concern
2. Provide detailed, step-by-step solution
3. Reference relevant policies or procedures
4. Offer proactive additional assistance
5. Set clear expectations for next steps

Deliver an expert-level response that exceeds customer expectations.""",
            "variables": {
                "question": "How do I return a damaged product?",
                "context": "Customer received broken item yesterday",
                "product_category": "Electronics",
                "customer_tier": "VIP",
                "urgency": "High",
                "knowledge_base_context": "Return policy allows 30-day returns for defective items with expedited processing for VIP customers"
            },
            "metadata": {
                "domain": "customer_service",
                "complexity": "expert",
                "variable_count": 6,
                "template_length": 720,
                "use_case": "expert_support",
                "tone": "expert_professional",
                "response_format": "comprehensive_structured"
            },
            "evaluation_criteria": ["expertise", "completeness", "professionalism", "customer_delight"],
            "expected_performance": {
                "response_time": "< 4 seconds",
                "customer_satisfaction": "> 4.8/5.0",
                "resolution_rate": "> 95%"
            }
        }
    ]
    
    logger.info(f"Created {len(prompts)} customer service prompt variants")
    for prompt in prompts:
        logger.info(f"  • {prompt['name']}: {prompt['metadata']['complexity']} complexity")
    
    return prompts


@step
def create_content_generation_prompts() -> Annotated[
    List[Dict[str, Any]],
    ArtifactConfig(name="content_generation_prompts", tags=["content", "marketing", "creative"])
]:
    """Create content generation prompts for different marketing use cases."""
    
    prompts = [
        {
            "id": "content_blog_v1",
            "name": "Blog Post Generator",
            "template": """Write a blog post about {topic}.

Target Audience: {audience}
Tone: {tone}
Length: {word_count} words

Include:
- Engaging introduction
- Key points and insights
- Call to action

Blog Post:""",
            "variables": {
                "topic": "Machine Learning in Customer Service", 
                "audience": "Business professionals",
                "tone": "Professional yet accessible",
                "word_count": "800"
            },
            "metadata": {
                "domain": "content_generation",
                "content_type": "blog_post",
                "complexity": "intermediate",
                "variable_count": 4,
                "template_length": 180
            },
            "evaluation_criteria": ["creativity", "clarity", "engagement", "seo_optimization"],
            "expected_performance": {
                "engagement_score": "> 7.0/10",
                "readability_score": "> 8.0/10",
                "seo_score": "> 75/100"
            }
        },
        {
            "id": "content_social_v1",
            "name": "Social Media Post Generator",
            "template": """Create an engaging social media post for {platform}.

Campaign: {campaign_name}
Product/Service: {product}
Key Message: {key_message}
Target Audience: {target_audience}
Hashtags: {hashtags}

Requirements:
- Platform-optimized length
- Strong hook in first line
- Clear value proposition
- Appropriate call-to-action
- Engaging visuals suggestion

Social Media Post:""",
            "variables": {
                "platform": "LinkedIn",
                "campaign_name": "AI-Powered Customer Success",
                "product": "ZenML MLOps Platform",
                "key_message": "Streamline your ML operations with production-ready pipelines",
                "target_audience": "ML Engineers and Data Scientists",
                "hashtags": "#MLOps #AI #DataScience #ZenML"
            },
            "metadata": {
                "domain": "content_generation",
                "content_type": "social_media",
                "complexity": "basic",
                "variable_count": 6,
                "template_length": 280
            },
            "evaluation_criteria": ["engagement", "clarity", "brand_alignment", "platform_optimization"],
            "expected_performance": {
                "engagement_rate": "> 3.5%",
                "click_through_rate": "> 2.0%",
                "brand_sentiment": "> 8.0/10"
            }
        }
    ]
    
    logger.info(f"Created {len(prompts)} content generation prompt variants")
    return prompts


@step
def create_code_assistant_prompts() -> Annotated[
    List[Dict[str, Any]],
    ArtifactConfig(name="code_assistant_prompts", tags=["code", "programming", "technical"])
]:
    """Create code assistance prompts for different programming scenarios."""
    
    prompts = [
        {
            "id": "code_debug_v1",
            "name": "Code Debugging Assistant",
            "template": """You are an expert software engineer helping debug code issues.

Code Language: {language}
Problem Description: {problem}
Code Snippet:
```{language}
{code}
```

Error Message (if any): {error_message}
Expected Behavior: {expected_behavior}

Please:
1. Identify the root cause of the issue
2. Explain why it's happening
3. Provide a corrected version of the code
4. Suggest best practices to prevent similar issues

Analysis and Solution:""",
            "variables": {
                "language": "Python",
                "problem": "Function returns None instead of expected value",
                "code": """def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    average = total / len(numbers)
    # Missing return statement""",
                "error_message": "None",
                "expected_behavior": "Should return the average of the input numbers"
            },
            "metadata": {
                "domain": "code_assistance",
                "task_type": "debugging",
                "complexity": "intermediate",
                "variable_count": 5,
                "template_length": 420
            },
            "evaluation_criteria": ["correctness", "clarity", "completeness", "best_practices"],
            "expected_performance": {
                "accuracy": "> 95%",
                "helpfulness": "> 9.0/10",
                "code_quality": "> 8.5/10"
            }
        },
        {
            "id": "code_review_v1",
            "name": "Code Review Assistant",
            "template": """You are conducting a comprehensive code review.

Programming Language: {language}
Code Purpose: {purpose}
Code to Review:
```{language}
{code}
```

Review Focus Areas:
- Code correctness and logic
- Performance optimization
- Security considerations
- Code style and readability
- Best practices adherence

Provide detailed feedback with:
1. Summary assessment
2. Specific issues found (if any)
3. Suggestions for improvement
4. Positive aspects to reinforce
5. Overall recommendation

Code Review:""",
            "variables": {
                "language": "Python",
                "purpose": "Data processing pipeline for ML training",
                "code": """import pandas as pd

def process_data(file_path):
    df = pd.read_csv(file_path)
    df = df.dropna()
    df['new_feature'] = df['feature1'] * df['feature2']
    return df

def train_model(data):
    # Model training logic here
    pass"""
            },
            "metadata": {
                "domain": "code_assistance",
                "task_type": "code_review",
                "complexity": "advanced",
                "variable_count": 3,
                "template_length": 520
            },
            "evaluation_criteria": ["thoroughness", "accuracy", "constructiveness", "expertise"],
            "expected_performance": {
                "review_quality": "> 9.0/10",
                "issue_detection": "> 90%",
                "developer_satisfaction": "> 8.5/10"
            }
        }
    ]
    
    logger.info(f"Created {len(prompts)} code assistance prompt variants")
    return prompts