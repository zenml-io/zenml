import os
import base64
import tarfile
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, ClassVar, Dict, Tuple, Type

from zenml.enums import ArtifactType, VisualizationType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.types import HTMLString


class PathMaterializer(BaseMaterializer):
    """Materializer for Path objects that provides downloadable file visualizations."""
    
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
        """Create HTML visualizations for each file with download buttons.
        
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
            
            # Create individual HTML files for each file
            for file_path in sorted(directory_path.glob('**/*')):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(directory_path))
                    try:
                        # Read file content
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        
                        # Create base64 encoded data for download
                        file_base64 = base64.b64encode(file_content).decode('utf-8')
                        
                        # Create simple HTML with download button
                        filename = os.path.basename(rel_path)
                        html_content = self._create_download_html(filename, file_base64)
                        
                        # Save HTML visualization
                        vis_uri = os.path.join(self.uri, f"{rel_path}.html")
                        with self.artifact_store.open(vis_uri, "w") as f:
                            f.write(html_content)
                        visualizations[vis_uri] = VisualizationType.HTML
                        
                        # For common text formats, also add their native visualization
                        if self._is_text_file(file_path):
                            text_content = file_content.decode('utf-8', errors='replace')
                            if file_path.suffix.lower() in ('.md', '.markdown'):
                                md_uri = os.path.join(self.uri, f"{rel_path}.md")
                                with self.artifact_store.open(md_uri, "w") as f:
                                    f.write(text_content)
                                visualizations[md_uri] = VisualizationType.MARKDOWN
                            
                            elif file_path.suffix.lower() in ('.csv'):
                                csv_uri = os.path.join(self.uri, f"{rel_path}.csv")
                                with self.artifact_store.open(csv_uri, "w") as f:
                                    f.write(text_content)
                                visualizations[csv_uri] = VisualizationType.CSV
                            
                            elif file_path.suffix.lower() in ('.json'):
                                json_uri = os.path.join(self.uri, f"{rel_path}.json")
                                with self.artifact_store.open(json_uri, "w") as f:
                                    f.write(text_content)
                                visualizations[json_uri] = VisualizationType.JSON
                    
                    except Exception as e:
                        print(f"Error processing {rel_path}: {str(e)}")
            
        except Exception as e:
            # If something goes wrong, create a simple error visualization
            error_uri = os.path.join(self.uri, "error.md")
            with self.artifact_store.open(error_uri, "w") as f:
                f.write(f"# Error Creating Visualization\n\n{str(e)}")
            visualizations[error_uri] = VisualizationType.MARKDOWN
        
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
    
    def _create_download_html(self, filename: str, file_base64: str) -> str:
        """Create a simple HTML page with a download button.
        
        Args:
            filename: Name of the file
            file_base64: Base64 encoded file content
            
        Returns:
            HTML content
        """
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Download {filename}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; text-align: center; }}
        .download-btn {{ 
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 15px 25px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 20px;
        }}
        .download-btn:hover {{ background-color: #45a049; }}
        h1 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Download File: {filename}</h1>
    <button class="download-btn" onclick="downloadFile()">Download {filename}</button>
    
    <script>
        function downloadFile() {{
            const a = document.createElement('a');
            a.href = 'data:application/octet-stream;base64,{file_base64}';
            a.download = '{filename}';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }}
        
        // Auto-trigger download when page loads
        window.onload = function() {{
            // Uncomment the next line to auto-download when page is opened
            // downloadFile();
        }};
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