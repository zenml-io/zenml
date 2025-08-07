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
"""Simple Prompt materializer for artifact storage."""

import json
import os
from typing import Any, ClassVar, Dict, Type

from zenml.enums import ArtifactType, VisualizationType
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.prompts.prompt import Prompt

logger = get_logger(__name__)

DEFAULT_PROMPT_FILENAME = "prompt.json"


class PromptMaterializer(BaseMaterializer):
    """Simple materializer for ZenML Prompt artifacts.

    This materializer handles saving/loading of Prompt objects as JSON files
    and extracts basic metadata for the ZenML dashboard.
    """

    ASSOCIATED_TYPES: ClassVar[tuple[Type[Any], ...]] = (Prompt,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[Prompt]) -> Prompt:
        """Load a Prompt object from storage.

        Args:
            data_type: The Prompt class

        Returns:
            The loaded Prompt object
        """
        prompt_file = os.path.join(self.uri, DEFAULT_PROMPT_FILENAME)

        with self.artifact_store.open(prompt_file, "r") as f:
            prompt_data = json.loads(f.read())

        return Prompt(**prompt_data)

    def save(self, data: Prompt) -> None:
        """Save a Prompt object to storage.

        Args:
            data: The Prompt object to save
        """
        prompt_file = os.path.join(self.uri, DEFAULT_PROMPT_FILENAME)

        # Convert to dictionary and save as JSON
        prompt_dict = data.model_dump(exclude_none=True)

        with self.artifact_store.open(prompt_file, "w") as f:
            f.write(json.dumps(prompt_dict, indent=2, default=str))

    def extract_metadata(self, data: Prompt) -> Dict[str, Any]:
        """Extract comprehensive metadata from a Prompt object.

        Args:
            data: The Prompt object

        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {
            # Basic prompt metadata
            "prompt_type": data.prompt_type,
            "template_length": len(data.template),
            "variable_count": len(data.variables),
            "variable_names": data.get_variable_names(),
            "missing_variables": data.get_missing_variables(),
            "variables_complete": data.validate_variables(),
            # Enhanced fields metadata
            "has_output_schema": data.output_schema is not None,
            "schema_type": type(data.output_schema).__name__
            if data.output_schema
            else None,
            "examples_count": len(data.examples),
            "has_examples": len(data.examples) > 0,
        }

        # Add schema details if available
        if data.output_schema is not None:
            schema_dict = data.get_schema_dict()
            if schema_dict:
                metadata["schema_properties"] = list(
                    schema_dict.get("properties", {}).keys()
                )
                metadata["schema_required"] = schema_dict.get("required", [])

        # Add example validation status
        if data.examples:
            valid_examples = [
                data.validate_example(ex) for ex in data.examples
            ]
            metadata["valid_examples_count"] = sum(valid_examples)
            metadata["all_examples_valid"] = all(valid_examples)

        logger.info(
            f"Extracted metadata for prompt: {data.prompt_type}, "
            f"schema={data.output_schema is not None}, "
            f"examples={len(data.examples)}"
        )
        return metadata

    def save_visualizations(
        self, data: Prompt
    ) -> Dict[str, VisualizationType]:
        """Save prompt visualizations for dashboard display.

        Args:
            data: The Prompt object to visualize

        Returns:
            Dictionary mapping visualization paths to their types
        """
        visualizations = {}

        # Create HTML visualization
        html_path = os.path.join(self.uri, "prompt_preview.html")
        html_content = self._generate_prompt_html(data)
        with self.artifact_store.open(html_path, "w") as f:
            f.write(html_content)
        visualizations[html_path] = VisualizationType.HTML

        # Create Markdown visualization
        md_path = os.path.join(self.uri, "prompt_preview.md")
        md_content = self._generate_prompt_markdown(data)
        with self.artifact_store.open(md_path, "w") as f:
            f.write(md_content)
        visualizations[md_path] = VisualizationType.MARKDOWN

        return visualizations

    def _generate_prompt_html(self, prompt: Prompt) -> str:
        """Generate HTML visualization for a prompt.

        Args:
            prompt: The Prompt object

        Returns:
            HTML string for dashboard display
        """
        # Escape HTML characters in template
        import html

        template_escaped = html.escape(prompt.template)

        # Highlight variables with a different color
        for var in prompt.get_variable_names():
            template_escaped = template_escaped.replace(
                f"{{{var}}}",
                f'<span style="color: #e74c3c; font-weight: bold;">{{{var}}}</span>',
            )

        # Generate sample output if all variables are provided
        sample_output = ""
        if prompt.validate_variables():
            try:
                formatted = html.escape(prompt.format(**prompt.variables))
                sample_output = f"""
                <div style="margin-top: 20px;">
                    <h3>Sample Output</h3>
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; font-family: monospace;">
                        {formatted}
                    </div>
                </div>
                """
            except Exception:
                pass

        # Build the HTML
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px;">
            <h2>Prompt Template</h2>
            <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span><strong>Type:</strong> {prompt.prompt_type}</span>
                </div>
                <div style="background-color: white; padding: 15px; border-radius: 5px; font-family: monospace; white-space: pre-wrap;">
                    {template_escaped}
                </div>
            </div>

            <h3>Variables</h3>
            <table style="border-collapse: collapse; width: 100%; margin: 10px 0;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Variable</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Default Value</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Add variable rows
        for var in prompt.get_variable_names():
            value = prompt.variables.get(var, "<i>Not provided</i>")
            if value != "<i>Not provided</i>":
                value = html.escape(str(value))
            html_content += f"""
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd; font-family: monospace;">{{{var}}}</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{value}</td>
                    </tr>
            """

        html_content += f"""
                </tbody>
            </table>

            <div style="margin-top: 20px;">
                <p><strong>Template Length:</strong> {len(prompt.template)} characters</p>
                <p><strong>Missing Variables:</strong> {", ".join(prompt.get_missing_variables()) or "None"}</p>
                <p><strong>Output Schema:</strong> {"Yes" if prompt.output_schema else "No"}</p>
                <p><strong>Examples:</strong> {len(prompt.examples)}</p>
            </div>

            {self._generate_schema_section_html(prompt)}
            {self._generate_examples_section_html(prompt)}
            {sample_output}
        </div>
        """

        return html_content

    def _generate_schema_section_html(self, prompt: Prompt) -> str:
        """Generate HTML section for output schema.

        Args:
            prompt: The Prompt object

        Returns:
            HTML string for schema section
        """
        if not prompt.output_schema:
            return ""

        import html

        schema_dict = prompt.get_schema_dict()
        if not schema_dict:
            return ""

        schema_json = html.escape(json.dumps(schema_dict, indent=2))

        return f"""
        <div style="margin-top: 20px;">
            <h3>Output Schema</h3>
            <div style="background-color: #e7f3ff; padding: 15px; border-radius: 5px;">
                <pre style="background-color: white; padding: 10px; border-radius: 3px; overflow-x: auto; font-family: monospace; font-size: 12px;">{schema_json}</pre>
            </div>
        </div>
        """

    def _generate_examples_section_html(self, prompt: Prompt) -> str:
        """Generate HTML section for examples.

        Args:
            prompt: The Prompt object

        Returns:
            HTML string for examples section
        """
        if not prompt.examples:
            return ""

        import html

        examples_html = """
        <div style="margin-top: 20px;">
            <h3>Examples</h3>
        """

        for i, example in enumerate(prompt.examples, 1):
            input_json = html.escape(
                json.dumps(example.get("input", {}), indent=2)
            )
            output_json = html.escape(
                json.dumps(example.get("output", {}), indent=2)
            )

            examples_html += f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #007bff;">
                <h4>Example {i}</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <strong>Input:</strong>
                        <pre style="background-color: white; padding: 10px; border-radius: 3px; font-family: monospace; font-size: 12px; margin-top: 5px;">{input_json}</pre>
                    </div>
                    <div>
                        <strong>Expected Output:</strong>
                        <pre style="background-color: white; padding: 10px; border-radius: 3px; font-family: monospace; font-size: 12px; margin-top: 5px;">{output_json}</pre>
                    </div>
                </div>
            </div>
            """

        examples_html += "</div>"
        return examples_html

    def _generate_prompt_markdown(self, prompt: Prompt) -> str:
        """Generate Markdown visualization for a prompt.

        Args:
            prompt: The Prompt object

        Returns:
            Markdown string for dashboard display
        """
        # Build variable table
        var_table = (
            "| Variable | Default Value |\n|----------|---------------|\n"
        )
        for var in prompt.get_variable_names():
            value = prompt.variables.get(var, "_Not provided_")
            var_table += f"| `{{{var}}}` | {value} |\n"

        # Generate sample output if possible
        sample_output = ""
        if prompt.validate_variables():
            try:
                formatted = prompt.format(**prompt.variables)
                sample_output = (
                    f"\n## Sample Output\n\n```\n{formatted}\n```\n"
                )
            except Exception:
                pass

        # Schema section
        schema_section = ""
        if prompt.output_schema:
            schema_dict = prompt.get_schema_dict()
            if schema_dict:
                schema_section = f"""
## Output Schema

```json
{json.dumps(schema_dict, indent=2)}
```
"""

        # Examples section
        examples_section = ""
        if prompt.examples:
            examples_section = "\n## Examples\n"
            for i, example in enumerate(prompt.examples, 1):
                examples_section += f"""
### Example {i}

**Input:**
```json
{json.dumps(example.get("input", {}), indent=2)}
```

**Expected Output:**
```json
{json.dumps(example.get("output", {}), indent=2)}
```
"""

        markdown = f"""# Prompt Template

**Type:** {prompt.prompt_type}

## Template

```
{prompt.template}
```

## Variables

{var_table}

## Metadata

- **Template Length:** {len(prompt.template)} characters
- **Variable Count:** {len(prompt.get_variable_names())}
- **Missing Variables:** {", ".join(prompt.get_missing_variables()) or "None"}
- **Output Schema:** {"Yes" if prompt.output_schema else "No"}
- **Examples:** {len(prompt.examples)}
{schema_section}{examples_section}{sample_output}
"""

        return markdown
