# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archive object storage built from the server's archive settings.

The URI names a bucket prefix or a local directory, for example
``s3://bucket/zenml-archive``. By default no credentials are configured
here: the artifact store flavor that owns the URI's scheme is instantiated
without any, so its SDK uses the ambient credential chain of the server
process, such as an IAM role, workload identity, or managed identity. A
server may instead name a ZenML service connector, which that artifact store
connects and refreshes exactly as a registered component would.

Archive I/O never goes through ``zenml.io.fileio``. That module dispatches on
a process-wide filesystem registry, and outside the server every artifact
store instantiation re-registers its scheme with its own credentials. This
wrapper keeps one artifact store instance and calls its methods directly.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4, uuid5

from zenml.artifact_stores.base_artifact_store import (
    BaseArtifactStore,
    BaseArtifactStoreConfig,
)
from zenml.enums import StackComponentType
from zenml.exceptions import ExecutionRetentionUnavailableError
from zenml.logger import get_logger
from zenml.stack.flavor import Flavor
from zenml.utils.time_utils import utc_now

logger = get_logger(__name__)

# Stable identity so log lines and path sanitization name the same store.
_ARCHIVE_STORE_NAMESPACE = UUID("5c1f3a4e-9b2d-4c6e-8f7a-0d1e2b3c4a5f")

# S3 exposes per-request transport controls through its artifact-store config.
# These do not bound a complete multipart archive operation, but they prevent
# one connection or socket read from waiting forever during shutdown.
_S3_CONNECT_TIMEOUT_SECONDS = 10
_S3_READ_TIMEOUT_SECONDS = 60
_S3_TOTAL_ATTEMPTS = 3


def _artifact_store_flavors() -> List[Flavor]:
    """List every built-in and integration artifact store flavor.

    Returns:
        Instantiated flavor descriptors.
    """
    from zenml.stack.flavor_registry import FlavorRegistry

    registry = FlavorRegistry()
    flavors = [
        flavor_class()
        for flavor_class in [
            *registry.builtin_flavors,
            *registry.integration_flavors,
        ]
    ]
    return [
        flavor
        for flavor in flavors
        if flavor.type == StackComponentType.ARTIFACT_STORE
    ]


def _flavor_for(uri: str) -> Flavor:
    """Select the artifact store flavor that owns the URI's scheme.

    Args:
        uri: Archive root URI or local directory.

    Returns:
        The matching flavor, or the local flavor for a plain path.

    Raises:
        ValueError: No installed flavor supports the URI's scheme.
    """
    flavors = _artifact_store_flavors()
    matches = [
        (len(scheme), flavor)
        for flavor in flavors
        if issubclass(flavor.config_class, BaseArtifactStoreConfig)
        for scheme in flavor.config_class.SUPPORTED_SCHEMES
        if scheme and uri.startswith(scheme)
    ]
    if matches:
        return max(matches, key=lambda match: match[0])[1]
    if "://" not in uri:
        return next(flavor for flavor in flavors if flavor.name == "local")
    raise ValueError(
        f"No artifact store flavor supports the archive URI scheme of '{uri}'."
    )


class ArchiveStorage:
    """Read and write archive objects under one root URI."""

    def __init__(self, artifact_store: BaseArtifactStore) -> None:
        """Wrap an artifact store rooted at the archive URI.

        Args:
            artifact_store: Store whose path is the archive root.
        """
        self.artifact_store = artifact_store
        self._former_stores: Dict[str, BaseArtifactStore] = {}

    @classmethod
    def from_uri(
        cls, uri: str, connector_id: Optional[UUID] = None
    ) -> "ArchiveStorage":
        """Instantiate the artifact store flavor that owns an archive URI.

        Without a connector the store authenticates with the server process's
        ambient credentials. A connector ID hands it a ZenML service
        connector instead, which the artifact store refreshes on its own once
        the credentials expire.

        Args:
            uri: Archive root URI or local directory.
            connector_id: Service connector to authenticate with, or None to
                use ambient credentials.

        Returns:
            Storage rooted at the URI.

        Raises:
            ExecutionRetentionUnavailableError: The URI is unsupported or its
                artifact store cannot be created.
        """  # noqa: DOC503
        root = uri.rstrip("/")
        try:
            flavor = _flavor_for(root)
            implementation = flavor.implementation_class
            if not issubclass(implementation, BaseArtifactStore):
                raise TypeError(f"Flavor {flavor.name} is no artifact store.")
            config_values: Dict[str, Any] = {"path": root}
            if root.startswith("s3://"):
                if "config_kwargs" not in flavor.config_class.model_fields:
                    raise TypeError(
                        "The S3 archive flavor does not expose transport "
                        "configuration."
                    )
                config_values["config_kwargs"] = {
                    "connect_timeout": _S3_CONNECT_TIMEOUT_SECONDS,
                    "read_timeout": _S3_READ_TIMEOUT_SECONDS,
                    "retries": {
                        "mode": "standard",
                        "total_max_attempts": _S3_TOTAL_ATTEMPTS,
                    },
                }
            now = utc_now()
            store = implementation(
                name="execution-archive",
                id=uuid5(_ARCHIVE_STORE_NAMESPACE, root),
                config=flavor.config_class(**config_values),
                flavor=flavor.name,
                type=StackComponentType.ARTIFACT_STORE,
                user=None,
                created=now,
                updated=now,
                connector=connector_id,
                connector_requirements=flavor.service_connector_requirements,
                register_filesystem=False,
            )
        except Exception as error:
            raise ExecutionRetentionUnavailableError(
                "The execution archive URI cannot be used; check "
                "ZENML_SERVER_ARCHIVE__URI, ZENML_SERVER_ARCHIVE__CONNECTOR_ID"
                " and the server's installed integrations."
            ) from error
        return cls(store)

    @property
    def root(self) -> str:
        """Archive root URI.

        Returns:
            The artifact store path without a trailing slash.
        """
        return self.artifact_store.path.rstrip("/")

    def object_uri(
        self, project_id: UUID, run_id: UUID, bundle_id: UUID
    ) -> str:
        """Name the object holding one run's archived detail.

        Args:
            project_id: Owning project.
            run_id: Archived run.
            bundle_id: Bundle row identity.

        Returns:
            Object URI below the archive root.
        """
        return f"{self.root}/{project_id}/{run_id}/{bundle_id}.json.gz"

    @staticmethod
    def root_of(uri: str) -> str:
        """Recover the archive root an object URI was written under.

        Args:
            uri: URI produced by `object_uri`.

        Returns:
            The root, without the project, run, and object segments.
        """
        return uri.rsplit("/", 3)[0]

    def write(self, uri: str, data: bytes) -> None:
        """Write one uniquely named archive object.

        Args:
            uri: Object URI below the archive root.
            data: Object bytes.

        Raises:
            ExecutionRetentionUnavailableError: The write failed.
        """
        try:
            self.artifact_store.makedirs(uri.rsplit("/", 1)[0])
            with self.artifact_store.open(uri, "wb") as target:
                target.write(data)
        except Exception as error:
            raise ExecutionRetentionUnavailableError(
                "Archive storage rejected a write; retry later."
            ) from error

    def read(self, uri: str, max_bytes: int) -> bytes:
        """Read one object, stopping one byte past the expected size.

        Args:
            uri: Object URI below the archive root.
            max_bytes: Largest size the caller accepts.

        Returns:
            At most ``max_bytes + 1`` bytes, so callers detect oversized data.

        Raises:
            ExecutionRetentionUnavailableError: The object could not be read.
        """
        # A former root that cannot be instantiated reports its own
        # configuration error rather than a transient read failure.
        store = self._store_for(uri)
        try:
            with store.open(uri, "rb") as source:
                return bytes(source.read(max_bytes + 1))
        except Exception as error:
            raise ExecutionRetentionUnavailableError(
                "Archived execution detail storage is unavailable. Retry "
                "shortly."
            ) from error

    def _store_for(self, uri: str) -> BaseArtifactStore:
        """Select the artifact store whose root contains a recorded URI.

        Artifact stores refuse paths outside their own root, so an object
        written before ZENML_SERVER_ARCHIVE__URI changed is read through a
        store rooted where it was written, with the configured connector.

        Args:
            uri: Object URI recorded on a bundle row.

        Returns:
            This storage's store, or one rooted at the object's original root.
        """
        if uri.startswith(f"{self.root}/"):
            return self.artifact_store
        former_root = self.root_of(uri)
        if former_root not in self._former_stores:
            self._former_stores[former_root] = ArchiveStorage.from_uri(
                former_root, connector_id=self.artifact_store.connector
            ).artifact_store
        return self._former_stores[former_root]

    def remove(self, uri: str) -> None:
        """Remove an object that never became authoritative, if possible.

        Args:
            uri: Object URI below the archive root.
        """
        try:
            if self.artifact_store.exists(uri):
                self.artifact_store.remove(uri)
        except Exception as error:
            # An unreferenced object is harmless; the failure is only logged.
            logger.warning(
                "Could not remove unreferenced archive object (%s).",
                type(error).__name__,
            )

    def probe(self) -> bool:
        """Check that the root accepts a write and returns the same bytes.

        Returns:
            Whether a unique probe object round-tripped.
        """
        uri = f"{self.root}/_probes/{uuid4()}"
        nonce = uuid4().hex.encode()
        try:
            self.write(uri, nonce)
            return self.read(uri, len(nonce)) == nonce
        except ExecutionRetentionUnavailableError:
            return False
        finally:
            self.remove(uri)
