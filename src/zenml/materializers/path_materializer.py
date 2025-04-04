#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of the materializer for Path objects."""

import base64
import os
import tarfile
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, ClassVar, Dict, Tuple, Type

from zenml.enums import ArtifactType, VisualizationType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class PathMaterializer(BaseMaterializer):
    """Materializer for Path objects with direct download links.

    This materializer handles `pathlib.Path` objects by storing their contents
    in a compressed tar archive within the artifact store. It also provides
    visualizations with direct download links for viewing and downloading
    the contents of the Path.
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Path,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
    ARCHIVE_NAME: ClassVar[str] = "data.tar.gz"

    def load(self, data_type: Type[Any]) -> Any:
        """Copy the artifact files to a local temp directory.

        Args:
            data_type: Unused.

        Returns:
            Path to the local directory that contains the artifact files.
        """
        directory = mkdtemp(prefix="zenml-artifact")
        archive_path_remote = os.path.join(self.uri, self.ARCHIVE_NAME)
        archive_path_local = os.path.join(directory, self.ARCHIVE_NAME)

        fileio.copy(archive_path_remote, archive_path_local)

        # Extract the archive to the temporary directory
        with tarfile.open(archive_path_local, "r:gz") as tar:
            tar.extractall(path=directory)

        # Clean up the archive file
        os.remove(archive_path_local)

        return Path(directory)

    def save(self, data: Any) -> None:
        """Store the directory in the artifact store.

        Args:
            data: Path to a local directory to store.
        """
        assert isinstance(data, Path)

        # Ensure the destination directory exists
        directory = mkdtemp(prefix="zenml-artifact")
        archive_path = os.path.join(directory, self.ARCHIVE_NAME)

        # Create a compressed tar archive
        with tarfile.open(archive_path, "w:gz") as tar:
            # Get the current working directory
            original_dir = os.getcwd()
            try:
                # Change to the source directory to preserve relative paths
                os.chdir(str(data))

                # Add all files and directories
                for item in os.listdir("."):
                    tar.add(item)
            finally:
                # Restore the original working directory
                os.chdir(original_dir)

        # Copy the archive to the artifact store
        fileio.copy(archive_path, os.path.join(self.uri, self.ARCHIVE_NAME))

        # Clean up the temporary archive
        os.remove(archive_path)

    def save_visualizations(self, data: Path) -> Dict[str, VisualizationType]:
        """Create HTML visualization with direct download links.

        Args:
            data: The Path object to visualize.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        visualizations = {}

        try:
            # Load the directory (either from original data or from artifact store)
            if os.path.exists(str(data)):
                directory_path = data
            else:
                directory_path = self.load(Path)

            # Prepare file data
            files_data = []
            for file_path in sorted(directory_path.glob("**/*")):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(directory_path))
                    size_bytes = file_path.stat().st_size

                    # Read the file content
                    with open(file_path, "rb") as f:
                        content_bytes = f.read()
                    content_b64 = base64.b64encode(content_bytes).decode(
                        "utf-8"
                    )

                    # For text files, also get preview content
                    is_text = self._is_text_file(file_path)
                    preview_content = ""
                    if is_text:
                        preview_content = content_bytes.decode(
                            "utf-8", errors="replace"
                        )

                    files_data.append(
                        {
                            "path": rel_path,
                            "filename": os.path.basename(rel_path),
                            "size": self._format_size(size_bytes),
                            "size_bytes": size_bytes,
                            "data": content_b64,
                            "is_text": is_text,
                            "preview": preview_content if is_text else "",
                        }
                    )

            # Create an HTML page with direct download links
            html_content = self._create_direct_download_html(files_data)
            html_uri = os.path.join(self.uri, "files_direct.html")
            with self.artifact_store.open(html_uri, "w") as f:
                f.write(html_content)

            visualizations[html_uri] = VisualizationType.HTML

        except Exception as e:
            # If something goes wrong, create a simple error visualization
            error_uri = os.path.join(self.uri, "error.html")
            error_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .error {{ color: red; background-color: #fee; padding: 10px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Error Creating Visualization</h1>
    <div class="error">{str(e)}</div>
</body>
</html>"""
            with self.artifact_store.open(error_uri, "w") as f:
                f.write(error_html)
            visualizations[error_uri] = VisualizationType.HTML

        return visualizations

    def _is_text_file(self, file_path: Path) -> bool:
        """Check if a file is likely a text file based on extension or content.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file is likely a text file, False otherwise
        """
        # Common text file extensions
        text_extensions = {
            ".txt",
            ".log",
            ".md",
            ".markdown",
            ".csv",
            ".json",
            ".yaml",
            ".yml",
            ".html",
            ".htm",
            ".css",
            ".js",
            ".py",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".sh",
            ".bat",
            ".cmd",
            ".xml",
            ".sql",
            ".diff",
            ".patch",
            ".gitignore",
        }

        if file_path.suffix.lower() in text_extensions:
            return True

        # For files without recognized extensions, try to detect if they're text
        try:
            # Read the first 1024 bytes and check if they're valid UTF-8
            with open(file_path, "rb") as f:
                sample = f.read(1024)
            sample.decode("utf-8")
            return True
        except (UnicodeDecodeError, IOError):
            return False

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in a human-readable way.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string (e.g., "1.23 MB")
        """
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1

        return f"{size:.1f} {units[unit_index]}"

    def _create_direct_download_html(
        self, files_data: list[Dict[str, Any]]
    ) -> str:
        """Create an HTML page with direct download links.

        Instead of using JavaScript to create downloads, this approach
        uses direct data URIs in anchor tags, which should be more compatible
        with the ZenML dashboard environment.

        Args:
            files_data: List of dictionaries with file information

        Returns:
            HTML content as a string
        """
        # Create file rows with direct download links
        file_rows = ""
        for file_info in files_data:
            # Create a direct download link with appropriate MIME type
            mime_type = self._get_mime_type(file_info["path"])
            # Text files work better with text/plain MIME type for downloads
            download_mime_type = (
                "text/plain" if file_info["is_text"] else mime_type
            )
            download_button = f"""
            <a href="data:{download_mime_type};base64,{file_info["data"]}" 
               download="{file_info["filename"]}" 
               class="download-btn">Download</a>"""

            # Add preview button if it's a text file
            preview_button = ""
            if file_info["is_text"]:
                # Use Base64 encoding for the content
                try:
                    content_b64 = base64.b64encode(
                        file_info["preview"].encode("utf-8")
                    ).decode("utf-8")
                    # Create preview button with HTML attributes
                    path_attr = file_info["path"].replace('"', "&quot;")
                    preview_button = '<button data-path="' + path_attr + '" '
                    preview_button += 'data-content-b64="' + content_b64 + '" '
                    preview_button += 'onclick="showPreviewFromData(this)" '
                    preview_button += 'class="preview-btn">Preview</button>'
                except Exception:
                    # Fallback to simpler preview button if encoding fails
                    preview_button = '<button class="preview-btn" disabled>Preview (Failed)</button>'

            # Build row HTML using string concatenation instead of f-string
            row_html = "<tr>"
            row_html += "<td>" + file_info["path"] + "</td>"
            row_html += "<td>" + file_info["size"] + "</td>"
            row_html += "<td>"
            row_html += download_button
            row_html += preview_button
            row_html += "</td>"
            row_html += "</tr>"

            file_rows += row_html

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Directory Contents</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; min-height: 95vh; }}
        h1 {{ color: #333; margin-bottom: 10px; }}
        .container {{ display: flex; flex-direction: column; height: 90vh; }}
        .file-list {{ margin-top: 10px; border: 1px solid #ddd; border-radius: 5px; overflow: auto; width: 100%; flex: 1; min-height: 400px; }}
        .file-list table {{ border-collapse: collapse; width: 100%; }}
        .file-list th {{ background-color: #f2f2f2; text-align: left; padding: 12px; border-bottom: 1px solid #ddd; position: sticky; top: 0; z-index: 1; }}
        .file-list td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
        .file-list tr:hover {{ background-color: #f5f5f5; }}
        .download-btn {{ display: inline-block; padding: 8px 12px; background-color: #008CBA; color: white; 
                      border: none; border-radius: 4px; text-decoration: none; cursor: pointer; }}
        .preview-btn {{ padding: 8px 12px; background-color: #4CAF50; color: white; 
                     border: none; border-radius: 4px; cursor: pointer; margin-left: 5px; }}
        .preview-container {{ display: none; margin-top: 20px; padding: 15px; border: 1px solid #ddd; 
                          border-radius: 5px; max-height: 50vh; min-height: 300px; overflow: auto; }}
        .preview-container pre {{ white-space: pre-wrap; font-family: monospace; margin: 0; }}
        .close-btn {{ float: right; background-color: #f44336; color: white; 
                   border: none; border-radius: 4px; padding: 5px 10px; cursor: pointer; }}
        p {{ margin-top: 5px; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Directory Contents</h1>
        <p>Click on a download button to save a file to your computer.</p>
        
        <div class="file-list">
            <table>
                <tr>
                    <th>File</th>
                    <th>Size</th>
                    <th>Actions</th>
                </tr>
                {file_rows}
            </table>
        </div>
        
        <div id="previewContainer" class="preview-container">
            <button onclick="closePreview()" class="close-btn">Close</button>
            <h3 id="previewTitle">File Preview</h3>
            <pre id="previewContent"></pre>
        </div>
    </div>
    
    <script>
        /* Function to decode Base64 string */
        function decodeBase64(str) {{
            /* Convert Base64 to raw binary data held in a string */
            const decoded = atob(str);
            /* Convert raw binary to UTF-8 text */
            return decodeURIComponent(
                Array.from(decoded)
                    .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                    .join('')
            );
        }}
        
        /* Function to show preview from data attributes */
        function showPreviewFromData(button) {{
            const path = button.getAttribute('data-path');
            const contentB64 = button.getAttribute('data-content-b64');
            
            const previewContainer = document.getElementById('previewContainer');
            const previewTitle = document.getElementById('previewTitle');
            const previewContent = document.getElementById('previewContent');
            
            /* Set preview title and content */
            previewTitle.textContent = 'Preview: ' + path;
            
            /* Decode the Base64 content */
            const content = decodeBase64(contentB64);
            previewContent.textContent = content;
            
            previewContainer.style.display = 'block';
            
            /* Scroll to the preview */
            previewContainer.scrollIntoView({{ behavior: 'smooth' }});
        }}
        
        /* Function to close the preview */
        function closePreview() {{
            document.getElementById('previewContainer').style.display = 'none';
        }}
    </script>
</body>
</html>"""

    def extract_metadata(self, data: Path) -> Dict[str, Any]:
        """Extract metadata from the given directory.

        Args:
            data: The Path object to extract metadata from.

        Returns:
            A dictionary of metadata.
        """
        # Either use the original path or load it from the artifact store
        if os.path.exists(str(data)):
            directory_path = data
        else:
            # If we're extracting metadata from an already saved artifact
            directory_path = self.load(Path)

        # Count files and directories
        file_count = sum(1 for _ in directory_path.glob("**/*") if _.is_file())
        dir_count = sum(1 for _ in directory_path.glob("**/*") if _.is_dir())

        # Get total size
        total_size = sum(
            item.stat().st_size
            for item in directory_path.glob("**/*")
            if item.is_file()
        )

        # Get file extensions
        file_extensions: Dict[str, int] = {}
        for item in directory_path.glob("**/*"):
            if item.is_file() and item.suffix:
                ext = item.suffix.lower()
                file_extensions[ext] = file_extensions.get(ext, 0) + 1

        return {
            "path": str(data),
            "file_count": file_count,
            "directory_count": dir_count,
            "total_size_bytes": total_size,
            "file_extensions": file_extensions,
        }

    def _get_mime_type(self, file_path: str) -> str:
        """Get the MIME type for a given file path.

        Args:
            file_path: The file path to get the MIME type for.

        Returns:
            The MIME type for the given file path.
        """
        # Map of common file extensions to MIME types
        mime_types = {
            ".txt": "text/plain",
            ".log": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".json": "application/json",
            ".yaml": "text/yaml",
            ".yml": "text/yaml",
            ".html": "text/html",
            ".htm": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".py": "text/x-python",
            ".diff": "text/plain",
            ".patch": "text/plain",
            ".xml": "application/xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".pdf": "application/pdf",
        }

        # Get file extension and convert to lowercase
        ext = Path(file_path).suffix.lower()

        # Return the corresponding MIME type or default to octet-stream
        return mime_types.get(ext, "application/octet-stream")
