"""Process-local in-memory registry for serving runtime.

This module provides a simple, thread-safe in-memory registry used to store:
- Raw Python objects keyed by artifact URIs
- A lightweight in-memory filesystem abstraction for paths (files/dirs)

The registry is intentionally process-local and ephemeral. It is only used
when serving runtime is active and an environment variable is set to enable
in-memory behavior.
"""

import io
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

_lock = threading.RLock()


@dataclass
class _MemoryFS:
    files: Dict[str, bytes] = field(default_factory=dict)
    dirs: Set[str] = field(default_factory=set)

    def _normalize(self, path: str) -> str:
        # Keep it simple: collapse backslashes and redundant slashes
        return path.replace("\\", "/")

    def open_read(self, path: str) -> io.BytesIO:
        path = self._normalize(path)
        with _lock:
            if path not in self.files:
                raise FileNotFoundError(path)
            data = self.files[path]
        return io.BytesIO(data)

    def open_write(self, path: str, append: bool = False) -> "_WriteBuffer":
        path = self._normalize(path)
        return _WriteBuffer(self, path, append=append)

    def exists(self, path: str) -> bool:
        path = self._normalize(path)
        with _lock:
            return path in self.files or path in self.dirs

    def isdir(self, path: str) -> bool:
        path = self._normalize(path)
        with _lock:
            return path in self.dirs

    def listdir(self, path: str) -> List[str]:
        path = self._normalize(path).rstrip("/")
        n = len(path)
        entries: Set[str] = set()
        with _lock:
            for d in self.dirs:
                if d.startswith(path + "/"):
                    rel = d[n + 1 :]
                    if "/" not in rel and rel:
                        entries.add(rel)
            for f in self.files:
                if f.startswith(path + "/"):
                    rel = f[n + 1 :]
                    part = rel.split("/", 1)[0]
                    if part:
                        entries.add(part)
        return sorted(entries)

    def makedirs(self, path: str) -> None:
        path = self._normalize(path).rstrip("/")
        parts = path.split("/")
        cur = ""
        with _lock:
            for p in parts:
                cur = f"{cur}/{p}" if cur else p
                self.dirs.add(cur)

    def mkdir(self, path: str) -> None:
        path = self._normalize(path).rstrip("/")
        with _lock:
            self.dirs.add(path)

    def remove(self, path: str) -> None:
        path = self._normalize(path)
        with _lock:
            self.files.pop(path, None)

    def rmtree(self, path: str) -> None:
        path = self._normalize(path).rstrip("/")
        with _lock:
            to_delete_files = [
                p for p in self.files if p.startswith(path + "/") or p == path
            ]
            for p in to_delete_files:
                self.files.pop(p, None)
            to_delete_dirs = [
                d for d in self.dirs if d.startswith(path + "/") or d == path
            ]
            for d in to_delete_dirs:
                self.dirs.discard(d)

    def rename(self, src: str, dst: str, overwrite: bool = False) -> None:
        src = self._normalize(src)
        dst = self._normalize(dst)
        with _lock:
            if src in self.files:
                if not overwrite and dst in self.files:
                    return
                self.files[dst] = self.files.pop(src)
            elif src in self.dirs:
                # Move dir: update all children
                mapping: List[Tuple[str, str]] = []
                for d in list(self.dirs):
                    if d == src or d.startswith(src + "/"):
                        mapping.append((d, d.replace(src, dst, 1)))
                for f in list(self.files):
                    if f == src or f.startswith(src + "/"):
                        mapping.append((f, f.replace(src, dst, 1)))
                for s, t in mapping:
                    if s in self.files:
                        self.files[t] = self.files.pop(s)
                    if s in self.dirs:
                        self.dirs.add(t)
                        self.dirs.discard(s)

    def copyfile(self, src: str, dst: str, overwrite: bool = False) -> None:
        src = self._normalize(src)
        dst = self._normalize(dst)
        with _lock:
            if src not in self.files:
                return
            if not overwrite and dst in self.files:
                return
            self.files[dst] = bytes(self.files[src])

    def stat(self, path: str) -> Dict[str, int]:
        path = self._normalize(path)
        with _lock:
            size = len(self.files.get(path, b""))
        return {"size": size}

    def size(self, path: str) -> Optional[int]:
        path = self._normalize(path)
        with _lock:
            return (
                len(self.files.get(path, b"")) if path in self.files else None
            )

    def walk(self, top: str) -> Iterable[Tuple[str, List[str], List[str]]]:
        top = self._normalize(top).rstrip("/")
        with _lock:
            # BFS over dirs
            queue = [top]
            visited: Set[str] = set()
            while queue:
                d = queue.pop(0)
                if d in visited:
                    continue
                visited.add(d)
                dirs = []
                files = []
                for entry in self.listdir(d):
                    full = f"{d}/{entry}" if d else entry
                    if full in self.dirs:
                        dirs.append(entry)
                        queue.append(full)
                    elif full in self.files:
                        files.append(entry)
                yield d, dirs, files


class _WriteBuffer(io.BytesIO):
    def __init__(self, fs: _MemoryFS, path: str, append: bool) -> None:
        self._fs = fs
        self._path = path
        self._append = append
        super().__init__(fs.files.get(path, b"") if append else b"")

    def close(self) -> None:
        with _lock:
            self._fs.files[self._path] = self.getvalue()
        super().close()


_fs = _MemoryFS()
_objects: Dict[str, Any] = {}


def put_object(uri: str, obj: Any) -> None:
    with _lock:
        _objects[uri] = obj


def has_object(uri: str) -> bool:
    with _lock:
        return uri in _objects


def get_object(uri: str) -> Any:
    with _lock:
        return _objects[uri]


def del_object(uri: str) -> None:
    """Delete an object from the registry if present."""
    with _lock:
        _objects.pop(uri, None)


# Filesystem adapter helpers
def fs_open(path: str, mode: str = "r") -> io.BytesIO | io.TextIOWrapper:
    """Open a file at the given path.

    Args:
        path: The path of the file to open.
        mode: The mode to open the file in.

    Returns:
        The opened file.
    """
    if "r" in mode:
        return _fs.open_read(path)
    append = "a" in mode
    return _fs.open_write(path, append=append)


def fs_exists(path: str) -> bool:
    """Check if a path exists.

    Args:
        path: The path to check.

    Returns:
        `True` if the path exists.
    """
    return _fs.exists(path)


def fs_isdir(path: str) -> bool:
    """Check if a path is a directory.

    Args:
        path: The path to check.

    Returns:
        `True` if the path is a directory.
    """
    return _fs.isdir(path)


def fs_listdir(path: str) -> List[str]:
    """List the contents of a directory.

    Args:
        path: The path to the directory.

    Returns:
        A list of the contents of the directory.
    """
    return _fs.listdir(path)


def fs_makedirs(path: str) -> None:
    """Make a directory at the given path.

    Args:
        path: The path to the directory.
    """
    _fs.makedirs(path)


def fs_mkdir(path: str) -> None:
    """Make a directory at the given path.

    Args:
        path: The path to the directory.
    """
    _fs.mkdir(path)


def fs_remove(path: str) -> None:
    """Remove a file or directory at the given path.

    Args:
        path: The path to the file or directory.
    """
    _fs.remove(path)


def fs_rename(src: str, dst: str, overwrite: bool = False) -> None:
    """Rename a file or directory.

    Args:
        src: The source path.
        dst: The destination path.
        overwrite: Whether to overwrite the destination file if it exists.
    """
    _fs.rename(src, dst, overwrite)


def fs_rmtree(path: str) -> None:
    """Remove a directory at the given path.

    Args:
        path: The path to the directory.
    """
    _fs.rmtree(path)


def fs_copyfile(src: str, dst: str, overwrite: bool = False) -> None:
    """Copy a file from the source to the destination.

    Args:
        src: The source path.
        dst: The destination path.
        overwrite: Whether to overwrite the destination file if it exists.
    """
    _fs.copyfile(src, dst, overwrite)


def fs_stat(path: str) -> Dict[str, int]:
    """Return the stat descriptor for a given file path.

    Args:
        path: The path to the file.

    Returns:
        The stat descriptor.
    """
    return _fs.stat(path)


def fs_size(path: str) -> Optional[int]:
    """Get the size of a file in bytes.

    Args:
        path: The path to the file.

    Returns:
        The size of the file in bytes.
    """
    return _fs.size(path)


def fs_walk(top: str) -> Iterable[Tuple[str, List[str], List[str]]]:
    """Walk the filesystem.

    Args:
        top: The path to the directory.
    """
    return _fs.walk(top)
