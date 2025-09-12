"""In-memory artifact store used for ephemeral runtime scenarios.

This artifact store implements the BaseArtifactStore interface purely in
memory using a process-local registry. It is not wired into stacks by default
and is intended for explicit, programmatic use or future opt-in flavors.
"""

from typing import (
    Any,
    ClassVar,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    cast,
)

from pydantic import Field

from zenml.artifact_stores.base_artifact_store import (
    BaseArtifactStore,
    BaseArtifactStoreConfig,
    BaseArtifactStoreFlavor,
    PathType,
)
from zenml.deployers.serving import _in_memory_registry as reg
from zenml.enums import StackComponentType


class InMemoryArtifactStoreConfig(BaseArtifactStoreConfig):
    """Config for the in-memory artifact store."""

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {"memory://"}
    path: str = Field(default="memory://runtime", description="In-memory root")


class InMemoryArtifactStore(BaseArtifactStore):
    """A process-local in-memory artifact store."""

    @property
    def config(self) -> InMemoryArtifactStoreConfig:
        """Returns the `InMemoryArtifactStoreConfig` config.

        Returns:
            The configuration.
        """
        return cast(InMemoryArtifactStoreConfig, self._config)

    @property
    def path(self) -> str:
        """Returns the path to the artifact store.

        For in-memory storage, this returns the memory:// root path.

        Returns:
            The artifact store path.
        """
        return "memory://runtime"

    # Implement filesystem-like methods against the registry FS
    def open(self, path: PathType, mode: str = "r") -> Any:
        """Open a file at the given path.

        Args:
            path: The path of the file to open.
            mode: The mode to open the file.

        Returns:
            The file object.
        """
        # BaseArtifactStore wrapper will already sanitize path
        buf = reg.fs_open(str(path), mode)
        if "b" in mode:
            return buf
        import io
        return io.TextIOWrapper(buf, encoding="utf-8")

    def copyfile(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Copy a file from the source to the destination.

        Args:
            src: The source path.
            dst: The destination path.
            overwrite: Whether to overwrite the destination file if it exists.
        """
        reg.fs_copyfile(str(src), str(dst), overwrite)

    def exists(self, path: PathType) -> bool:
        """Checks if a path exists.

        Args:
            path: The path to check.

        Returns:
            `True` if the path exists.
        """
        return reg.fs_exists(str(path))

    def glob(self, pattern: PathType) -> List[PathType]:
        """Returns a list of files matching a given pattern.

        Args:
            pattern: The pattern to match.

        Returns:
            A list of files matching the pattern.
        """
        # Minimal glob: return direct children matching exact names
        # For production, integrate a proper glob if needed
        import fnmatch

        pattern = str(pattern)
        parent = pattern.split("*", 1)[0].rstrip("/")
        candidates: List[str] = []
        if reg.fs_isdir(parent):
            for entry in reg.fs_listdir(parent):
                candidates.append(f"{parent}/{entry}")
        else:
            # fallback: single file
            candidates.append(parent)
        return [c for c in candidates if fnmatch.fnmatch(c, pattern)]

    def isdir(self, path: PathType) -> bool:
        """Returns whether the given path points to a directory.

        Args:
            path: The path to check.

        Returns:
            `True` if the path points to a directory.
        """
        return reg.fs_isdir(str(path))

    def listdir(self, path: PathType) -> List[PathType]:
        """Returns a list of files under a given directory in the filesystem.

        Args:
            path: The path to the directory.

        Returns:
            A list of files under the given directory.
        """
        return [str(f) for f in reg.fs_listdir(str(path))]

    def makedirs(self, path: PathType) -> None:
        """Make a directory at the given path, recursively creating parents.

        Args:
            path: The path to the directory.
        """
        reg.fs_makedirs(str(path))

    def mkdir(self, path: PathType) -> None:
        """Make a directory at the given path.

        Args:
            path: The path to the directory.
        """
        reg.fs_mkdir(str(path))

    def remove(self, path: PathType) -> None:
        """Remove a file or directory at the given path.

        Args:
            path: The path to the file or directory.
        """
        reg.fs_remove(str(path))

    def rename(
        self, src: PathType, dst: PathType, overwrite: bool = False
    ) -> None:
        """Rename a file or directory.

        Args:
            src: The source path.
            dst: The destination path.
            overwrite: Whether to overwrite the destination file if it exists.
        """
        reg.fs_rename(str(src), str(dst), overwrite)

    def rmtree(self, path: PathType) -> None:
        """Remove a directory at the given path.

        Args:
            path: The path to the directory.
        """
        reg.fs_rmtree(str(path))

    def stat(self, path: PathType) -> Any:
        """Return the stat descriptor for a given file path.

        Args:
            path: The path to the file.

        Returns:
            The stat descriptor.
        """
        return reg.fs_stat(str(path))

    def size(self, path: PathType) -> Optional[int]:
        """Get the size of a file in bytes.

        Args:
            path: The path to the file.

        Returns:
            The size of the file in bytes.
        """
        return reg.fs_size(str(path))

    def walk(
        self,
        top: PathType,
        topdown: bool = True,
        onerror: Optional[Any] = None,
    ) -> Iterable[Tuple[PathType, List[PathType], List[PathType]]]:
        """Walk the filesystem.

        Args:
            top: The path to the directory.
            topdown: Whether to walk the filesystem topdown.
            onerror: The error to raise if an error occurs.
        """
        # Ignore order flags for now
        for root, dirs, files in reg.fs_walk(str(top)):
            yield str(root), [str(d) for d in dirs], [str(f) for f in files]


class InMemoryArtifactStoreFlavor(BaseArtifactStoreFlavor):
    """Flavor for the in-memory artifact store."""

    @property
    def type(self) -> StackComponentType:
        """Returns the type of the artifact store.

        Returns:
            The type of the artifact store.
        """
        return StackComponentType.ARTIFACT_STORE

    @property
    def name(self) -> str:
        """Returns the name of the artifact store.

        Returns:
            The name of the artifact store.
        """
        return "in_memory"

    @property
    def config_class(self) -> Type[BaseArtifactStoreConfig]:
        """Returns the config class for the artifact store.

        Returns:
            The config class for the artifact store.
        """
        return InMemoryArtifactStoreConfig

    @property
    def implementation_class(self) -> Type["BaseArtifactStore"]:
        """Returns the implementation class for the artifact store.

        Returns:
            The implementation class for the artifact store.
        """
        return InMemoryArtifactStore
