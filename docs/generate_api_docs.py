#!/usr/bin/env python
"""Script to generate GitBook-compatible API documentation using pydoc-markdown."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Configuration
GITBOOK_SUMMARY_FILE = "toc.md"  # GitBook table of contents file
API_DOCS_DIR = "gitbook-api-docs"
GITBOOK_TARGET_DIR = "book/reference/api"  # Adjust to match your GitBook structure

def run_pydoc_markdown():
    """Run pydoc-markdown to generate the API documentation."""
    print("Generating API documentation with pydoc-markdown...")
    
    # Set PYTHONPATH to include the src directory
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{os.path.abspath('src')}:{env.get('PYTHONPATH', '')}"
    
    # Create output directory if it doesn't exist
    output_dir = Path("docs") / API_DOCS_DIR
    os.makedirs(output_dir, exist_ok=True)
    
    # Run pydoc-markdown and capture output
    result = subprocess.run(
        ["pydoc-markdown", "pydoc-markdown.yml"], 
        cwd="docs",
        capture_output=True,
        text=True,
        env=env
    )
    
    if result.returncode != 0:
        print(f"Error running pydoc-markdown: {result.stderr}")
        if result.stdout:
            print(f"\nAdditional information:\n{result.stdout}")
        sys.exit(1)
    
    # Check if we got output (stdout should contain the Markdown)
    if result.stdout:
        print("Processing output from pydoc-markdown...")
        
        # Save the complete output for debugging
        debug_file = output_dir / "complete_output.md"
        with open(debug_file, 'w') as f:
            f.write(result.stdout)
        print(f"Saved complete output to {debug_file} for reference")
        
        # Extract and save modules
        extract_and_save_modules(result.stdout, output_dir)
    else:
        print("No output generated from pydoc-markdown.")
        sys.exit(1)
    
    print("API documentation generated successfully.")

def extract_and_save_modules(output, output_dir):
    """Extract module content from pydoc-markdown output and save to files.
    
    Args:
        output: The stdout output from pydoc-markdown
        output_dir: Directory to save the parsed files
    """
    # Clear existing markdown files in the output directory
    for file in output_dir.glob("**/*.md"):
        if file.name != "complete_output.md":  # Keep the debug file
            file.unlink()
    
    # Split output by module sections
    # We look for level 1 headers (# Module) which indicate the start of a new module
    module_sections = []
    current_section = []
    lines = output.split('\n')
    
    for i, line in enumerate(lines):
        # Check if line starts with a level 1 header (# Module)
        if line.startswith('# ') and (i == 0 or not lines[i-1].startswith('#')):
            if current_section:
                module_sections.append(current_section)
                current_section = []
            current_section = [line]
        elif current_section:
            current_section.append(line)
    
    # Add the last section
    if current_section:
        module_sections.append(current_section)
    
    # Process each module section
    for section in module_sections:
        if not section:
            continue
            
        # Extract module name from the header
        header = section[0]
        module_name = header[2:].strip()  # Remove '# ' prefix
        
        # Handle submodules by looking for the full module path
        # For example, "zenml.cli" instead of just "cli"
        for i, line in enumerate(section):
            if line.startswith('Module **'):
                # Extract the full module path, e.g., "Module **zenml.cli**"
                match = re.search(r'Module \*\*([a-zA-Z0-9_.]+)\*\*', line)
                if match:
                    module_name = match.group(1)
                break
        
        # Generate file path
        file_path = output_dir / f"{module_name.replace('.', '/')}.md"
        os.makedirs(file_path.parent, exist_ok=True)
        
        # Save the content
        with open(file_path, 'w') as f:
            f.write('\n'.join(section))
        
        print(f"Saved documentation for module {module_name}")
    
    print(f"Extracted and saved {len(module_sections)} module sections")

def post_process_files():
    """Perform post-processing on the generated Markdown files."""
    docs_dir = Path("docs") / API_DOCS_DIR
    
    if not docs_dir.exists():
        print(f"Warning: Generated docs directory not found at {docs_dir}")
        print("Make sure pydoc-markdown completed successfully.")
        return
    
    print(f"Post-processing Markdown files in {docs_dir}...")
    for md_file in docs_dir.glob("**/*.md"):
        content = md_file.read_text()
        
        # Add GitBook page metadata (if needed)
        if not content.startswith("---"):
            title = md_file.stem.replace("_", " ").title()
            metadata = f"""---
description: API documentation for {title}
---

"""
            content = metadata + content
        
        # Update internal links to use GitBook format
        # This is a simplified example - you might need more complex link processing
        
        # Write the modified content back
        md_file.write_text(content)
    
    print("Post-processing complete.")

def copy_to_gitbook():
    """Copy the generated Markdown files to the GitBook directory."""
    source_dir = Path("docs") / API_DOCS_DIR
    target_dir = Path("docs") / GITBOOK_TARGET_DIR
    
    print(f"Copying API docs to GitBook directory: {target_dir}")
    
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Clear existing API docs
    for item in target_dir.glob("*"):
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    
    # Copy new API docs
    for item in source_dir.glob("**/*"):
        relative_path = item.relative_to(source_dir)
        destination = target_dir / relative_path
        
        if item.is_file():
            os.makedirs(destination.parent, exist_ok=True)
            shutil.copy2(item, destination)
        elif item.is_dir():
            os.makedirs(destination, exist_ok=True)
    
    print("Files copied successfully.")

def generate_gitbook_summary():
    """Update the GitBook TOC file to include the API reference."""
    api_dir = Path("docs") / GITBOOK_TARGET_DIR
    summary_file = Path("docs/book") / GITBOOK_SUMMARY_FILE
    
    if not summary_file.exists():
        print(f"Warning: GitBook {GITBOOK_SUMMARY_FILE} not found at {summary_file}")
        return
    
    print(f"Updating GitBook {GITBOOK_SUMMARY_FILE}...")
    
    # Read existing summary
    content = summary_file.read_text()
    
    # Check if API Reference section already exists
    api_section = "## API Reference"
    if api_section in content:
        print(f"{api_section} section already exists in {GITBOOK_SUMMARY_FILE}.")
        # In a more advanced version, you could update the existing section
        return
    
    # Generate API reference links
    api_links = ["\n## API Reference\n"]
    
    # Add main modules first
    for module_file in sorted(api_dir.glob("*.md")):
        rel_path = module_file.relative_to(Path("docs/book"))
        name = module_file.stem.replace("_", " ").title()
        api_links.append(f"* [{name}](./{rel_path})")
    
    # Then add subdirectories
    for subdir in sorted(item for item in api_dir.iterdir() if item.is_dir()):
        subdir_name = subdir.name.replace("_", " ").title()
        api_links.append(f"\n### {subdir_name}\n")
        
        for module_file in sorted(subdir.glob("*.md")):
            rel_path = module_file.relative_to(Path("docs/book"))
            name = module_file.stem.replace("_", " ").title()
            api_links.append(f"* [{name}](./{rel_path})")
    
    # Append to the summary file
    with open(summary_file, "a") as f:
        f.write("\n".join(api_links))
    
    print(f"Updated {GITBOOK_SUMMARY_FILE} with API reference links.")

def main():
    """Main function to generate and process API documentation."""
    # Check if pydoc-markdown is installed
    try:
        subprocess.run(["pydoc-markdown", "--version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: pydoc-markdown is not installed. Please install it with:")
        print("pip install pydoc-markdown")
        sys.exit(1)
    
    # Generate the API documentation
    run_pydoc_markdown()
    
    # Post-process the generated files
    post_process_files()
    
    # Copy to GitBook directory
    copy_to_gitbook()
    
    # Update the GitBook summary
    generate_gitbook_summary()
    
    print("API documentation generation complete!")
    print(f"Generated API docs are in: docs/{GITBOOK_TARGET_DIR}")

if __name__ == "__main__":
    main() 