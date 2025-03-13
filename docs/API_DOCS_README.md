# ZenML API Documentation Generator

This directory contains tools to generate GitBook-compatible API documentation from ZenML's codebase using pydoc-markdown.

## Prerequisites

Install the required dependencies:

```bash
pip install -r docs/api_docs_requirements.txt
```

Or install pydoc-markdown directly:

```bash
pip install pydoc-markdown
```

## Configuration Files

- `pydoc-markdown.yml` - Configuration for pydoc-markdown that controls how docstrings are processed and Markdown is generated
- `generate_api_docs.py` - Python script that runs pydoc-markdown and integrates the output with GitBook
- `api_docs_requirements.txt` - Required Python packages for the documentation generator

## How to Generate API Documentation

1. Run the generation script:

```bash
# From the repository root
python docs/generate_api_docs.py
```

2. The script will:
   - Run pydoc-markdown to generate Markdown files from your Python docstrings
   - Apply GitBook-specific formatting to the generated files
   - Copy the files to the GitBook directory structure at `docs/book/reference/api/`
   - Update the GitBook `toc.md` file with links to the API reference

## Customization

### Adding More Modules

To document additional modules:

1. Edit `pydoc-markdown.yml` and add your modules to the `modules` list:

```yaml
loaders:
  - type: python
    search_path: ["../src"]
    modules: 
      - "zenml"
      - "zenml.cli"
      - "zenml.client"
      - "zenml.pipelines"
      # Add your module here
```

### Changing Output Format

The Markdown format can be customized by editing the `renderer` section in `pydoc-markdown.yml`.

### GitBook Integration

If your GitBook structure is different from the default, modify these variables in `generate_api_docs.py`:

```python
GITBOOK_SUMMARY_FILE = "toc.md"  # The name of your GitBook table of contents file
GITBOOK_TARGET_DIR = "book/reference/api"  # Where to put the API docs
```

## Cross-References

The generated documentation includes cross-references between API components. In GitBook, these will appear as clickable links to other parts of the API documentation.

## Local Development

When writing docstrings, you can run this tool locally to preview how your documentation will appear in GitBook:

```bash
python docs/generate_api_docs.py
```

## Troubleshooting

- **Missing documentation**: Make sure your module is listed in the `modules` section of `pydoc-markdown.yml`
- **Broken formatting**: Check that your docstrings follow the Google style
- **Cross-reference issues**: Ensure class/function references use fully-qualified names
- **pydoc-markdown errors**: If you see errors when running pydoc-markdown, try running it directly with `pydoc-markdown docs/pydoc-markdown.yml` to see more detailed error messages

### Common Errors and Solutions

1. **Unknown configuration options**: With pydoc-markdown 4.8.2, you may see warnings about unknown configuration options like `output`. This is fixed by:
   - Removing the `output` section from the configuration
   - Using the `--build` and `--site-dir` command-line options instead

2. **ImportError for modules**: If you see errors like `ImportError: zenml.cli`, it's likely that the Python path isn't set correctly. The script now sets PYTHONPATH to include the src directory.

3. **No documentation generated**: Make sure your docstrings are in Google format and that the modules you're trying to document are properly imported in your code.

4. **Markdown file path issues**: If links in the generated TOC are incorrect, check the path generation in the `generate_gitbook_summary` function. 