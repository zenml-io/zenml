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
"""PromptResponse materializer for artifact storage and linking."""

import json
import os
from typing import Any, ClassVar, Dict, Type

from zenml.enums import ArtifactType, VisualizationType
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.prompts.prompt_response import PromptResponse

logger = get_logger(__name__)

DEFAULT_RESPONSE_FILENAME = "prompt_response.json"


class PromptResponseMaterializer(BaseMaterializer):
    """Materializer for ZenML PromptResponse artifacts.

    This materializer handles saving/loading of PromptResponse objects as JSON
    files and extracts comprehensive metadata for tracking LLM outputs, costs,
    and quality metrics in the ZenML dashboard.

    The materializer supports:
    - Structured response data with parsing results
    - Generation metadata (model, parameters, timestamps)
    - Cost and token usage tracking
    - Quality scores and validation results
    - Provenance links to source prompts
    """

    ASSOCIATED_TYPES: ClassVar[tuple[Type[Any], ...]] = (PromptResponse,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[PromptResponse]) -> PromptResponse:  # noqa: ARG002
        """Load a PromptResponse object from storage.

        Args:
            data_type: The PromptResponse class

        Returns:
            The loaded PromptResponse object
        """
        response_file = os.path.join(self.uri, DEFAULT_RESPONSE_FILENAME)

        with self.artifact_store.open(response_file, "r") as f:
            response_data = json.loads(f.read())

        return PromptResponse(**response_data)

    def save(self, data: PromptResponse) -> None:
        """Save a PromptResponse object to storage.

        Args:
            data: The PromptResponse object to save
        """
        response_file = os.path.join(self.uri, DEFAULT_RESPONSE_FILENAME)

        # Convert to dictionary and save as JSON
        response_dict = data.model_dump(exclude_none=True)

        with self.artifact_store.open(response_file, "w") as f:
            f.write(json.dumps(response_dict, indent=2, default=str))

    def extract_metadata(self, data: PromptResponse) -> Dict[str, Any]:
        """Extract comprehensive metadata from a PromptResponse object.

        Args:
            data: The PromptResponse object

        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {
            # Content metadata
            "content_length": len(data.content),
            "has_parsed_output": data.parsed_output is not None,
            # Generation metadata
            "model_name": data.model_name,
            "temperature": data.temperature,
            "max_tokens": data.max_tokens,
            # Usage and cost tracking
            "prompt_tokens": data.prompt_tokens,
            "completion_tokens": data.completion_tokens,
            "total_tokens": data.total_tokens,
            "total_cost": data.total_cost,
            "token_efficiency": data.get_token_efficiency(),
            "cost_per_token": data.get_cost_per_token(),
            # Quality metrics
            "quality_score": data.quality_score,
            "validation_passed": data.validation_passed,
            "validation_error_count": len(data.validation_errors),
            "is_valid_response": data.is_valid_response(),
            # Provenance
            "prompt_id": data.prompt_id,
            "prompt_version": data.prompt_version,
            "parent_response_count": len(data.parent_response_ids),
            # Timing
            "created_at": data.created_at.isoformat()
            if data.created_at
            else None,
            "response_time_ms": data.response_time_ms,
        }

        # Add custom metadata
        if data.metadata:
            for key, value in data.metadata.items():
                metadata[key] = value

        logger.info(
            f"Extracted metadata for response: model={data.model_name}, "
            f"tokens={data.total_tokens}, cost=${data.total_cost or 0:.4f}"
        )
        return metadata

    def save_visualizations(
        self, data: PromptResponse
    ) -> Dict[str, VisualizationType]:
        """Save response visualizations for dashboard display.

        Args:
            data: The PromptResponse object to visualize

        Returns:
            Dictionary mapping visualization paths to their types
        """
        visualizations = {}

        # Create HTML visualization
        html_path = os.path.join(self.uri, "response_preview.html")
        html_content = self._generate_response_html(data)
        with self.artifact_store.open(html_path, "w") as f:
            f.write(html_content)
        visualizations[html_path] = VisualizationType.HTML

        # Create Markdown visualization
        md_path = os.path.join(self.uri, "response_preview.md")
        md_content = self._generate_response_markdown(data)
        with self.artifact_store.open(md_path, "w") as f:
            f.write(md_content)
        visualizations[md_path] = VisualizationType.MARKDOWN

        # Create JSON visualization for structured output
        if data.parsed_output is not None:
            json_path = os.path.join(self.uri, "parsed_output.json")
            with self.artifact_store.open(json_path, "w") as f:
                f.write(json.dumps(data.parsed_output, indent=2, default=str))
            visualizations[json_path] = VisualizationType.JSON

        return visualizations

    def _generate_response_html(self, response: PromptResponse) -> str:
        """Generate HTML visualization for a response.

        Args:
            response: The PromptResponse object

        Returns:
            HTML string for dashboard display
        """
        import html

        content_escaped = html.escape(response.content)

        # Status indicators
        status_color = "#28a745" if response.is_valid_response() else "#dc3545"
        status_text = "Valid" if response.is_valid_response() else "Invalid"

        quality_color = (
            "#28a745"
            if (response.quality_score or 0) > 0.8
            else "#ffc107"
            if (response.quality_score or 0) > 0.5
            else "#dc3545"
        )

        # Cost and efficiency metrics
        cost_section = ""
        if (
            response.total_cost is not None
            or response.total_tokens is not None
        ):
            cost_section = f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>Usage & Cost</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                    <div><strong>Prompt Tokens:</strong> {response.prompt_tokens or "N/A"}</div>
                    <div><strong>Completion Tokens:</strong> {response.completion_tokens or "N/A"}</div>
                    <div><strong>Total Tokens:</strong> {response.total_tokens or "N/A"}</div>
                    <div><strong>Total Cost:</strong> ${response.total_cost or 0:.4f}</div>
                    <div><strong>Token Efficiency:</strong> {(response.get_token_efficiency() or 0) * 100:.1f}%</div>
                    <div><strong>Cost per Token:</strong> ${response.get_cost_per_token() or 0:.6f}</div>
                </div>
            </div>
            """

        # Validation section
        validation_section = ""
        if response.validation_errors:
            validation_section = f"""
            <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3 style="color: #721c24;">Validation Errors</h3>
                <ul>
                    {"".join(f"<li>{html.escape(error)}</li>" for error in response.validation_errors)}
                </ul>
            </div>
            """

        # Parsed output section
        parsed_section = ""
        if response.parsed_output is not None:
            parsed_escaped = html.escape(
                json.dumps(response.parsed_output, indent=2, default=str)
            )
            parsed_section = f"""
            <div style="background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>Parsed Output</h3>
                <pre style="background-color: white; padding: 10px; border-radius: 3px; overflow-x: auto;">{parsed_escaped}</pre>
            </div>
            """

        # Provenance section
        provenance_section = ""
        if response.prompt_id:
            provenance_section = f"""
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3>Provenance</h3>
                <div><strong>Source Prompt ID:</strong> {response.prompt_id}</div>
                {f"<div><strong>Prompt Version:</strong> {response.prompt_version}</div>" if response.prompt_version else ""}
                {f"<div><strong>Parent Responses:</strong> {len(response.parent_response_ids)}</div>" if response.parent_response_ids else ""}
            </div>
            """

        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2>LLM Response</h2>
                <div>
                    <span style="background-color: {status_color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 8px;">
                        {status_text}
                    </span>
                    {f'<span style="background-color: {quality_color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">Quality: {(response.quality_score or 0) * 100:.0f}%</span>' if response.quality_score is not None else ""}
                </div>
            </div>

            <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span><strong>Model:</strong> {response.model_name or "Unknown"}</span>
                    <span><strong>Length:</strong> {len(response.content)} chars</span>
                </div>
                <div style="background-color: white; padding: 15px; border-radius: 5px; font-family: monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto;">
                    {content_escaped}
                </div>
            </div>

            {cost_section}
            {validation_section}
            {parsed_section}
            {provenance_section}

            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                <p><strong>Generated:</strong> {response.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if response.created_at else "Unknown"}</p>
                <p><strong>Response Time:</strong> {response.response_time_ms or "N/A"} ms</p>
            </div>
        </div>
        """

        return html_content

    def _generate_response_markdown(self, response: PromptResponse) -> str:
        """Generate Markdown visualization for a response.

        Args:
            response: The PromptResponse object

        Returns:
            Markdown string for dashboard display
        """
        # Status and quality indicators
        status_emoji = "✅" if response.is_valid_response() else "❌"
        quality_emoji = (
            "🟢"
            if (response.quality_score or 0) > 0.8
            else "🟡"
            if (response.quality_score or 0) > 0.5
            else "🔴"
        )

        # Build markdown content
        markdown = f"""# LLM Response {status_emoji}

**Model:** {response.model_name or "Unknown"}  
**Status:** {"Valid" if response.is_valid_response() else "Invalid"}  
**Quality:** {quality_emoji} {(response.quality_score or 0) * 100:.0f}%  
**Length:** {len(response.content)} characters

## Content

```
{response.content}
```
"""

        # Add usage and cost section
        if (
            response.total_cost is not None
            or response.total_tokens is not None
        ):
            markdown += f"""
## Usage & Cost

| Metric | Value |
|--------|-------|
| Prompt Tokens | {response.prompt_tokens or "N/A"} |
| Completion Tokens | {response.completion_tokens or "N/A"} |
| Total Tokens | {response.total_tokens or "N/A"} |
| Total Cost | ${response.total_cost or 0:.4f} |
| Token Efficiency | {(response.get_token_efficiency() or 0) * 100:.1f}% |
| Cost per Token | ${response.get_cost_per_token() or 0:.6f} |
"""

        # Add validation errors if any
        if response.validation_errors:
            markdown += f"""
## Validation Errors

"""
            for error in response.validation_errors:
                markdown += f"- {error}\n"

        # Add parsed output if available
        if response.parsed_output is not None:
            markdown += f"""
## Parsed Output

```json
{json.dumps(response.parsed_output, indent=2, default=str)}
```
"""

        # Add provenance information
        if response.prompt_id:
            markdown += f"""
## Provenance

- **Source Prompt ID:** {response.prompt_id}
"""
            if response.prompt_version:
                markdown += (
                    f"- **Prompt Version:** {response.prompt_version}\n"
                )
            if response.parent_response_ids:
                markdown += f"- **Parent Responses:** {len(response.parent_response_ids)}\n"

        # Add metadata
        markdown += f"""
## Metadata

- **Generated:** {response.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if response.created_at else "Unknown"}
- **Response Time:** {response.response_time_ms or "N/A"} ms
- **Temperature:** {response.temperature or "N/A"}
- **Max Tokens:** {response.max_tokens or "N/A"}
"""

        return markdown
