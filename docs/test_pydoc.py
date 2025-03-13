#!/usr/bin/env python
"""Simple test script to generate documentation for a single module."""

import os
import subprocess
import sys
from pathlib import Path

def create_test_config():
    """Create a simplified test configuration for pydoc-markdown."""
    test_config = """
loaders:
  - type: python
    search_path: ["../src"]
    modules:
      - "zenml.cli"

processors:
  - type: filter
    skip_empty_modules: true
  - type: google

renderer:
  type: markdown
  descriptive_class_title: true
  descriptive_module_title: true

output:
  directory: "./test-docs"
"""
    
    with open("docs/test_config.yml", "w") as f:
        f.write(test_config)
    
    print("Created test configuration file at docs/test_config.yml")

def run_test():
    """Run pydoc-markdown with the test configuration."""
    # Set PYTHONPATH to include the src directory
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{os.path.abspath('src')}:{env.get('PYTHONPATH', '')}"
    
    print("Running pydoc-markdown with test configuration...")
    print(f"PYTHONPATH is set to: {env['PYTHONPATH']}")
    
    # The correct way to run pydoc-markdown with a config file
    result = subprocess.run(
        ["pydoc-markdown", "test_config.yml"], 
        cwd="docs",
        capture_output=True,
        text=True,
        env=env
    )
    
    print("\nSTDOUT:")
    print(result.stdout)
    
    print("\nSTDERR:")
    print(result.stderr)
    
    if result.returncode != 0:
        print(f"Error running pydoc-markdown (exit code {result.returncode})")
        sys.exit(1)
    else:
        print("Test completed successfully!")
        # List generated files
        test_docs_dir = Path("docs/test-docs")
        if test_docs_dir.exists():
            print("\nGenerated test files:")
            for file in test_docs_dir.glob("**/*.md"):
                print(f"  - {file.relative_to(Path('docs'))}")
        else:
            print("No output files found in docs/test-docs")

if __name__ == "__main__":
    create_test_config()
    run_test() 