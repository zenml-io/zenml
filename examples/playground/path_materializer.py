import os
import base64
import tarfile
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, ClassVar, Dict, Tuple, Type

from zenml.enums import ArtifactType, VisualizationType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class PathMaterializer(BaseMaterializer):
    """Materializer for Path objects with direct download links."""
    
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
        with tarfile.open(archive_path_local, 'r:gz') as tar:
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
        with tarfile.open(archive_path, 'w:gz') as tar:
            # Get the current working directory
            original_dir = os.getcwd()
            try:
                # Change to the source directory to preserve relative paths
                os.chdir(str(data))
                
                # Add all files and directories
                for item in os.listdir('.'):
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
            for file_path in sorted(directory_path.glob('**/*')):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(directory_path))
                    size_bytes = file_path.stat().st_size
                    
                    # Read the file content
                    with open(file_path, 'rb') as f:
                        content_bytes = f.read()
                    content_b64 = base64.b64encode(content_bytes).decode('utf-8')
                    
                    # For text files, also get preview content
                    is_text = self._is_text_file(file_path)
                    preview_content = ""
                    if is_text:
                        preview_content = content_bytes.decode('utf-8', errors='replace')
                    
                    files_data.append({
                        'path': rel_path,
                        'filename': os.path.basename(rel_path),
                        'size': self._format_size(size_bytes),
                        'size_bytes': size_bytes,
                        'data': content_b64,
                        'is_text': is_text,
                        'preview': preview_content if is_text else ""
                    })
            
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
            '.txt', '.log', '.md', '.markdown', '.csv', '.json', '.yaml', '.yml',
            '.html', '.htm', '.css', '.js', '.py', '.java', '.c', '.cpp', '.h',
            '.sh', '.bat', '.cmd', '.xml', '.sql', '.diff', '.patch', '.gitignore'
        }
        
        if file_path.suffix.lower() in text_extensions:
            return True
        
        # For files without recognized extensions, try to detect if they're text
        try:
            # Read the first 1024 bytes and check if they're valid UTF-8
            with open(file_path, 'rb') as f:
                sample = f.read(1024)
            sample.decode('utf-8')
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
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
            
        return f"{size:.1f} {units[unit_index]}"
    
    def _create_direct_download_html(self, files_data: list) -> str:
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
            # Create a direct download link
            download_button = f"""
            <a href="data:application/octet-stream;base64,{file_info['data']}" 
               download="{file_info['filename']}" 
               class="download-btn">Download</a>"""
            
            # Add preview button if it's a text file
            preview_button = ""
            if file_info['is_text']:
                # Escape any quotes in the preview content to avoid breaking the JavaScript
                safe_preview = file_info['preview'].replace('"', '\\"').replace('\n', '\\n')
                preview_button = f"""
                <button onclick="showPreview('{file_info['path']}', `{safe_preview}`)" 
                        class="preview-btn">Preview</button>"""
            
            file_rows += f"""
            <tr>
                <td>{file_info['path']}</td>
                <td>{file_info['size']}</td>
                <td>
                    {download_button}
                    {preview_button}
                </td>
            </tr>"""
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Directory Contents</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .file-list {{ margin-top: 20px; border: 1px solid #ddd; border-radius: 5px; overflow: hidden; width: 100%; }}
        .file-list table {{ border-collapse: collapse; width: 100%; }}
        .file-list th {{ background-color: #f2f2f2; text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }}
        .file-list td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
        .file-list tr:hover {{ background-color: #f5f5f5; }}
        .download-btn {{ display: inline-block; padding: 8px 12px; background-color: #008CBA; color: white; 
                      border: none; border-radius: 4px; text-decoration: none; cursor: pointer; }}
        .preview-btn {{ padding: 8px 12px; background-color: #4CAF50; color: white; 
                     border: none; border-radius: 4px; cursor: pointer; margin-left: 5px; }}
        .preview-container {{ display: none; margin-top: 20px; padding: 15px; border: 1px solid #ddd; 
                          border-radius: 5px; max-height: 500px; overflow: auto; }}
        .preview-container pre {{ white-space: pre-wrap; font-family: monospace; margin: 0; }}
        .close-btn {{ float: right; background-color: #f44336; color: white; 
                   border: none; border-radius: 4px; padding: 5px 10px; cursor: pointer; }}
    </style>
</head>
<body>
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
    
    <script>
        // Function to show preview for text files
        function showPreview(path, content) {{
            const previewContainer = document.getElementById('previewContainer');
            const previewTitle = document.getElementById('previewTitle');
            const previewContent = document.getElementById('previewContent');
            
            // Set preview title and content
            previewTitle.textContent = 'Preview: ' + path;
            previewContent.textContent = content;
            previewContainer.style.display = 'block';
            
            // Scroll to the preview
            previewContainer.scrollIntoView({{ behavior: 'smooth' }});
        }}
        
        // Function to close the preview
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
        file_count = sum(1 for _ in directory_path.glob('**/*') if _.is_file())
        dir_count = sum(1 for _ in directory_path.glob('**/*') if _.is_dir())
        
        # Get total size
        total_size = sum(item.stat().st_size for item in directory_path.glob('**/*') if item.is_file())
        
        # Get file extensions
        file_extensions = {}
        for item in directory_path.glob('**/*'):
            if item.is_file() and item.suffix:
                ext = item.suffix.lower()
                file_extensions[ext] = file_extensions.get(ext, 0) + 1
        
        return {
            "path": str(data),
            "file_count": file_count,
            "directory_count": dir_count,
            "total_size_bytes": total_size,
            "file_extensions": file_extensions
        }