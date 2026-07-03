#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""SSH client wrapper around paramiko."""

import io
import os
import socket
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator, Optional

import paramiko

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.integrations.ssh.flavors.base import SSHConnectionConfigMixin

logger = get_logger(__name__)


@dataclass
class RemoteCommandResult:
    """Result of a remote command execution.

    Attributes:
        exit_code: Process exit code (0 = success).
        stdout: Captured standard output.
        stderr: Captured standard error (empty when combined with stdout).
    """

    exit_code: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class SSHClient:
    """Context-managed SSH client that wraps paramiko.

    Attributes:
        config: Connection configuration.
    """

    config: "SSHConnectionConfigMixin"
    _client: object = field(default=None, init=False, repr=False)

    def __enter__(self) -> "SSHClient":
        """Open the SSH connection.

        Returns:
            Self with an active connection.
        """
        self._connect()
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the SSH connection."""
        self._disconnect()

    def _connect(self) -> None:
        """Establish the SSH connection using paramiko.

        Raises:
            RuntimeError: If required explicit SSH auth fields are missing, or
                if connection or authentication fails.
        """
        private_key = self.config.ssh_private_key

        key_path = (
            os.path.expanduser(self.config.ssh_key_path)
            if self.config.ssh_key_path
            else None
        )

        if not key_path and private_key is None:
            raise RuntimeError(
                "SSH authentication requires either `ssh_key_path` or "
                "`ssh_private_key` to be configured on the component."
            )

        passphrase = self.config.ssh_key_passphrase

        client = paramiko.SSHClient()

        # Host key policy
        if self.config.verify_host_key:
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            try:
                if self.config.known_hosts_path:
                    client.load_host_keys(self.config.known_hosts_path)
                else:
                    client.load_system_host_keys()
            except FileNotFoundError:
                logger.warning(
                    "Known hosts file not found. Host key verification "
                    "may fail. Add the remote host key to your known_hosts "
                    "file or set verify_host_key=False (less secure)."
                )
        else:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec

        # Load the private key
        pkey: Optional[paramiko.PKey] = None
        if key_path:
            try:
                pkey = paramiko.RSAKey.from_private_key_file(
                    key_path, password=passphrase
                )
            except paramiko.ssh_exception.SSHException:
                # Try other key types (Ed25519, ECDSA)
                try:
                    pkey = paramiko.Ed25519Key.from_private_key_file(
                        key_path, password=passphrase
                    )
                except paramiko.ssh_exception.SSHException:
                    pkey = paramiko.ECDSAKey.from_private_key_file(
                        key_path, password=passphrase
                    )
        elif private_key:
            key_file = io.StringIO(private_key)
            try:
                pkey = paramiko.RSAKey.from_private_key(
                    key_file, password=passphrase
                )
            except paramiko.ssh_exception.SSHException:
                key_file.seek(0)
                try:
                    pkey = paramiko.Ed25519Key.from_private_key(
                        key_file, password=passphrase
                    )
                except paramiko.ssh_exception.SSHException:
                    key_file.seek(0)
                    pkey = paramiko.ECDSAKey.from_private_key(
                        key_file, password=passphrase
                    )

        auth_method = "key file" if self.config.ssh_key_path else "key content"
        # Retry transient connection failures (e.g. a momentarily overloaded
        # sshd dropping connections -> "Error reading SSH protocol banner",
        # socket timeouts, resets). Without this a brief blip on the host
        # fails the whole pipeline run with a cryptic paramiko error.
        max_attempts = 3
        last_error: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                client.connect(
                    hostname=self.config.hostname,
                    port=self.config.port,
                    username=self.config.username,
                    pkey=pkey,
                    timeout=self.config.connection_timeout,
                )
                last_error = None
                break
            except paramiko.AuthenticationException as e:
                # Authentication won't succeed on retry, fail fast with
                # actionable guidance.
                raise RuntimeError(
                    f"SSH authentication failed connecting to "
                    f"{self.config.hostname}:{self.config.port} as "
                    f"{self.config.username} using {auth_method}. Check that "
                    f"the username is correct and the public key is authorized "
                    f"on the host (~/.ssh/authorized_keys): {e}"
                ) from e
            except (
                paramiko.SSHException,
                socket.timeout,
                OSError,
                EOFError,
            ) as e:
                last_error = e
                if attempt < max_attempts:
                    backoff = 2**attempt
                    logger.warning(
                        "SSH connection to %s:%d failed (attempt %d/%d): %s. "
                        "Retrying in %ds...",
                        self.config.hostname,
                        self.config.port,
                        attempt,
                        max_attempts,
                        e,
                        backoff,
                    )
                    time.sleep(backoff)
        if last_error is not None:
            raise RuntimeError(
                f"Could not establish an SSH connection to "
                f"{self.config.hostname}:{self.config.port} as "
                f"{self.config.username} after {max_attempts} attempts (using "
                f"{auth_method}). To diagnose, run this from the machine "
                f"executing the pipeline:\n"
                f"    ssh -p {self.config.port} {self.config.username}@"
                f"{self.config.hostname}\n"
                f"- If that also fails: the host is unreachable — check it is "
                f"running, that a firewall/security group allows inbound TCP "
                f"on port {self.config.port}, and that the hostname/IP is "
                f"correct.\n"
                f"- If that succeeds: the host was likely transiently "
                f"overloaded (re-run the pipeline) or low on resources — check "
                f"its disk and memory (`df -h`, `free -m`).\n"
                f"Last error: {last_error}"
            ) from last_error

        # Configure keepalive
        if self.config.keepalive_interval > 0:
            transport = client.get_transport()
            if transport:
                transport.set_keepalive(self.config.keepalive_interval)

        self._client = client
        logger.info(
            "SSH connection established to %s:%d as %s",
            self.config.hostname,
            self.config.port,
            self.config.username,
        )

    def _disconnect(self) -> None:
        """Close the SSH connection if open."""
        if self._client is not None:
            try:
                if isinstance(self._client, paramiko.SSHClient):
                    self._client.close()
            except Exception:
                logger.debug("Error closing SSH connection", exc_info=True)
            finally:
                self._client = None

    def _get_client(self) -> "paramiko.SSHClient":
        """Get the underlying paramiko client, ensuring it is connected.

        Returns:
            The active paramiko SSHClient.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None or not isinstance(
            self._client, paramiko.SSHClient
        ):
            raise RuntimeError(
                "SSH client is not connected. Use SSHClient as a "
                "context manager: `with SSHClient(config) as ssh: ...`"
            )
        return self._client

    def exec(
        self,
        command: str,
        *,
        stream: bool = False,
        get_pty: bool = False,
        combine_stderr: bool = False,
    ) -> RemoteCommandResult:
        """Execute a command on the remote host.

        Args:
            command: Shell command to execute.
            stream: If True, stream stdout to the local logger in real time.
            get_pty: Request a pseudo-terminal (improves log buffering for
                long-running commands).
            combine_stderr: If True, merge stderr into stdout on the channel
                to avoid buffer deadlocks on long output.

        Returns:
            RemoteCommandResult with exit code and captured output.
        """
        client = self._get_client()

        if stream:
            return self._exec_streaming(
                client,
                command,
                get_pty=get_pty,
                combine_stderr=combine_stderr,
            )

        _, stdout_ch, stderr_ch = client.exec_command(command, get_pty=get_pty)  # nosec
        stdout_text = stdout_ch.read().decode("utf-8", errors="replace")
        stderr_text = stderr_ch.read().decode("utf-8", errors="replace")
        exit_code = stdout_ch.channel.recv_exit_status()

        return RemoteCommandResult(
            exit_code=exit_code,
            stdout=stdout_text,
            stderr=stderr_text,
        )

    def _exec_streaming(
        self,
        client: "paramiko.SSHClient",
        command: str,
        *,
        get_pty: bool,
        combine_stderr: bool,
    ) -> RemoteCommandResult:
        """Execute a command with real-time log streaming.

        Args:
            client: The paramiko SSHClient.
            command: Shell command to execute.
            get_pty: Request a pseudo-terminal.
            combine_stderr: Merge stderr into stdout.

        Returns:
            RemoteCommandResult with exit code and captured output.

        Raises:
            RuntimeError: If the SSH transport is not available.
        """
        transport = client.get_transport()
        if transport is None:
            raise RuntimeError("SSH transport is not available.")

        channel = transport.open_session()
        if combine_stderr:
            channel.set_combine_stderr(True)
        if get_pty:
            channel.get_pty()
        channel.exec_command(command)  # nosec

        stdout_chunks: list[str] = []
        buf_size = 4096

        while True:
            if channel.recv_ready():
                data = channel.recv(buf_size).decode("utf-8", errors="replace")
                stdout_chunks.append(data)
                for line in data.splitlines():
                    if line.strip():
                        logger.info("[remote] %s", line.rstrip())
            else:
                if channel.exit_status_ready():
                    break
                time.sleep(0.1)

        exit_code = channel.recv_exit_status()
        channel.close()

        return RemoteCommandResult(
            exit_code=exit_code,
            stdout="".join(stdout_chunks),
            stderr="",
        )

    @contextmanager
    def sftp(self) -> Iterator["paramiko.SFTPClient"]:
        """Open an SFTP session over the active connection.

        Yields:
            An open paramiko SFTP client.
        """
        client = self._get_client()
        sftp = client.open_sftp()
        try:
            yield sftp
        finally:
            sftp.close()

    def put_text(
        self, remote_path: str, content: str, *, mode: int = 0o600
    ) -> None:
        """Upload text content to a file on the remote host via SFTP.

        Args:
            remote_path: Absolute path on the remote host.
            content: Text content to write.
            mode: File permissions (default: owner read/write only).
        """
        with self.sftp() as sftp:
            with sftp.file(remote_path, "w") as f:
                f.write(content)
            sftp.chmod(remote_path, mode)

    def read_text(self, remote_path: str) -> str:
        """Read a remote file's text contents via SFTP.

        Args:
            remote_path: Absolute path on the remote host.

        Returns:
            The file contents as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        with self.sftp() as sftp:
            try:
                with sftp.file(remote_path, "r") as f:
                    raw: bytes = f.read()
                    return raw.decode("utf-8", errors="replace")
            except FileNotFoundError:
                raise
            except OSError as e:
                raise FileNotFoundError(
                    f"Remote file not found or unreadable: {remote_path}"
                ) from e
