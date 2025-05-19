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
#!/usr/bin/env python3

import os
import sys
import yaml
import json
import argparse
from typing import Dict, List, Optional, Any, Tuple


def parse_input_filter(input_str: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse the input string in the format 'pipeline_name:stack::params'.
    
    This function takes a filter string and breaks it down into its components
    to allow filtering of pipeline configurations.
    
    Args:
        input_str: Input string in the format 'pipeline_name:stack::params'.
                   Example: 'my_pipeline:aws::small' or 'my_pipeline:aws' or 'my_pipeline'
        
    Returns:
        Tuple of (pipeline_name, stack, params) where stack and params can be None
        if not specified in the input string.
    """
    if not input_str:
        return None, None, None
    
    parts = input_str.split(':')
    pipeline_name = parts[0] if parts else None
    
    stack = None
    params = None
    
    if len(parts) > 1:
        stack_params = parts[1].split('::')
        if stack_params[0]:
            stack = stack_params[0]
        
        if len(stack_params) > 1 and stack_params[1]:
            params = stack_params[1]
    
    return pipeline_name, stack, params


def load_config_file(file_path: str) -> Dict:
    """Load and parse a YAML configuration file.
    
    Args:
        file_path: Path to the configuration file
        
    Returns:
        Dictionary containing the parsed configuration
        
    Raises:
        SystemExit: If the file doesn't exist or can't be parsed
    """
    if not os.path.exists(file_path):
        print(f"Error: Configuration file '{file_path}' not found")
        sys.exit(1)
    
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        sys.exit(1)


def format_params_as_cli_args(params: Dict) -> str:
    """Format parameters dictionary as command-line arguments.
    
    Converts a dictionary of parameters into a string of CLI arguments
    in the format '--key value'.
    
    Args:
        params: Dictionary of parameters (key-value pairs)
        
    Returns:
        String of command-line arguments formatted as '--key value'
    """
    if not params:
        return ""
    
    return " ".join([f"--{key} {value}" for key, value in params.items()])


def generate_configurations(config: Dict, pipeline_filter: Optional[str] = None, 
                           stack_filter: Optional[str] = None, 
                           params_filter: Optional[str] = None) -> List[Dict]:
    """Generate all possible configuration combinations based on input filters.
    
    For each pipeline in the configuration, this function generates all valid
    combinations of stack and parameter sets, applying any filters provided.
    
    Args:
        config: Configuration dictionary from the YAML file
        pipeline_filter: Optional pipeline name to filter by
        stack_filter: Optional stack name to filter by
        params_filter: Optional parameter set name to filter by
        
    Returns:
        List of configuration dictionaries with pipeline_name, stack, command,
        and formatted parameters
    """
    results = []
    
    for pipeline_name, pipeline_config in config.items():
        # Skip if pipeline filter is specified and doesn't match
        if pipeline_filter and pipeline_name != pipeline_filter:
            continue
        
        command = pipeline_config.get("command", None)
        
        # Handle different parameter structures
        params_dict = pipeline_config.get("params", {})
        
        # If params is a direct dictionary, treat it as having a single default params
        if params_dict and not any(isinstance(v, dict) for v in params_dict.values()):
            param_sets = {"default": params_dict}
        else:
            param_sets = params_dict or {"default": {}}
        
        # Get stack information - can be a dictionary with requirements as values
        stacks_config = pipeline_config.get("stacks", {"default": None})
        
        # If stacks is a list, convert to a dict with None values
        if isinstance(stacks_config, list):
            stacks_config = {stack: None for stack in stacks_config}
        
        for stack_name, requirements in stacks_config.items():
            # Skip if stack filter is specified and doesn't match
            if stack_filter and stack_name != stack_filter:
                continue
            
            for param_name, param_values in param_sets.items():
                # Skip if params filter is specified and doesn't match
                if params_filter and param_name != params_filter:
                    continue
                
                config_entry = {
                    "pipeline_name": pipeline_name,
                    "stack": stack_name,
                }
                
                if command:
                    config_entry["command"] = command
                
                if requirements:
                    config_entry["requirements"] = requirements
                
                if param_values:
                    # Format parameters as CLI arguments
                    config_entry["params"] = format_params_as_cli_args(param_values)
                
                results.append(config_entry)
    
    return results


def main():
    """Main entry point for the script.
    
    Parses command line arguments, loads the configuration file,
    generates pipeline configurations, and outputs a GitHub Actions
    strategy matrix.
    """
    parser = argparse.ArgumentParser(
        description="Generate GitHub Actions strategy matrix from pipeline configurations"
    )
    parser.add_argument(
        "--config", 
        default="dev/dev_pipelines_config.yaml", 
        help="Path to the configuration file"
    )
    parser.add_argument(
        "--input", 
        help="Filter in format pipeline_name:stack::params"
    )
    
    args = parser.parse_args()
    
    # Parse input filter
    pipeline_filter, stack_filter, params_filter = parse_input_filter(args.input)
    
    # Load configuration
    config = load_config_file(args.config)
    
    # Generate configurations
    configurations = generate_configurations(
        config, 
        pipeline_filter=pipeline_filter,
        stack_filter=stack_filter,
        params_filter=params_filter
    )
    
    # Output GitHub Actions matrix
    if not configurations:
        print("No matching configurations found.")
    else:
        # Format for GitHub Actions matrix strategy as JSON
        matrix = {"include": configurations}
        print(json.dumps(matrix))


if __name__ == "__main__":
    main() 