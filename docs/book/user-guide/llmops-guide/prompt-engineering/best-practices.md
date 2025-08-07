---
description: Learn production-tested best practices for prompt engineering at scale, including structured output, response tracking, and cost optimization.
---

# Best Practices

This page compiles lessons learned from production teams using ZenML's prompt engineering features at scale. These practices cover both simple prompt versioning and advanced LLM capabilities like structured output and response tracking.

## Version Management

### Automatic Versioning with ZenML

ZenML automatically handles prompt versioning through its artifact system. Focus on meaningful changes rather than manual version management:

```python
# ✅ Good: Let ZenML handle versioning automatically
@step
def create_prompt_v1() -> Prompt:
    """Version 1: Basic approach."""
    return Prompt(template="Answer: {question}")

@step  
def create_prompt_v2() -> Prompt:
    """Version 2: Enhanced wording."""
    return Prompt(template="Answer this question: {question}")

@step
def create_prompt_v3() -> Prompt:
    """Version 3: Clear instructions."""
    return Prompt(template="Answer this question clearly: {question}")

# ZenML automatically versions these as artifacts: 1, 2, 3...
```

### Manual Version Tracking (Optional)

For documentation purposes, you can track versions in step names or docstrings:

```python
# ✅ Good: Clear step naming for version tracking
@step
def create_customer_prompt_basic() -> Prompt:
    """Basic customer service prompt - handles simple queries."""
    return Prompt(template="Help with: {query}")

@step
def create_customer_prompt_enhanced() -> Prompt:
    """Enhanced customer service prompt - more empathetic."""
    return Prompt(template="I'm here to help with: {query}")
```

### Git Integration Patterns

Store prompts alongside your code for proper version control:

```python
# prompts/customer_service.py
"""Customer service prompt templates."""

class CustomerServicePrompts:
    """Centralized prompt definitions."""
    
    @staticmethod
    def basic_response() -> Prompt:
        """Standard customer response prompt."""
        return Prompt(
            template="""You are a friendly customer service representative for {company}.

Customer: {customer_message}

Please provide a helpful response that:
- Addresses their specific concern
- Offers concrete next steps
- Maintains a professional but warm tone""",
            variables={"company": "our company"}
        )
    
    @staticmethod
    def escalation_response() -> Prompt:
        """Prompt for escalated customer issues."""
        return Prompt(
            template="""You are a senior customer service specialist handling an escalated issue.

Issue summary: {issue_summary}
Customer history: {customer_history}
Previous attempts: {previous_attempts}

Provide a comprehensive resolution plan that:
- Acknowledges the customer's frustration
- Takes ownership of the issue
- Provides a clear path to resolution
- Includes compensation if appropriate"""
        )
```

## Prompt Comparison Best Practices

### Use Built-in Diff Functionality

ZenML provides GitHub-style diff comparison as core functionality:

```python
# ✅ Good: Use built-in diff methods
@step
def analyze_prompt_changes(old_prompt: Prompt, new_prompt: Prompt) -> dict:
    """Analyze changes between prompt versions."""
    diff_result = old_prompt.diff(new_prompt, "Current", "Proposed")
    
    return {
        "similarity": diff_result['template_diff']['stats']['similarity_ratio'],
        "changes": diff_result['template_diff']['stats']['total_changes'],
        "identical": diff_result['summary']['identical'],
        "recommendation": "deploy" if diff_result['template_diff']['stats']['similarity_ratio'] > 0.8 else "review"
    }

# ❌ Avoid: Custom diff implementations
def custom_diff_logic(prompt1, prompt2):
    # Don't reinvent the wheel - use ZenML's core functionality
    pass
```

### Compare Outputs, Not Just Templates

```python
@step
def compare_prompt_effectiveness(
    prompt1: Prompt, 
    prompt2: Prompt, 
    test_data: list
) -> dict:
    """Compare actual prompt outputs for effectiveness."""
    
    # Generate outputs
    outputs1 = [prompt1.format(**data) for data in test_data]
    outputs2 = [prompt2.format(**data) for data in test_data]
    
    # Use ZenML's output comparison
    from zenml.prompts import compare_text_outputs
    comparison = compare_text_outputs(outputs1, outputs2)
    
    return {
        "avg_similarity": comparison['aggregate_stats']['average_similarity'],
        "changed_outputs": comparison['aggregate_stats']['changed_outputs'],
        "recommendation": "significant_change" if comparison['aggregate_stats']['average_similarity'] < 0.7 else "minor_change"
    }
```

### Change Documentation

Document what changed and why using ZenML's diff functionality:

```python
# ✅ Good: Use diff analysis for change documentation
@step
def document_prompt_changes(old_prompt: Prompt, new_prompt: Prompt) -> dict:
    """Document prompt changes for review."""
    diff_result = old_prompt.diff(new_prompt)
    
    return {
        "change_summary": {
            "similarity": f"{diff_result['template_diff']['stats']['similarity_ratio']:.1%}",
            "lines_added": diff_result['template_diff']['stats']['added_lines'],
            "lines_removed": diff_result['template_diff']['stats']['removed_lines'],
            "variables_changed": diff_result['summary']['variables_changed']
        },
        "unified_diff": diff_result['template_diff']['unified_diff'],
        "change_reason": "Improved clarity and response quality",
        "tested_on": "1000 customer interactions",
        "performance_impact": "15% improvement in satisfaction"
    }
```

Good commit messages with ZenML:

```bash
# ✅ Good commit messages
git commit -m "prompts: improve customer service response clarity

- Added specific instruction for concrete next steps  
- Clarified tone expectations (professional but warm)
- ZenML diff shows 85% similarity with focused improvements
- A/B tested with 1000 interactions, 15% satisfaction increase"

# ❌ Poor commit messages  
git commit -m "update prompt"
git commit -m "prompt v3" 
git commit -m "fix"
```

## Template Design

### Keep Templates Focused

Each prompt should have a single, clear purpose:

```python
# ✅ Good: Focused on one task
email_classification_prompt = Prompt(
    template="Classify this email as: URGENT, NORMAL, or LOW_PRIORITY\n\nEmail: {email_content}",
    version="1.0.0"
)

sentiment_analysis_prompt = Prompt(
    template="Analyze the sentiment of this text as: POSITIVE, NEUTRAL, or NEGATIVE\n\nText: {text}",
    version="1.0.0"
)

# ❌ Avoid: Multiple tasks in one prompt
multi_task_prompt = Prompt(
    template="Classify this email (URGENT/NORMAL/LOW), analyze sentiment (POS/NEU/NEG), and suggest a response: {email}",
    version="1.0.0"
)
```

### Use Clear Variable Names

Make variable names self-documenting:

```python
# ✅ Good: Clear, descriptive variable names
legal_review_prompt = Prompt(
    template="""Review this {document_type} for potential legal issues.

Document content: {document_content}
Jurisdiction: {legal_jurisdiction}
Review focus: {review_focus_areas}

Provide analysis for: {required_analysis_sections}""",
    version="1.0.0"
)

# ❌ Avoid: Cryptic or generic names
bad_prompt = Prompt(
    template="Review {x} for {y} in {z} focusing on {a}",
    version="1.0.0"
)
```

### Provide Sensible Defaults

Set defaults that work for 80% of use cases:

```python
# ✅ Good: Sensible defaults reduce friction
support_prompt = Prompt(
    template="""You are a {role} for {company_name} helping with {issue_type}.

Customer issue: {customer_issue}

Provide a {response_style} response with {detail_level} detail.""",
    version="1.0.0",
    variables={
        "role": "helpful customer support agent",
        "company_name": "our company",
        "issue_type": "general inquiry",
        "response_style": "professional and empathetic",
        "detail_level": "appropriate"
    }
)
```

## Testing Strategies

### Representative Test Cases

Use real user scenarios, not artificial examples:

```python
# ✅ Good: Real customer scenarios
real_test_cases = [
    {
        "inputs": {"customer_issue": "I can't log into my account and I have an important meeting in 30 minutes"},
        "expected_tone": "urgent_helpful",
        "expected_elements": ["immediate assistance", "alternative solutions", "follow-up"]
    },
    {
        "inputs": {"customer_issue": "I love your product but have a small suggestion for improvement"},
        "expected_tone": "appreciative_receptive", 
        "expected_elements": ["thank you", "value feedback", "next steps"]
    }
]

# ❌ Avoid: Artificial test cases
artificial_test_cases = [
    {"inputs": {"customer_issue": "test issue 1"}},
    {"inputs": {"customer_issue": "test issue 2"}}
]
```

### Business-Relevant Metrics

Measure what matters to your business:

```python
def calculate_business_metrics(response: str, customer_context: dict) -> dict:
    """Calculate metrics that matter to the business."""
    return {
        # Customer satisfaction indicators
        "politeness_score": evaluate_politeness(response),
        "empathy_score": evaluate_empathy(response), 
        "helpfulness_score": evaluate_helpfulness(response, customer_context),
        
        # Operational efficiency
        "response_length": len(response.split()),
        "action_items_count": count_action_items(response),
        "escalation_needed": needs_escalation(response),
        
        # Brand consistency
        "tone_alignment": evaluate_brand_tone(response),
        "terminology_consistency": check_brand_terms(response)
    }

# ❌ Avoid: Metrics that don't drive decisions
def poor_metrics(response: str) -> dict:
    return {
        "character_count": len(response),
        "word_count": len(response.split()),
        "sentence_count": response.count('.')
    }
```

### Statistical Rigor

Ensure sufficient sample sizes for reliable decisions:

```python
@step 
def production_ab_test(
    prompt_a: Prompt,
    prompt_b: Prompt,
    min_sample_size: int = 100,
    confidence_level: float = 0.95
) -> dict:
    """Run production A/B test with statistical rigor."""
    
    # Collect sufficient samples
    results_a = collect_samples(prompt_a, min_sample_size)
    results_b = collect_samples(prompt_b, min_sample_size)
    
    # Statistical analysis
    significance_test = perform_statistical_test(
        results_a, results_b, confidence_level
    )
    
    # Business impact analysis
    business_impact = calculate_business_impact(results_a, results_b)
    
    return {
        "statistical_significance": significance_test,
        "business_impact": business_impact,
        "recommendation": make_recommendation(significance_test, business_impact),
        "sample_sizes": {"prompt_a": len(results_a), "prompt_b": len(results_b)}
    }
```

## Production Deployment

### Environment-Specific Prompts

Use different prompts for different environments:

```python
import os

@step
def get_environment_appropriate_prompt() -> Prompt:
    """Get prompt appropriate for current environment."""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return Prompt(
            template="Provide a professional response to: {query}",
            version="2.1.0"  # Stable, well-tested
        )
    elif env == "staging":  
        return Prompt(
            template="Please provide a professional and helpful response to: {query}",
            version="2.2.0-rc1"  # Release candidate
        )
    else:
        return Prompt(
            template="[DEV] Response to: {query}",
            version="2.2.0-dev"  # Development version
        )
```

### Gradual Rollout Strategy

Deploy new prompts incrementally:

```python
@step
def gradual_prompt_rollout(
    current_prompt: Prompt,
    new_prompt: Prompt,
    rollout_config: dict
) -> Prompt:
    """Gradually roll out new prompt based on configuration."""
    
    rollout_percentage = rollout_config.get("percentage", 0.0)
    user_segments = rollout_config.get("segments", [])
    
    # Segment-based rollout
    if user_segments and get_user_segment() in user_segments:
        return new_prompt
    
    # Percentage-based rollout
    if random.random() < rollout_percentage:
        log_metric("prompt_version", new_prompt.version)
        return new_prompt
    else:
        log_metric("prompt_version", current_prompt.version)
        return current_prompt
```

### Monitoring and Alerting

Monitor prompt performance in production:

```python
@step
def monitor_prompt_performance(
    prompt: Prompt,
    response: str,
    user_feedback: dict = None
) -> None:
    """Monitor prompt performance and alert on issues."""
    
    # Performance metrics
    response_time = time.time() - start_time
    response_length = len(response)
    
    # Quality indicators
    quality_score = evaluate_response_quality(response)
    user_satisfaction = user_feedback.get("satisfaction") if user_feedback else None
    
    # Log metrics
    log_metrics({
        "prompt_version": prompt.version,
        "response_time": response_time,
        "response_length": response_length,
        "quality_score": quality_score,
        "user_satisfaction": user_satisfaction
    })
    
    # Alert on issues
    if quality_score < 0.7:
        alert("Low quality response detected", {
            "prompt_version": prompt.version,
            "quality_score": quality_score
        })
    
    if response_time > 5.0:
        alert("Slow response time", {
            "prompt_version": prompt.version,
            "response_time": response_time
        })
```

## Team Collaboration

### Code Review Process

Include prompts in your standard code review process:

```python
# Pull request template should include:
"""
## Prompt Changes

### What changed
- Updated customer service prompt from v2.0.0 to v2.1.0
- Added specific instruction for next steps
- Improved tone consistency

### Testing results
- A/B tested with 500 customer interactions
- 12% improvement in customer satisfaction scores
- No significant change in response time

### Rollout plan
- Deploy to staging first
- Gradual rollout starting at 10%
- Full rollout after 1 week if metrics remain positive

### Rollback plan
- Monitor satisfaction scores hourly
- Automatic rollback if scores drop below 4.2/5
- Manual rollback trigger available
"""
```

### Documentation Standards

Document prompt decisions and rationale:

```python
class DocumentedPrompts:
    """Customer service prompts with full documentation."""
    
    @staticmethod
    def basic_response() -> Prompt:
        """
        Basic customer service response prompt.
        
        Purpose: Generate helpful responses to general customer inquiries
        
        History:
        - v1.0.0: Initial version, basic response structure
        - v1.1.0: Added empathy language, 8% satisfaction improvement
        - v2.0.0: Restructured for clarity, 15% improvement in resolution rate
        - v2.1.0: Added specific next steps instruction, current version
        
        Performance:
        - Average satisfaction: 4.3/5
        - Resolution rate: 85%
        - Average response time: 2.3s
        
        Known issues:
        - Occasionally too verbose for simple questions
        - Consider splitting into basic/detailed variants
        
        Next planned improvements:
        - Add dynamic length adjustment based on question complexity
        - A/B test more conversational tone
        """
        return Prompt(
            template="""You are a friendly customer service representative.

Customer: {customer_message}

Please provide a helpful response that:
- Addresses their specific concern
- Offers concrete next steps  
- Maintains a warm, professional tone""",
            version="2.1.0"
        )
```

### Shared Prompt Libraries

Create reusable prompt libraries for your team:

```python
# shared_prompts/common.py
class CommonPrompts:
    """Shared prompts used across multiple services."""
    
    @staticmethod
    def polite_refusal(version: str = "1.0.0") -> Prompt:
        """Standard polite refusal for requests we can't fulfill."""
        return Prompt(
            template="""I understand you'd like {requested_action}, but I'm not able to {limitation_reason}.

Instead, I can help you with:
- {alternative_1}
- {alternative_2}
- {alternative_3}

Would any of these alternatives work for you?""",
            version=version
        )
    
    @staticmethod
    def information_gathering(version: str = "1.0.0") -> Prompt:
        """Standard prompt for gathering additional information."""
        return Prompt(
            template="""I'd be happy to help you with {request_topic}.

To provide the most accurate assistance, could you please provide:
{required_information}

This will help me give you a more personalized and helpful response.""",
            version=version
        )
```

## Performance Optimization

### Prompt Length Optimization

Balance detail with performance:

```python
# Monitor prompt performance by length
@step
def optimize_prompt_length(prompt: Prompt, performance_data: dict) -> Prompt:
    """Optimize prompt length based on performance data."""
    
    current_length = len(prompt.template)
    avg_response_time = performance_data["avg_response_time"]
    quality_score = performance_data["avg_quality_score"]
    
    # If too slow and quality is good, try shorter version
    if avg_response_time > 3.0 and quality_score > 0.8:
        return create_shorter_version(prompt)
    
    # If fast but poor quality, try more detailed version
    elif avg_response_time < 1.0 and quality_score < 0.7:
        return create_longer_version(prompt)
    
    return prompt  # Current version is optimal
```

### Caching Strategies

Cache formatted prompts for repeated patterns:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_formatted_prompt(template: str, **kwargs) -> str:
    """Cache frequently used prompt formatting."""
    prompt = Prompt(template=template, version="1.0.0")
    return prompt.format(**kwargs)

# Use in high-frequency scenarios
def handle_common_request(request_type: str, user_data: dict) -> str:
    """Handle common requests with cached prompts."""
    if request_type == "greeting":
        return get_cached_formatted_prompt(
            "Hello {name}, welcome to {service}!",
            name=user_data["name"],
            service="our platform"
        )
```

## Common Pitfalls to Avoid

### Over-Engineering

```python
# ❌ Avoid: Complex prompt management systems
class OverEngineeredPromptManager:
    def __init__(self):
        self.prompt_cache = {}
        self.version_tree = {}
        self.approval_workflow = {}
        self.audit_log = {}
    
    def create_prompt_with_approval_workflow(self, template, approvers, metadata):
        # 100+ lines of complexity...
        pass

# ✅ Do: Simple, focused approach
def get_current_prompt() -> Prompt:
    """Get current production prompt."""
    return Prompt(
        template="Answer: {question}",
        version="1.0.0"
    )
```

### Perfectionism Paralysis

```python
# ❌ Avoid: Endless optimization without deployment
def perfect_prompt_development():
    """Don't fall into this trap."""
    while True:
        prompt = create_new_version()
        test_results = extensive_testing(prompt)
        if test_results["perfection_score"] < 100:
            continue  # Never ships!

# ✅ Do: Good enough to ship, then iterate
def iterative_improvement():
    """Ship and improve."""
    prompt = create_good_enough_version()  # 80% quality
    deploy_to_production(prompt)
    
    while True:
        feedback = collect_production_feedback()
        improved_prompt = make_small_improvement(prompt, feedback)
        ab_test_result = test_in_production(prompt, improved_prompt)
        
        if ab_test_result["is_better"]:
            prompt = improved_prompt
            deploy_to_production(prompt)
```

### Ignoring User Feedback

```python
# ✅ Do: Build feedback loops into your prompts
feedback_aware_prompt = Prompt(
    template="""You are a helpful assistant. 

User request: {user_request}

Please provide a helpful response. After your response, ask:
"Was this helpful? How could I improve my response?"

Response:""",
    version="1.0.0"
)
```

## Key Takeaways

1. **Simplicity wins**: Teams using simple Git-based versioning outperform those with complex systems
2. **Test with real data**: Artificial test cases don't predict real performance
3. **Measure business impact**: Focus on metrics that drive business decisions
4. **Deploy incrementally**: Gradual rollouts reduce risk and enable quick recovery
5. **Document decisions**: Future you will thank present you for good documentation
6. **Collaborate actively**: Include prompts in code reviews and team processes
7. **Optimize for iteration speed**: Fast feedback loops beat perfect first attempts

## Production Checklist

Before deploying prompts to production:

- [ ] **Version properly tagged** with semantic versioning
- [ ] **A/B tested** with statistically significant sample size
- [ ] **Business metrics improved** over current version
- [ ] **Error handling** implemented for edge cases
- [ ] **Monitoring and alerting** configured
- [ ] **Rollback plan** documented and tested
- [ ] **Team reviewed** and approved changes
- [ ] **Documentation updated** with rationale and performance data

Following these practices will help you build robust, scalable prompt engineering workflows that deliver real business value while avoiding common pitfalls that derail many LLMOps projects.

## Enhanced Features Best Practices

### Structured Output with Schemas

Use Pydantic schemas for type-safe, validated responses:

```python
from pydantic import BaseModel, Field

# ✅ Good: Well-defined schema with descriptions
class CustomerInsight(BaseModel):
    sentiment: str = Field(..., description="POSITIVE, NEGATIVE, or NEUTRAL")
    confidence: float = Field(..., description="Confidence score 0.0-1.0")
    key_themes: List[str] = Field(..., description="Main topics discussed")
    action_required: bool = Field(..., description="Whether follow-up is needed")

schema_prompt = Prompt(
    template="Analyze this customer feedback: {feedback}",
    output_schema=CustomerInsight.model_json_schema(),
    variables={"feedback": ""}
)

# ❌ Avoid: Overly complex nested schemas
class OverlyComplexSchema(BaseModel):
    level1: Dict[str, Dict[str, List[Dict[str, Optional[Union[str, int, float]]]]]]
```

### Few-Shot Learning Examples

Provide diverse, realistic examples that cover edge cases:

```python
# ✅ Good: Diverse examples covering different scenarios
invoice_prompt = Prompt(
    template="Extract invoice data from: {document_text}",
    output_schema=InvoiceSchema.model_json_schema(),
    examples=[
        {
            "input": {"document_text": "Invoice #INV-001 from ACME Corp for $500"},
            "output": {"number": "INV-001", "amount": 500.0, "vendor": "ACME Corp"}
        },
        {
            "input": {"document_text": "Bill No. B-789 - DataTech Solutions - Total: €1,200"},
            "output": {"number": "B-789", "amount": 1200.0, "vendor": "DataTech Solutions"}
        },
        {
            "input": {"document_text": "Receipt #R-456 missing amount field"},
            "output": {"number": "R-456", "amount": None, "vendor": None}
        }
    ]
)

# ❌ Avoid: Examples too similar to each other or test data
```

### Response Tracking and Cost Management

Monitor LLM performance and costs systematically:

```python
@step
def process_with_tracking(
    documents: List[str],
    prompt: Prompt
) -> List[PromptResponse]:
    """Process documents with comprehensive response tracking."""
    responses = []
    
    for doc in documents:
        response = call_llm_with_prompt(prompt.format(document=doc))
        
        # Create tracked response artifact
        tracked_response = PromptResponse(
            content=response.content,
            parsed_output=parse_structured_output(response.content),
            model_name="gpt-4",
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_cost=calculate_cost(response.usage),
            validation_passed=validate_output(parsed_output),
            created_at=datetime.now(),
            metadata={"document_type": "invoice", "processing_batch": "batch_001"}
        )
        
        responses.append(tracked_response)
    
    return responses
```

### Quality and Validation Patterns

Implement robust validation beyond schema compliance:

```python
def validate_response_quality(response: PromptResponse) -> float:
    """Calculate comprehensive quality score for responses."""
    score = 0.0
    
    # Schema compliance (40% of score)
    if response.validation_passed:
        score += 0.4
    
    # Content quality (30% of score)
    if response.parsed_output and len(str(response.parsed_output)) > 50:
        score += 0.3
    
    # Cost efficiency (20% of score)
    if response.get_cost_per_token() and response.get_cost_per_token() < 0.001:
        score += 0.2
    
    # Speed (10% of score)
    if response.response_time_ms and response.response_time_ms < 5000:
        score += 0.1
    
    return score
```

### Avoiding Data Leakage in Examples

Ensure prompt examples don't over-match your test data:

```python
# ✅ Good: Examples use different patterns than test data
# Test data: "INVOICE #INV-2024-001 from ACME Corporation"
# Examples should use different formats:
examples = [
    {"input": "Bill #B-789 from TechCorp", "output": {"number": "B-789"}},
    {"input": "Receipt R-456 - DataSoft", "output": {"number": "R-456"}},
]

# ❌ Avoid: Examples too similar to test data
bad_examples = [
    {"input": "INVOICE #INV-2024-002 from ACME Corporation", ...}  # Too similar!
]
```

### Performance Monitoring

Set up comprehensive monitoring for production prompts:

```python
@step
def monitor_prompt_performance(responses: List[PromptResponse]) -> Dict[str, float]:
    """Monitor key performance indicators for prompt responses."""
    metrics = {
        "success_rate": sum(r.validation_passed for r in responses) / len(responses),
        "average_quality": sum(r.quality_score or 0 for r in responses) / len(responses),
        "average_cost": sum(r.total_cost or 0 for r in responses) / len(responses),
        "average_response_time": sum(r.response_time_ms or 0 for r in responses) / len(responses),
        "token_efficiency": sum(r.get_token_efficiency() or 0 for r in responses) / len(responses)
    }
    
    # Alert if metrics degrade
    if metrics["success_rate"] < 0.95:
        logger.warning(f"Success rate below threshold: {metrics['success_rate']:.2%}")
    
    return metrics
```

These enhanced features enable production-grade LLM workflows with proper observability, cost control, and quality assurance while maintaining ZenML's philosophy of simplicity and artifact-based management.

## Artifact Tracing and Relationships

A critical aspect of production LLM workflows is **tracing which responses were generated by which prompts**. ZenML provides elegant solutions for this through its built-in artifact lineage system.

### The Hybrid Approach (Recommended)

The most effective strategy combines **ZenML's automatic lineage tracking** (80% of use cases) with **strategic metadata** (20% of use cases) for enhanced querying.

#### Primary: Metadata-Based Linking

The most flexible approach uses explicit metadata linking to trace prompt → response relationships across runs and pipelines:

```python
from zenml import step, pipeline
from zenml.prompts import Prompt, PromptResponse
from zenml.client import Client
import hashlib
import uuid

@step
def create_extraction_prompt() -> Prompt:
    """Create prompt artifact with linkable ID."""
    prompt = Prompt(
        template="Extract invoice data: {document_text}",
        output_schema=InvoiceSchema.model_json_schema(),
        examples=[...]
    )
    
    # Create unique prompt identifier for linking
    prompt_id = str(uuid.uuid4())
    prompt_hash = hashlib.md5(prompt.template.encode()).hexdigest()[:8]
    
    # Store ID in prompt metadata for linking
    prompt.metadata = {
        "prompt_id": prompt_id,
        "prompt_hash": prompt_hash,
        "prompt_name": "invoice_extraction_v2",
        "schema_version": "1.0"
    }
    
    return prompt

@step
def extract_data(
    documents: List[str], 
    prompt: Prompt
) -> List[PromptResponse]:
    """Process documents with explicit metadata linking."""
    responses = []
    
    # Get prompt linking information
    prompt_id = prompt.metadata.get("prompt_id")
    prompt_hash = prompt.metadata.get("prompt_hash")
    prompt_name = prompt.metadata.get("prompt_name")
    
    for doc in documents:
        # LLM processing
        llm_output = call_llm_api(prompt.format(document_text=doc))
        
        # Create response with explicit linking metadata
        response = PromptResponse(
            content=llm_output["content"],
            parsed_output=parse_json(llm_output["content"]),
            model_name="gpt-4",
            total_cost=0.003,
            validation_passed=True,
            metadata={
                # Explicit prompt linking
                "prompt_id": prompt_id,
                "prompt_hash": prompt_hash,
                "prompt_name": prompt_name,
                "prompt_template_preview": prompt.template[:50] + "...",
                
                # Business context
                "document_type": "invoice",
                "processing_batch": f"batch_{uuid.uuid4().hex[:8]}",
                "created_by_step": "extract_data"
            }
        )
        responses.append(response)
    
    return responses

@pipeline
def document_pipeline():
    """Pipeline with metadata-based linking."""
    prompt = create_extraction_prompt()
    documents = ["Invoice text...", "Bill content..."]
    responses = extract_data(documents, prompt)
    return responses
```

#### Querying by Metadata Linkage

```python
from zenml.client import Client

def find_responses_by_prompt_id(prompt_id: str = None, prompt_name: str = None):
    """Find all responses generated by a specific prompt using metadata linking."""
    client = Client()
    
    # Get all PromptResponse artifacts
    all_response_artifacts = client.list_artifacts(
        type_name="PromptResponse",
        size=1000  # Adjust as needed
    )
    
    matching_responses = []
    
    # Filter by prompt metadata
    for artifact in all_response_artifacts:
        response = artifact.load()
        
        # Match by prompt_id or prompt_name
        if prompt_id and response.metadata.get("prompt_id") == prompt_id:
            matching_responses.append({
                "response": response,
                "artifact_id": artifact.id,
                "artifact_name": artifact.name,
                "created": artifact.created
            })
        elif prompt_name and response.metadata.get("prompt_name") == prompt_name:
            matching_responses.append({
                "response": response,
                "artifact_id": artifact.id,
                "artifact_name": artifact.name,
                "created": artifact.created
            })
    
    # Sort by creation time
    matching_responses.sort(key=lambda x: x["created"], reverse=True)
    
    if matching_responses:
        responses = [item["response"] for item in matching_responses]
        
        # Analyze results
        success_rate = sum(r.validation_passed for r in responses) / len(responses)
        total_cost = sum(r.total_cost or 0 for r in responses)
        avg_quality = sum(r.quality_score or 0 for r in responses) / len(responses)
        
        # Get prompt info from first response
        first_response = responses[0]
        prompt_info = {
            "prompt_name": first_response.metadata.get("prompt_name"),
            "prompt_hash": first_response.metadata.get("prompt_hash"),
            "template_preview": first_response.metadata.get("prompt_template_preview")
        }
        
        return {
            "prompt_info": prompt_info,
            "response_count": len(responses),
            "success_rate": success_rate,
            "avg_quality": avg_quality,
            "total_cost": total_cost,
            "responses": responses,
            "time_range": {
                "earliest": matching_responses[-1]["created"],
                "latest": matching_responses[0]["created"]
            }
        }
    else:
        return {"error": f"No responses found for prompt_id={prompt_id}, prompt_name={prompt_name}"}

# Usage examples
analysis_by_name = find_responses_by_prompt_id(prompt_name="invoice_extraction_v2")
if "error" not in analysis_by_name:
    print(f"Found {analysis_by_name['response_count']} responses for {analysis_by_name['prompt_info']['prompt_name']}")
    print(f"Success rate: {analysis_by_name['success_rate']:.1%}")
    print(f"Average quality: {analysis_by_name['avg_quality']:.2f}")
    print(f"Total cost: ${analysis_by_name['total_cost']:.4f}")
```

#### Secondary: Strategic Metadata

Add minimal metadata only for business-specific filtering that ZenML doesn't handle:

```python
@step
def extract_data_with_metadata(
    documents: List[Dict[str, str]], 
    prompt: Prompt
) -> List[PromptResponse]:
    """Enhanced version with strategic metadata."""
    responses = []
    
    for doc in documents:
        llm_output = call_llm_api(prompt.format(document_text=doc["content"]))
        
        response = PromptResponse(
            content=llm_output["content"],
            parsed_output=parse_json(llm_output["content"]),
            model_name="gpt-4",
            total_cost=0.003,
            metadata={
                # ✅ Business context for filtering
                "document_type": doc["type"],  # "invoice", "receipt", "bill"
                "processing_batch": "batch_2024_001",
                "source_system": "accounting_app",
                
                # ❌ Avoid: ZenML already tracks these
                # "prompt_version": "...",  # ZenML handles versioning
                # "step_name": "...",       # ZenML tracks pipeline structure
                # "run_id": "...",          # ZenML provides run context
            }
        )
        responses.append(response)
    
    return responses

# Query by business metadata
def analyze_by_document_type():
    """Analyze performance by document type using metadata."""
    client = Client()
    
    # Get recent runs
    runs = client.list_pipeline_runs(
        pipeline_name="document_pipeline",
        size=10
    )
    
    results_by_type = {}
    
    for run in runs:
        step = run.steps.get("extract_data_with_metadata")
        if step:
            responses = [artifact.load() for artifact in step.outputs["return"]]
            
            # Group by document type using metadata
            for response in responses:
                doc_type = response.metadata.get("document_type", "unknown")
                if doc_type not in results_by_type:
                    results_by_type[doc_type] = []
                results_by_type[doc_type].append(response)
    
    # Analyze each type
    for doc_type, responses in results_by_type.items():
        success_rate = sum(r.validation_passed for r in responses) / len(responses)
        avg_cost = sum(r.total_cost or 0 for r in responses) / len(responses)
        
        print(f"{doc_type}: {success_rate:.1%} success, ${avg_cost:.4f} avg cost")
```

### Dashboard Integration

The ZenML dashboard provides visual artifact lineage without any additional code:

```python
# Get dashboard URL for artifact lineage
client = Client()
run = client.get_pipeline_run("latest")
prompt_artifact = run.steps["create_extraction_prompt"].outputs["return"]

dashboard_url = f"http://localhost:8237/artifacts/{prompt_artifact.id}/lineage"
print(f"View prompt lineage at: {dashboard_url}")
```

In the dashboard:
1. **Navigate to the Artifacts tab**
2. **Click on your Prompt artifact**  
3. **View the "Lineage" tab** - see a visual graph of all PromptResponse artifacts generated
4. **Click through relationships** - explore the complete pipeline flow

### Advanced: Cross-Run Analysis with Metadata

For production monitoring, analyze prompt performance across multiple runs using metadata linkage:

```python
def monitor_prompt_performance_by_metadata(
    prompt_name: str, 
    days: int = 7,
    document_type: str = "invoice"
) -> Dict:
    """Monitor prompt performance across multiple runs using metadata."""
    from datetime import datetime, timedelta
    client = Client()
    
    # Get all PromptResponse artifacts from the last N days
    cutoff_date = datetime.now() - timedelta(days=days)
    
    all_response_artifacts = client.list_artifacts(
        type_name="PromptResponse",
        created=f">{days}d",  # Last N days
        size=10000  # Adjust as needed
    )
    
    # Filter responses by prompt and document type
    matching_responses = []
    
    for artifact in all_response_artifacts:
        response = artifact.load()
        
        # Filter by prompt name and document type
        if (response.metadata.get("prompt_name") == prompt_name and 
            response.metadata.get("document_type") == document_type):
            matching_responses.append({
                "response": response,
                "artifact": artifact,
                "batch_id": response.metadata.get("processing_batch"),
                "created": artifact.created
            })
    
    # Group by processing batch (represents different runs)
    batches = {}
    for item in matching_responses:
        batch_id = item["batch_id"] or "unknown"
        if batch_id not in batches:
            batches[batch_id] = []
        batches[batch_id].append(item)
    
    # Analyze each batch
    performance_data = []
    
    for batch_id, batch_responses in batches.items():
        responses = [item["response"] for item in batch_responses]
        
        # Get prompt characteristics from first response
        first_response = responses[0]
        prompt_hash = first_response.metadata.get("prompt_hash")
        
        # Calculate batch metrics
        batch_metrics = {
            "batch_id": batch_id,
            "batch_date": batch_responses[0]["created"],
            "prompt_hash": prompt_hash,
            "prompt_name": prompt_name,
            "document_type": document_type,
            "response_count": len(responses),
            "success_rate": sum(r.validation_passed for r in responses) / len(responses),
            "avg_quality": sum(r.quality_score or 0 for r in responses) / len(responses),
            "total_cost": sum(r.total_cost or 0 for r in responses),
            "avg_response_time": sum(r.response_time_ms or 0 for r in responses) / len(responses),
            "validation_errors": sum(len(r.validation_errors) for r in responses)
        }
        
        performance_data.append(batch_metrics)
    
    # Sort by date
    performance_data.sort(key=lambda x: x["batch_date"], reverse=True)
    
    # Calculate overall metrics
    all_responses = [item["response"] for item in matching_responses]
    
    if all_responses:
        overall_metrics = {
            "monitoring_period": f"Last {days} days",
            "prompt_name": prompt_name,
            "document_type": document_type,
            "total_batches": len(batches),
            "total_responses": len(all_responses),
            "overall_success_rate": sum(r.validation_passed for r in all_responses) / len(all_responses),
            "overall_avg_quality": sum(r.quality_score or 0 for r in all_responses) / len(all_responses),
            "total_cost": sum(r.total_cost or 0 for r in all_responses),
            "performance_by_batch": performance_data,
            "prompt_versions": len(set(p["prompt_hash"] for p in performance_data if p["prompt_hash"]))
        }
    else:
        overall_metrics = {
            "error": f"No responses found for prompt '{prompt_name}' and document type '{document_type}'"
        }
    
    return overall_metrics

# Usage examples
monitoring = monitor_prompt_performance_by_metadata(
    prompt_name="invoice_extraction_v2",
    days=7,
    document_type="invoice"
)

if "error" not in monitoring:
    print(f"Monitored '{monitoring['prompt_name']}' over {monitoring['monitoring_period']}")
    print(f"Total responses: {monitoring['total_responses']} across {monitoring['total_batches']} batches")
    print(f"Overall success rate: {monitoring['overall_success_rate']:.1%}")
    print(f"Average quality: {monitoring['overall_avg_quality']:.2f}")
    print(f"Total cost: ${monitoring['total_cost']:.2f}")
    print(f"Prompt versions detected: {monitoring['prompt_versions']}")
    
    # Analyze trend over batches
    recent_batches = monitoring['performance_by_batch'][:3]
    if len(recent_batches) >= 2:
        trend = recent_batches[0]['success_rate'] - recent_batches[1]['success_rate']
        print(f"Success rate trend: {trend:+.1%} (latest vs previous)")

# Compare different prompt versions
def compare_prompt_versions(prompt_base_name: str, days: int = 30):
    """Compare performance of different versions of a prompt."""
    client = Client()
    
    # Get all responses for prompts with similar names
    all_responses = client.list_artifacts(
        type_name="PromptResponse", 
        created=f">{days}d",
        size=10000
    )
    
    version_performance = {}
    
    for artifact in all_responses:
        response = artifact.load()
        prompt_name = response.metadata.get("prompt_name", "")
        
        if prompt_base_name in prompt_name:
            if prompt_name not in version_performance:
                version_performance[prompt_name] = []
            version_performance[prompt_name].append(response)
    
    # Compare versions
    comparison = {}
    for version, responses in version_performance.items():
        comparison[version] = {
            "response_count": len(responses),
            "success_rate": sum(r.validation_passed for r in responses) / len(responses),
            "avg_quality": sum(r.quality_score or 0 for r in responses) / len(responses),
            "total_cost": sum(r.total_cost or 0 for r in responses),
            "avg_cost_per_response": sum(r.total_cost or 0 for r in responses) / len(responses)
        }
    
    return comparison
```

### Why This Approach Works Best

1. **Leverages ZenML's Strengths**: Automatic artifact tracking, versioning, and dashboard visualization
2. **Minimal Overhead**: Most relationships tracked automatically without additional code
3. **Business Context**: Strategic metadata for filtering and analysis that ZenML doesn't provide
4. **Scalable**: Fast queries for recent data, efficient for production monitoring
5. **Future-Proof**: Benefits from ZenML improvements and ecosystem development

### When to Use Each Method

| Scenario | Approach | Example |
|----------|----------|---------|
| "What responses did this prompt generate?" | **ZenML Lineage** | `run.steps["step"].outputs["return"]` |
| "Compare prompts across runs" | **ZenML Lineage** | Multi-run analysis with automatic relationships |
| "Filter by document type" | **Strategic Metadata** | `response.metadata["document_type"] == "invoice"` |
| "A/B testing prompt variants" | **Strategic Metadata** | `response.metadata["prompt_variant"] == "A"` |
| "Debug specific pipeline run" | **Dashboard** | Visual lineage exploration |
| "Production monitoring" | **Hybrid** | ZenML lineage + business metadata filtering |

This hybrid approach gives you **90% of the power with 10% of the complexity** - exactly what production teams need for effective LLM workflows.