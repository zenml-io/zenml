#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Archivable mixin."""

import io
import tarfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import IO, Any, Dict

from zenml.io import fileio


class Archivable(ABC):
    """Archivable mixin class."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the object.

        Args:
            *args: Unused args for subclasses.
            **kwargs: Unused keyword args for subclasses.
        """
        self._extra_files: Dict[str, str] = {}

    def add_file(self, source: str, destination: str) -> None:
        """Adds a file to the archive.

        Args:
            source: The source of the file to add. This can either be a path
                or the file content.
            destination: The path inside the archive where the file
                should be added.
        """
        if fileio.exists(source):
            with fileio.open(source) as f:
                self._extra_files[destination] = f.read()
        else:
            self._extra_files[destination] = source

    def add_directory(self, source: str, destination: str) -> None:
        """Adds a directory to the archive.

        Args:
            source: Path to the directory.
            destination: The path inside the build context where the directory
                should be added.

        Raises:
            ValueError: If `source` does not point to a directory.
        """
        if not fileio.isdir(source):
            raise ValueError(
                f"Can't add directory {source} to the build context as it "
                "does not exist or is not a directory."
            )

        for dir, _, files in fileio.walk(source):
            dir_path = Path(fileio.convert_to_str(dir))
            for file_name in files:
                file_name = fileio.convert_to_str(file_name)
                file_source = dir_path / file_name
                file_destination = (
                    Path(destination)
                    / dir_path.relative_to(source)
                    / file_name
                )

                with file_source.open("r") as f:
                    self._extra_files[file_destination.as_posix()] = f.read()

    def write_archive(
        self, output_file: IO[bytes], use_gzip: bool = True
    ) -> None:
        """Writes an archive of the build context to the given file.

        Args:
            output_file: The file to write the archive to.
            use_gzip: Whether to use `gzip` to compress the file.
        """
        files = self.get_files()
        extra_files = self.get_extra_files()

        if use_gzip:
            from gzip import GzipFile

            # We don't use the builtin gzip functionality of the `tarfile`
            # library as that one includes the tar filename and creation
            # timestamp in the archive which causes the hash of the resulting
            # file to be different each time. We use this hash to avoid
            # duplicate uploads, which is why we pass emtpy values for filename
            # and mtime here.
            fileobj = GzipFile(
                filename="", mode="wb", fileobj=output_file, mtime=0.0
            )
        else:
            fileobj = output_file

        with tarfile.open(mode="w", fileobj=fileobj) as tf:
            for archive_path, file_path in files.items():
                if archive_path in extra_files:
                    continue

                if info := tf.gettarinfo(file_path, arcname=archive_path):
                    if info.isfile():
                        with open(file_path, "rb") as f:
                            tf.addfile(info, f)
                    else:
                        tf.addfile(info, None)

            for archive_path, contents in extra_files:
                info = tarfile.TarInfo(archive_path)
                contents_encoded = contents.encode("utf-8")
                info.size = len(contents_encoded)
                tf.addfile(info, io.BytesIO(contents_encoded))

        output_file.seek(0)

    @abstractmethod
    def get_files(self) -> Dict[str, str]:
        """Gets all regular files that should be included in the archive.

        Returns:
            A dict {path_in_archive: path_on_filesystem} for all regular files
            in the archive.
        """

    def get_extra_files(self) -> Dict[str, str]:
        """Gets all extra files that should be included in the archive.

        Returns:
            A dict {path_in_archive: file_content} for all extra files in the
            archive.
        """
        return self._extra_files.copy()
