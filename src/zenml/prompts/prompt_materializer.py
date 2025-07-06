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
"""Enhanced Prompt materializer for artifact storage and visualization."""

import json
import os
from typing import Any, ClassVar, Dict, Type

from zenml.enums import ArtifactType, VisualizationType
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.prompts.prompt import Prompt

logger = get_logger(__name__)

DEFAULT_PROMPT_FILENAME = "prompt.json"
VISUALIZATION_FILENAME = "prompt_visualization.html"


class PromptMaterializer(BaseMaterializer):
    """Enhanced materializer for ZenML Prompt abstraction.

    This materializer handles saving/loading of Prompt objects and creates
    rich HTML visualizations for the ZenML dashboard with enhanced features.
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

        # Read the JSON file
        with self.artifact_store.open(prompt_file, "r") as f:
            prompt_data = json.loads(f.read())

        return Prompt.from_dict(prompt_data)

    def save(self, data: Prompt) -> None:
        """Save a Prompt object to storage.

        Args:
            data: The Prompt object to save
        """
        prompt_file = os.path.join(self.uri, DEFAULT_PROMPT_FILENAME)

        # Convert to dictionary and save as JSON
        prompt_dict = data.to_dict()

        with self.artifact_store.open(prompt_file, "w") as f:
            f.write(json.dumps(prompt_dict, indent=2, default=str))

    def extract_metadata(self, data: Prompt) -> Dict[str, Any]:
        """Extract comprehensive metadata from a Prompt object.

        Args:
            data: The Prompt object

        Returns:
            Dictionary containing extracted metadata
        """
        summary = data.get_summary()

        metadata = {
            # Core information
            "prompt_id": data.prompt_id,
            "prompt_type": data.prompt_type,
            "task": data.task,
            "version": data.version,
            "description": data.description,
            
            # Template analysis
            "template_length": summary["template_length"],
            "variable_count": summary["variable_count"],
            "variable_names": summary["variable_names"],
            "missing_variables": summary["missing_variables"],
            "variables_complete": summary["variables_complete"],
            
            # Configuration
            "has_examples": summary["has_examples"],
            "example_count": len(data.examples) if data.examples else 0,
            "has_instructions": summary["has_instructions"],
            "complexity_score": data.get_complexity_score(),
            
            # Timestamps
            "created_at": data.created_at.isoformat()
            if data.created_at
            else None,
            "updated_at": data.updated_at.isoformat()
            if data.updated_at
            else None,
            
            # Tags and metadata
            "tags": data.tags,
            "custom_metadata": data.metadata,
        }

        # Add token estimation if possible
        if data.variables:
            estimated_tokens = data.estimate_tokens()
            if estimated_tokens:
                metadata["estimated_tokens"] = estimated_tokens

        return {k: v for k, v in metadata.items() if v is not None}

    def save_visualizations(
        self, data: Prompt
    ) -> Dict[str, VisualizationType]:
        """Generate and save visualizations for the Prompt.

        Args:
            data: The Prompt object to visualize

        Returns:
            Dictionary mapping visualization file names to their types
        """
        # Generate enhanced HTML visualization
        html_content = self._generate_html_visualization(data)
        html_path = os.path.join(self.uri, "visualization.html")

        with self.artifact_store.open(html_path, "w") as f:
            f.write(html_content)

        return {"visualization.html": VisualizationType.HTML}

    def _generate_html_visualization(self, data: Prompt) -> str:
        """Generate comprehensive HTML visualization for the Prompt.

        Args:
            data: The Prompt object

        Returns:
            HTML string for visualization
        """
        summary = data.get_summary()

        # Main sections
        header_html = self._render_header(data, summary)
        template_html = self._render_template_section(data)
        config_html = self._render_configuration_section(data)
        examples_html = self._render_examples_section(data)
        performance_html = self._render_performance_section(data)
        metadata_html = self._render_metadata_section(data)
        lineage_html = self._render_lineage_section(data)

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>ZenML Prompt Visualization</title>
            <style>
                {self._get_css_styles()}
            </style>
            <script>
                {self._get_javascript()}
            </script>
        </head>
        <body>
            <div class="prompt-container">
                {header_html}
                {template_html}
                {config_html}
                {examples_html}
                {performance_html}
                {lineage_html}
                {metadata_html}
            </div>
        </body>
        </html>
        """

    def _render_header(self, data: Prompt, summary: Dict[str, Any]) -> str:
        """Render the header section with enhanced information."""
        status_badges = []

        # Completion status
        if summary["variables_complete"]:
            status_badges.append(
                '<span class="badge badge-success">✓ Variables Complete</span>'
            )
        else:
            status_badges.append(
                '<span class="badge badge-warning">⚠ Missing Variables</span>'
            )

        # Type and task badges
        if data.prompt_type:
            status_badges.append(
                f'<span class="badge badge-info">{data.prompt_type.title()}</span>'
            )
        if data.task:
            status_badges.append(
                f'<span class="badge badge-primary">{data.task.title()}</span>'
            )
        
        # Complexity badge
        complexity = data.get_complexity_score()
        complexity_class = "low" if complexity < 0.3 else "medium" if complexity < 0.7 else "high"
        status_badges.append(
            f'<span class="badge badge-{complexity_class}">Complexity: {complexity:.1f}</span>'
        )

        version_info = f"v{data.version}" if data.version else "No Version"
        prompt_id_short = data.prompt_id[:8] + "..." if data.prompt_id else "unknown"

        return f"""
        <div class="header">
            <h1>🎯 ZenML Prompt</h1>
            <div class="header-info">
                <div class="left-info">
                    <div class="version">{version_info}</div>
                    <div class="prompt-id">ID: {prompt_id_short}</div>
                </div>
                <div class="badges">
                    {" ".join(status_badges)}
                </div>
            </div>
            {f'<p class="description">{data.description}</p>' if data.description else ""}
        </div>
        """

    def _render_template_section(self, data: Prompt) -> str:
        """Render the template section with syntax highlighting."""
        formatted_template = data.template.replace("\\n", "<br>")

        # Highlight variables with enhanced styling
        import re

        formatted_template = re.sub(
            r"\{([^}]+)\}",
            r'<span class="variable" title="Variable: \1">{<span class="variable-name">\1</span>}</span>',
            formatted_template,
        )

        # Variables section with status indicators
        variables_html = ""
        if data.variables:
            var_items = []
            for k, v in data.variables.items():
                var_items.append(
                    f'<li><span class="var-key">{k}</span> = <span class="var-value">"{v}"</span></li>'
                )
            variables_html = f"""
            <div class="variables">
                <h4>📋 Default Variables</h4>
                <ul class="variable-list">
                    {"".join(var_items)}
                </ul>
            </div>
            """

        missing_vars = data.get_missing_variables()
        missing_html = ""
        if missing_vars:
            missing_items = [
                f"<li><code>{var}</code></li>" for var in missing_vars
            ]
            missing_html = f"""
            <div class="missing-variables">
                <h4>⚠️ Missing Variables</h4>
                <ul class="missing-list">
                    {"".join(missing_items)}
                </ul>
            </div>
            """

        # Template stats
        template_stats = f"""
        <div class="template-stats">
            <span class="stat">📏 {len(data.template)} chars</span>
            <span class="stat">🔢 {len(data.get_variable_names())} variables</span>
            <span class="stat">📊 {data.estimate_tokens() or 'Unknown'} tokens (est.)</span>
        </div>
        """

        return f"""
        <div class="section template-section">
            <h2>📝 Template</h2>
            {template_stats}
            <div class="template-content">
                <pre class="template-text">{formatted_template}</pre>
                <button class="copy-btn" onclick="copyTemplate()" title="Copy template">📋</button>
            </div>
            {variables_html}
            {missing_html}
        </div>
        """

    def _render_configuration_section(self, data: Prompt) -> str:
        """Render the configuration section."""
        config_items = []

        # Basic configuration
        if data.prompt_type:
            config_items.append(("Prompt Type", data.prompt_type, "🏷️"))
        if data.task:
            config_items.append(("Task", data.task, "🎯"))
        if data.instructions:
            config_items.append(("Instructions", data.instructions[:100] + "..." if len(data.instructions) > 100 else data.instructions, "📋"))

        if not config_items:
            return ""

        config_html = []
        for label, value, icon in config_items:
            config_html.append(f"""
            <div class="config-item">
                <span class="config-icon">{icon}</span>
                <span class="config-label">{label}:</span>
                <span class="config-value">{value}</span>
            </div>
            """)

        return f"""
        <div class="section config-section">
            <h2>⚙️ Configuration</h2>
            <div class="config-grid">
                {"".join(config_html)}
            </div>
        </div>
        """

    def _render_examples_section(self, data: Prompt) -> str:
        """Render the examples section."""
        if not data.examples:
            return ""

        examples_html = []
        for i, example in enumerate(data.examples, 1):
            example_content = []
            for key, value in example.items():
                example_content.append(f"""
                <div class="example-field">
                    <label>{key.title()}:</label>
                    <div class="example-value">{value}</div>
                </div>
                """)

            examples_html.append(f"""
            <div class="example-item">
                <h4>Example {i}</h4>
                {"".join(example_content)}
            </div>
            """)

        return f"""
        <div class="section examples-section">
            <h2>💡 Examples ({len(data.examples)})</h2>
            <div class="examples-grid">
                {"".join(examples_html)}
            </div>
        </div>
        """

    def _render_performance_section(self, data: Prompt) -> str:
        """Render the performance metrics section."""
        if not data.performance_metrics:
            return ""

        metrics_html = []
        for metric, value in data.performance_metrics.items():
            # Format metric value
            if isinstance(value, float):
                formatted_value = f"{value:.3f}"
                # Add trend indicator if available
                trend_icon = "📈" if value > 0.7 else "📊" if value > 0.5 else "📉"
            else:
                formatted_value = str(value)
                trend_icon = "📊"

            metrics_html.append(f"""
            <div class="metric-item">
                <div class="metric-icon">{trend_icon}</div>
                <div class="metric-name">{metric.replace("_", " ").title()}</div>
                <div class="metric-value">{formatted_value}</div>
            </div>
            """)

        return f"""
        <div class="section performance-section">
            <h2>📈 Performance Metrics</h2>
            <div class="metrics-grid">
                {"".join(metrics_html)}
            </div>
        </div>
        """

    def _render_lineage_section(self, data: Prompt) -> str:
        """Render the lineage and versioning section."""
        if not data.parent_prompt_id and not data.version:
            return ""

        lineage_items = []

        if data.parent_prompt_id:
            lineage_items.append(f"""
            <div class="lineage-item">
                <span class="lineage-icon">👨‍👩‍👧‍👦</span>
                <span class="lineage-label">Parent ID:</span>
                <span class="lineage-value">{data.parent_prompt_id[:8]}...</span>
            </div>
            """)

        if data.version:
            lineage_items.append(f"""
            <div class="lineage-item">
                <span class="lineage-icon">🏷️</span>
                <span class="lineage-label">Version:</span>
                <span class="lineage-value">{data.version}</span>
            </div>
            """)

        return f"""
        <div class="section lineage-section">
            <h2>🌳 Lineage & Versioning</h2>
            <div class="lineage-grid">
                {"".join(lineage_items)}
            </div>
        </div>
        """

    def _render_metadata_section(self, data: Prompt) -> str:
        """Render additional metadata section."""
        metadata_items = []

        # Tags
        if data.tags:
            tags_html = " ".join(
                [f'<span class="tag">{tag}</span>' for tag in data.tags]
            )
            metadata_items.append(("Tags", tags_html))

        # Timestamps
        if data.created_at:
            metadata_items.append(
                ("Created", data.created_at.strftime("%Y-%m-%d %H:%M:%S"))
            )
        if data.updated_at:
            metadata_items.append(
                ("Updated", data.updated_at.strftime("%Y-%m-%d %H:%M:%S"))
            )

        # Custom metadata
        if data.metadata:
            for key, value in data.metadata.items():
                metadata_items.append(
                    (key.replace("_", " ").title(), str(value))
                )

        if not metadata_items:
            return ""

        metadata_html = []
        for label, value in metadata_items:
            metadata_html.append(f"""
            <div class="metadata-item">
                <span class="metadata-label">{label}:</span>
                <span class="metadata-value">{value}</span>
            </div>
            """)

        return f"""
        <div class="section metadata-section">
            <h2>ℹ️ Metadata</h2>
            <div class="metadata-grid">
                {"".join(metadata_html)}
            </div>
        </div>
        """

    def _get_javascript(self) -> str:
        """Get JavaScript for interactive features."""
        return """
        function copyTemplate() {
            const templateElement = document.querySelector('.template-text');
            const text = templateElement.textContent;
            navigator.clipboard.writeText(text).then(() => {
                const btn = document.querySelector('.copy-btn');
                const originalText = btn.textContent;
                btn.textContent = '✅';
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 1000);
            });
        }
        
        // Add click handlers for expandable sections
        document.addEventListener('DOMContentLoaded', function() {
            const sections = document.querySelectorAll('.section h2');
            sections.forEach(header => {
                header.style.cursor = 'pointer';
                header.addEventListener('click', function() {
                    const section = this.parentElement;
                    section.classList.toggle('collapsed');
                });
            });
        });
        """

    def _get_css_styles(self) -> str:
        """Get enhanced CSS styles for the HTML visualization."""
        return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }
        
        .prompt-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            position: relative;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="20" cy="20" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="80" cy="80" r="1" fill="rgba(255,255,255,0.1)"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
            opacity: 0.3;
        }
        
        .header h1 {
            margin: 0 0 15px 0;
            font-size: 2.5em;
            font-weight: 300;
            position: relative;
            z-index: 1;
        }
        
        .header-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            position: relative;
            z-index: 1;
        }
        
        .left-info {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 5px;
        }
        
        .version, .prompt-id, .author {
            background: rgba(255, 255, 255, 0.2);
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: 500;
            font-size: 0.9em;
        }
        
        .badges {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 500;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        .badge-success { background: #28a745; color: white; }
        .badge-warning { background: #ffc107; color: #212529; }
        .badge-info { background: #17a2b8; color: white; }
        .badge-primary { background: #007bff; color: white; }
        .badge-low { background: #6c757d; color: white; }
        .badge-medium { background: #fd7e14; color: white; }
        .badge-high { background: #dc3545; color: white; }
        
        .description {
            margin: 15px 0 0 0;
            font-size: 1.1em;
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }
        
        .section {
            padding: 30px;
            border-bottom: 1px solid #e9ecef;
            transition: all 0.3s ease;
        }
        
        .section:last-child {
            border-bottom: none;
        }
        
        .section.collapsed {
            padding: 15px 30px;
        }
        
        .section.collapsed > *:not(h2) {
            display: none;
        }
        
        .section h2 {
            margin: 0 0 20px 0;
            font-size: 1.5em;
            color: #495057;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .template-stats {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            font-size: 0.9em;
            color: #6c757d;
        }
        
        .stat {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .template-content {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            position: relative;
        }
        
        .template-text {
            margin: 0;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 14px;
            line-height: 1.8;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .copy-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 5px 10px;
            cursor: pointer;
            font-size: 0.8em;
            transition: background 0.2s;
        }
        
        .copy-btn:hover {
            background: #0056b3;
        }
        
        .variable {
            background: linear-gradient(45deg, #e3f2fd, #bbdefb);
            color: #1565c0;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        
        .variable:hover {
            background: linear-gradient(45deg, #bbdefb, #90caf9);
            transform: scale(1.05);
        }
        
        .variable-name {
            color: #0d47a1;
        }
        
        .variables, .missing-variables {
            margin-top: 15px;
            padding: 15px;
            border-radius: 8px;
        }
        
        .variables {
            background: linear-gradient(45deg, #e8f5e8, #c8e6c9);
            border-left: 4px solid #28a745;
        }
        
        .missing-variables {
            background: linear-gradient(45deg, #fff3cd, #ffeaa7);
            border-left: 4px solid #ffc107;
        }
        
        .variables h4, .missing-variables h4 {
            margin: 0 0 10px 0;
            color: #495057;
        }
        
        .variable-list, .missing-list {
            margin: 0;
            padding-left: 20px;
        }
        
        .variable-list li {
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .var-key {
            background: #495057;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9em;
        }
        
        .var-value {
            color: #28a745;
            font-weight: 500;
            font-family: monospace;
        }
        
        .config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }
        
        .config-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px;
            background: linear-gradient(45deg, #f8f9fa, #e9ecef);
            border-radius: 8px;
            border-left: 4px solid #007bff;
            transition: all 0.3s ease;
        }
        
        .config-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .config-icon {
            font-size: 1.2em;
            flex-shrink: 0;
        }
        
        .config-label {
            font-weight: 600;
            color: #495057;
            flex-shrink: 0;
        }
        
        .config-value {
            color: #6c757d;
            font-family: monospace;
            word-break: break-word;
        }
        
        .examples-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }
        
        .example-item {
            background: linear-gradient(45deg, #f8f9fa, #fff);
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .example-item h4 {
            margin: 0 0 15px 0;
            color: #495057;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 8px;
        }
        
        .example-field {
            margin-bottom: 12px;
        }
        
        .example-field label {
            display: block;
            font-weight: 600;
            color: #495057;
            margin-bottom: 4px;
        }
        
        .example-value {
            background: white;
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid #dee2e6;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .metric-item {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .metric-item:hover {
            transform: translateY(-4px);
        }
        
        .metric-icon {
            font-size: 1.5em;
            margin-bottom: 8px;
        }
        
        .metric-name {
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 8px;
        }
        
        .metric-value {
            font-size: 1.8em;
            font-weight: 600;
        }
        
        .lineage-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }
        
        .lineage-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px;
            background: linear-gradient(45deg, #f1f3f4, #e8eaed);
            border-radius: 8px;
            border-left: 4px solid #6c757d;
        }
        
        .lineage-icon {
            font-size: 1.2em;
            flex-shrink: 0;
        }
        
        .lineage-label {
            font-weight: 600;
            color: #495057;
            flex-shrink: 0;
        }
        
        .lineage-value {
            color: #6c757d;
            font-family: monospace;
        }
        
        .metadata-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 12px;
        }
        
        .metadata-item {
            display: flex;
            padding: 10px 0;
            border-bottom: 1px solid #e9ecef;
        }
        
        .metadata-label {
            font-weight: 600;
            color: #495057;
            margin-right: 10px;
            min-width: 120px;
            flex-shrink: 0;
        }
        
        .metadata-value {
            color: #6c757d;
            flex: 1;
            word-break: break-word;
        }
        
        .tag {
            display: inline-block;
            background: linear-gradient(45deg, #007bff, #0056b3);
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-right: 5px;
            margin-bottom: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        @media (max-width: 768px) {
            .header-info {
                flex-direction: column;
                gap: 15px;
            }
            
            .badges {
                justify-content: center;
            }
            
            .config-grid,
            .examples-grid,
            .metrics-grid,
            .lineage-grid,
            .metadata-grid {
                grid-template-columns: 1fr;
            }
        }
        """