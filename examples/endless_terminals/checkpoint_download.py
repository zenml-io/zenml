"""Download a bounded adapter archive through the native authenticated proxy."""

import errno
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import time
from http.client import IncompleteRead
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_BUDGET_SECONDS = 300
READ_TIMEOUT_SECONDS = 60


class NoRedirect(HTTPRedirectHandler):
    """Reject redirects so the API key cannot follow another origin."""

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        """Reject the redirect instead of forwarding credentials.

        Args:
            req: Original authenticated request.
            fp: Original response stream.
            code: Redirect status code.
            msg: Response reason.
            headers: Response headers.
            newurl: Redirect destination that will not be requested.
        """
        return None


def download_archive(
    url: str, output: Path, base_url: str, api_key: str
) -> None:
    """Fetch and safely extract an archive from the training API origin.

    Args:
        url: Archive URL returned by the training service.
        output: Empty destination directory.
        base_url: Already validated training origin.
        api_key: Per-run credential.

    Raises:
        ValueError: The URL, archive paths, or sizes violate the contract.
        OSError: A download fails after bounded transient retries.
        IncompleteRead: An incomplete response persists after bounded retries.
        TimeoutError: Reads time out or the shared download budget expires.
        tarfile.TarError: The archive cannot be read safely.
    """  # noqa: DOC503 - Archive parsing errors propagate from tarfile.
    source, origin = urlsplit(url), urlsplit(base_url)
    if (
        (source.scheme, source.hostname, source.port)
        != (origin.scheme, origin.hostname, origin.port)
        or source.username
        or source.password
        or source.fragment
    ):
        raise ValueError("Checkpoint archive must use the training origin")
    if any(output.iterdir()):
        raise ValueError("Checkpoint destination must be empty")
    request = Request(url, headers={"X-API-Key": api_key})
    deadline = time.monotonic() + DOWNLOAD_BUDGET_SECONDS
    for attempt in range(DOWNLOAD_ATTEMPTS):
        # A failed response must never contribute bytes to the next attempt.
        with tempfile.TemporaryFile() as downloaded:
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Checkpoint download budget exhausted")
                with build_opener(NoRedirect()).open(
                    request, timeout=min(READ_TIMEOUT_SECONDS, remaining)
                ) as response:
                    size = 0
                    while chunk := response.read(1024 * 1024):
                        if time.monotonic() >= deadline:
                            raise TimeoutError(
                                "Checkpoint download budget exhausted"
                            )
                        size += len(chunk)
                        if size > MAX_ARCHIVE_BYTES:
                            raise ValueError(
                                "Checkpoint archive exceeds download limit"
                            )
                        downloaded.write(chunk)
            except (OSError, IncompleteRead) as error:
                cause = error.reason if isinstance(error, URLError) else error
                transient = isinstance(
                    cause, (TimeoutError, ConnectionError, IncompleteRead)
                ) or (
                    isinstance(cause, OSError)
                    and cause.errno
                    in {errno.ETIMEDOUT, errno.ENETUNREACH, errno.EHOSTUNREACH}
                )
                if (
                    not transient
                    or attempt + 1 == DOWNLOAD_ATTEMPTS
                    or time.monotonic() >= deadline
                ):
                    raise
                continue
            downloaded.seek(0)
            with (
                tempfile.TemporaryDirectory(dir=output.parent) as staged,
                tarfile.open(fileobj=downloaded, mode="r:*") as archive,
            ):
                members: list[tarfile.TarInfo] = []
                paths: set[PurePosixPath] = set()
                total = 0
                for member in archive:
                    path = PurePosixPath(member.name)
                    total += member.size
                    if (
                        path.is_absolute()
                        or ".." in path.parts
                        or (not path.parts and not member.isdir())
                        or path in paths
                        or not (member.isfile() or member.isdir())
                        or member.size < 0
                        or total > MAX_ARCHIVE_BYTES
                        or len(members) >= 10000
                    ):
                        raise ValueError(
                            "Unsafe or oversized checkpoint archive"
                        )
                    paths.add(path)
                    members.append(member)
                for member in members:
                    target = Path(staged).joinpath(
                        *PurePosixPath(member.name).parts
                    )
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        content = archive.extractfile(member)
                        if content is None:
                            raise ValueError("Missing checkpoint file content")
                        with content, target.open("xb") as destination:
                            shutil.copyfileobj(content, destination)
                Path(staged).replace(output)
            return


def checkpoint_coordinates(checkpoint: str) -> tuple[str, str]:
    """Resolve a sampler path into the pinned SkyRL archive route fields.

    SkyRL returns two path components while Tinker's path convenience method
    requires three. Its explicit archive method supports SkyRL's route.

    Args:
        checkpoint: Short SkyRL or canonical sampler checkpoint path.

    Returns:
        Model ID and bare sampler checkpoint ID.

    Raises:
        ValueError: The path is not a bounded sampler checkpoint identifier.
    """
    match = re.fullmatch(
        r"tinker://([A-Za-z0-9_-]{1,255})/(?:sampler_weights/)?([A-Za-z0-9_-]{1,255})",
        checkpoint,
    )
    if match is None:
        raise ValueError("Invalid SkyRL sampler checkpoint path")
    return match.group(1), match.group(2)


def main() -> None:
    """Resolve a Tinker checkpoint and download it using the per-run key."""
    import tinker

    checkpoint, destination, base_url = sys.argv[1:]
    api_key = os.environ["TINKER_API_KEY"]
    model_id, checkpoint_id = checkpoint_coordinates(checkpoint)
    client = tinker.ServiceClient(base_url=base_url, api_key=api_key)
    result = (
        client.create_rest_client()
        .get_checkpoint_archive_url(model_id, checkpoint_id)
        .result(timeout=60)
    )
    download_archive(result.url, Path(destination), base_url, api_key)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # The parent suppresses SDK stderr; retain a bounded, redacted cause.
        if len(sys.argv) == 4:
            message = str(error).replace(
                os.environ.get("TINKER_API_KEY", "[NO_KEY]"), "[REDACTED]"
            )
            (
                Path(sys.argv[2]).parent / "checkpoint-download-error.json"
            ).write_text(
                json.dumps(
                    {"type": type(error).__name__, "message": message[:4096]}
                )
                + "\n"
            )
        raise
