"""Simple Prompt class for document extraction."""

from typing import Any, Dict, List


class Prompt:
    """Simple prompt class for text templating."""
    
    def __init__(self, template: str, variables: List[str]):
        """Initialize prompt with template and expected variables.
        
        Args:
            template: The prompt template string
            variables: List of variable names expected in the template
        """
        self.template = template
        self.variables = {var: var for var in variables}
    
    def format(self, **kwargs: Any) -> str:
        """Format the prompt template with provided variables.
        
        Args:
            **kwargs: Variable values to substitute in template
            
        Returns:
            Formatted prompt string
        """
        return self.template.format(**kwargs)