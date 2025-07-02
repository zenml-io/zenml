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
"""Utility functions for prompt operations."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from zenml.prompts.prompt import Prompt
from zenml.prompts.prompt_comparison import PromptComparison, compare_prompts


def create_prompt_variant(
    base_prompt: Prompt,
    variant_name: str,
    **changes: Any
) -> Prompt:
    """Create a variant of a prompt with specified changes.
    
    Args:
        base_prompt: The base prompt to create a variant from
        variant_name: Name/description for the variant
        **changes: Fields to change in the variant
        
    Returns:
        New Prompt instance as a variant
    """
    return base_prompt.create_variant(name=variant_name, **changes)


def load_prompt_from_file(file_path: str) -> Prompt:
    """Load a prompt from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loaded Prompt instance
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Prompt.from_dict(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in {file_path}: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load prompt from {file_path}: {e}")


def save_prompt_to_file(prompt: Prompt, file_path: str, indent: int = 2) -> None:
    """Save a prompt to a JSON file.
    
    Args:
        prompt: Prompt to save
        file_path: Path where to save the file
        indent: JSON indentation level
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(prompt.to_dict(), f, indent=indent, default=str)


def load_prompts_from_directory(directory_path: str) -> List[Prompt]:
    """Load all prompts from JSON files in a directory.
    
    Args:
        directory_path: Path to directory containing prompt files
        
    Returns:
        List of loaded Prompt instances
    """
    prompts = []
    directory = Path(directory_path)
    
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    for file_path in directory.glob("*.json"):
        try:
            prompt = load_prompt_from_file(str(file_path))
            prompts.append(prompt)
        except Exception as e:
            print(f"Warning: Failed to load prompt from {file_path}: {e}")
    
    return prompts


def save_prompts_to_directory(
    prompts: List[Prompt], 
    directory_path: str,
    filename_template: str = "{prompt_id}.json"
) -> None:
    """Save multiple prompts to JSON files in a directory.
    
    Args:
        prompts: List of prompts to save
        directory_path: Directory where to save the files
        filename_template: Template for generating filenames
    """
    directory = Path(directory_path)
    directory.mkdir(parents=True, exist_ok=True)
    
    for prompt in prompts:
        # Generate filename
        filename = filename_template.format(
            prompt_id=prompt.prompt_id,
            task=prompt.task or "unknown",
            domain=prompt.domain or "unknown",
            version=prompt.version or "unknown",
            description=prompt.description or "prompt"
        )
        
        # Clean filename
        filename = "".join(c for c in filename if c.isalnum() or c in '._-')
        if not filename.endswith('.json'):
            filename += '.json'
        
        file_path = directory / filename
        save_prompt_to_file(prompt, str(file_path))


def compare_prompts(prompt1: Prompt, prompt2: Prompt) -> PromptComparison:
    """Compare two prompts and return detailed comparison.
    
    Args:
        prompt1: First prompt to compare
        prompt2: Second prompt to compare
        
    Returns:
        PromptComparison object with detailed analysis
    """
    from zenml.prompts.prompt_comparison import compare_prompts as _compare_prompts
    return _compare_prompts(prompt1, prompt2)


def find_best_prompt(
    prompts: List[Prompt], 
    metric: str = "accuracy",
    prefer_recent: bool = True
) -> Optional[Prompt]:
    """Find the best performing prompt from a list.
    
    Args:
        prompts: List of prompts to evaluate
        metric: Performance metric to use for comparison
        prefer_recent: Whether to prefer more recent prompts in case of ties
        
    Returns:
        Best performing prompt or None if no prompts have the metric
    """
    if not prompts:
        return None
    
    # Filter prompts that have the specified metric
    candidates = [
        p for p in prompts 
        if p.performance_metrics and metric in p.performance_metrics
    ]
    
    if not candidates:
        return None
    
    # Sort by metric (descending) and optionally by creation date
    def sort_key(prompt: Prompt) -> Tuple[float, datetime]:
        performance = prompt.performance_metrics[metric]
        created_at = prompt.created_at or datetime.min
        return (performance, created_at if prefer_recent else datetime.min)
    
    return max(candidates, key=sort_key)


def merge_prompt_variables(
    base_variables: Optional[Dict[str, Any]], 
    override_variables: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Merge prompt variables with override precedence.
    
    Args:
        base_variables: Base variable values
        override_variables: Override variable values
        
    Returns:
        Merged variables dictionary
    """
    merged = {}
    
    if base_variables:
        merged.update(base_variables)
    
    if override_variables:
        merged.update(override_variables)
    
    return merged


def validate_prompt_template(template: str) -> Tuple[bool, List[str]]:
    """Validate a prompt template for common issues.
    
    Args:
        template: Template string to validate
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check for empty template
    if not template.strip():
        issues.append("Template is empty")
        return False, issues
    
    # Check for unmatched braces
    open_braces = template.count('{')
    close_braces = template.count('}')
    
    if open_braces != close_braces:
        issues.append(f"Unmatched braces: {open_braces} opening, {close_braces} closing")
    
    # Check for nested braces
    import re
    nested_pattern = r'\{[^}]*\{[^}]*\}[^}]*\}'
    if re.search(nested_pattern, template):
        issues.append("Template contains nested braces")
    
    # Check for common formatting issues
    if template.count('{{') > template.count('{') - template.count('{{'):
        issues.append("Template may contain escaped braces that won't be replaced")
    
    # Check for potentially problematic variables
    variable_pattern = r'\{([^}]+)\}'
    variables = re.findall(variable_pattern, template)
    
    for var in variables:
        if not var.strip():
            issues.append("Template contains empty variable placeholder")
        elif not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var.strip()):
            issues.append(f"Variable '{var}' contains invalid characters")
    
    return len(issues) == 0, issues


def extract_template_variables(template: str) -> List[str]:
    """Extract all variable names from a template.
    
    Args:
        template: Template string
        
    Returns:
        List of unique variable names
    """
    import re
    pattern = r'\{([^}]+)\}'
    variables = re.findall(pattern, template)
    return list(set(var.strip() for var in variables))


def format_prompt_safely(
    template: str, 
    variables: Optional[Dict[str, Any]] = None,
    missing_value: str = "[MISSING]"
) -> str:
    """Format a prompt template safely, handling missing variables.
    
    Args:
        template: Template string to format
        variables: Variables to substitute
        missing_value: Value to use for missing variables
        
    Returns:
        Formatted template string
    """
    if not variables:
        variables = {}
    
    # Extract all variables from template
    template_vars = extract_template_variables(template)
    
    # Create safe variables dict with defaults for missing vars
    safe_vars = {}
    for var in template_vars:
        safe_vars[var] = variables.get(var, missing_value)
    
    try:
        return template.format(**safe_vars)
    except Exception as e:
        return f"[FORMATTING ERROR: {e}]"


def create_prompt_from_template(
    template: str,
    prompt_type: str = "user",
    task: Optional[str] = None,
    domain: Optional[str] = None,
    **kwargs: Any
) -> Prompt:
    """Create a prompt from a template string with minimal configuration.
    
    Args:
        template: Template string
        prompt_type: Type of prompt
        task: Task for the prompt
        domain: Domain for the prompt
        **kwargs: Additional prompt configuration
        
    Returns:
        Configured Prompt instance
    """
    return Prompt(
        template=template,
        prompt_type=prompt_type,
        task=task,
        domain=domain,
        created_at=datetime.now(),
        **kwargs
    )


def generate_prompt_report(prompts: List[Prompt]) -> str:
    """Generate a comprehensive report for a list of prompts.
    
    Args:
        prompts: List of prompts to analyze
        
    Returns:
        Formatted report string
    """
    if not prompts:
        return "No prompts to analyze."
    
    report = []
    
    # Header
    report.append("# Prompt Collection Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Total Prompts: {len(prompts)}")
    report.append("")
    
    # Summary statistics
    tasks = [p.task for p in prompts if p.task]
    domains = [p.domain for p in prompts if p.domain]
    prompt_types = [p.prompt_type for p in prompts if p.prompt_type]
    
    report.append("## Summary")
    report.append(f"- Unique Tasks: {len(set(tasks))} ({', '.join(set(tasks))})")
    report.append(f"- Unique Domains: {len(set(domains))} ({', '.join(set(domains))})")
    report.append(f"- Prompt Types: {len(set(prompt_types))} ({', '.join(set(prompt_types))})")
    report.append("")
    
    # Complexity analysis
    complexities = [p.get_complexity_score() for p in prompts]
    avg_complexity = sum(complexities) / len(complexities)
    
    report.append("## Complexity Analysis")
    report.append(f"- Average Complexity: {avg_complexity:.2f}")
    report.append(f"- Most Complex: {max(complexities):.2f}")
    report.append(f"- Least Complex: {min(complexities):.2f}")
    report.append("")
    
    # Template statistics
    template_lengths = [len(p.template) for p in prompts]
    avg_length = sum(template_lengths) / len(template_lengths)
    
    report.append("## Template Statistics")
    report.append(f"- Average Length: {avg_length:.0f} characters")
    report.append(f"- Longest Template: {max(template_lengths)} characters")
    report.append(f"- Shortest Template: {min(template_lengths)} characters")
    report.append("")
    
    # Variable analysis
    all_variables = []
    for prompt in prompts:
        if prompt.variables:
            all_variables.extend(prompt.variables.keys())
    
    if all_variables:
        from collections import Counter
        var_counts = Counter(all_variables)
        most_common = var_counts.most_common(5)
        
        report.append("## Most Common Variables")
        for var, count in most_common:
            report.append(f"- {var}: {count} prompts")
        report.append("")
    
    # Performance analysis (if available)
    prompts_with_performance = [p for p in prompts if p.performance_metrics]
    
    if prompts_with_performance:
        report.append("## Performance Summary")
        report.append(f"- Prompts with Performance Data: {len(prompts_with_performance)}")
        
        # Collect all metrics
        all_metrics = set()
        for prompt in prompts_with_performance:
            all_metrics.update(prompt.performance_metrics.keys())
        
        for metric in sorted(all_metrics):
            values = [
                p.performance_metrics[metric] 
                for p in prompts_with_performance 
                if metric in p.performance_metrics
            ]
            if values:
                avg_val = sum(values) / len(values)
                report.append(f"- Average {metric}: {avg_val:.3f}")
        
        report.append("")
    
    # Individual prompt details
    report.append("## Individual Prompts")
    
    for i, prompt in enumerate(prompts, 1):
        report.append(f"### {i}. {prompt.description or f'Prompt {prompt.prompt_id[:8]}...'}")
        report.append(f"- ID: {prompt.prompt_id}")
        report.append(f"- Type: {prompt.prompt_type}")
        report.append(f"- Task: {prompt.task or 'Not specified'}")
        report.append(f"- Domain: {prompt.domain or 'Not specified'}")
        report.append(f"- Complexity: {prompt.get_complexity_score():.2f}")
        report.append(f"- Template Length: {len(prompt.template)} characters")
        
        if prompt.variables:
            report.append(f"- Variables: {', '.join(prompt.variables.keys())}")
        
        if prompt.performance_metrics:
            metrics_str = ', '.join(f"{k}={v:.3f}" for k, v in prompt.performance_metrics.items())
            report.append(f"- Performance: {metrics_str}")
        
        report.append("")
    
    return "\n".join(report)


def create_prompt_library_from_examples() -> List[Prompt]:
    """Create a library of example prompts for common use cases.
    
    Returns:
        List of example Prompt instances
    """
    examples = [
        # Question Answering
        Prompt(
            template="Answer the following question clearly and concisely:\n\nQuestion: {question}\n\nAnswer:",
            prompt_type="user",
            task="question_answering",
            domain="general",
            description="Basic question answering prompt",
            version="1.0.0",
            tags=["qa", "basic"],
            model_config_params={"temperature": 0.3, "max_tokens": 200}
        ),
        
        # Summarization
        Prompt(
            template="Summarize the following text in {num_sentences} sentences:\n\n{text}\n\nSummary:",
            prompt_type="user",
            task="summarization",
            domain="general",
            description="Text summarization prompt",
            version="1.0.0",
            tags=["summarization", "text"],
            variables={"num_sentences": "3"},
            model_config_params={"temperature": 0.2, "max_tokens": 150}
        ),
        
        # Code Generation
        Prompt(
            template="Write a {language} function that {description}:\n\n```{language}\n{function_signature}\n# Your code here\n```",
            prompt_type="user",
            task="code_generation",
            domain="programming",
            description="Code generation prompt",
            version="1.0.0",
            tags=["coding", "generation"],
            variables={"language": "python"},
            model_config_params={"temperature": 0.1, "max_tokens": 300}
        ),
        
        # Creative Writing
        Prompt(
            template="Write a {genre} story about {topic}. The story should be {tone} and approximately {length} words.\n\nStory:",
            prompt_type="user",
            task="creative_writing",
            domain="creative",
            description="Creative writing prompt",
            version="1.0.0",
            tags=["creative", "story", "writing"],
            variables={"genre": "short", "tone": "mysterious", "length": "500"},
            model_config_params={"temperature": 0.8, "max_tokens": 600}
        ),
        
        # Classification
        Prompt(
            template="Classify the following text into one of these categories: {categories}\n\nText: {text}\n\nCategory:",
            prompt_type="user",
            task="classification",
            domain="general",
            description="Text classification prompt",
            version="1.0.0",
            tags=["classification", "categorization"],
            model_config_params={"temperature": 0.1, "max_tokens": 50}
        ),
    ]
    
    # Set creation timestamps
    for prompt in examples:
        prompt.created_at = datetime.now()
    
    return examples