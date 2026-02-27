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
"""SSH client wrapper with lazy paramiko import.

This module isolates all Paramiko-specific behavior so the step operator
does not need to interact with Paramiko internals directly.  Paramiko is
imported lazily (inside methods) so the integration can be discovered by
ZenML's registry even when paramiko is not installed.
"""

import io
from dataclasses import dataclass, field
from typing import Optional

from zenml.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SSHConnectionConfig:
    """Configuration for an SSH connection.

    Attributes:
        hostname: Remote host to connect to.
        port: SSH port.
        username: SSH username.
        ssh_key_path: Path to a private key file (mutually exclusive with
            ssh_private_key, but at least one must be set).
        ssh_private_key: Private key content as a string.
        ssh_key_passphrase: Passphrase for an encrypted private key.
        verify_host_key: Whether to verify the remote host key.
        known_hosts_path: Path to a known_hosts file.
        connection_timeout: Timeout in seconds for connection.
        keepalive_interval: Seconds between keepalive packets.
    """

    hostname: str
    port: int
    username: str
    ssh_key_path: Optional[str] = None
    ssh_private_key: Optional[str] = None
    ssh_key_passphrase: Optional[str] = None
    verify_host_key: bool = True
    known_hosts_path: Optional[str] = None
    connection_timeout: float = 10.0
    keepalive_interval: int = 30


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

    Usage::

        cfg = SSHConnectionConfig(hostname="gpu-box", ...)
        with SSHClient(cfg) as ssh:
            result = ssh.exec("docker --version")
            ssh.put_text("/tmp/env", "KEY=VALUE\\n", mode=0o600)

    Attributes:
        config: Connection configuration.
    """

    config: SSHConnectionConfig
    _client: object = field(default=None, init=False, repr=False)

    def __enter__(self) -> "SSHClient":
        """Open the SSH connection.

        Returns:
            Self with an active connection.

        Raises:
            RuntimeError: If paramiko is not installed or connection fails.
        """
        self._connect()
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the SSH connection."""
        self._disconnect()

    def _connect(self) -> None:
        """Establish the SSH connection using paramiko.

        Raises:
            RuntimeError: If connection or authentication fails.
        """
        try:
            import paramiko
        except ImportError as e:
            raise RuntimeError(
                "The 'paramiko' package is required for the SSH step "
                "operator but is not installed. Install it with: "
                "zenml integration install ssh"
            ) from e

        client = paramiko.SSHClient()

        # Host key policy
        if self.config.verify_host_key:
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            known_hosts = (
                self.config.known_hosts_path
                if self.config.known_hosts_path
                else None
            )
            try:
                if known_hosts:
                    client.load_host_keys(known_hosts)
                else:
                    client.load_system_host_keys()
            except FileNotFoundError:
                logger.warning(
                    "Known hosts file not found. Host key verification "
                    "may fail. Add the remote host key to your known_hosts "
                    "file or set verify_host_key=False (less secure)."
                )
        else:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Load the private key
        passphrase = (
            self.config.ssh_key_passphrase
            if self.config.ssh_key_passphrase
            else None
        )
        pkey: Optional[paramiko.PKey] = None
        if self.config.ssh_key_path:
            try:
                pkey = paramiko.RSAKey.from_private_key_file(
                    self.config.ssh_key_path, password=passphrase
                )
            except paramiko.ssh_exception.SSHException:
                # Try other key types (Ed25519, ECDSA)
                try:
                    pkey = paramiko.Ed25519Key.from_private_key_file(
                        self.config.ssh_key_path, password=passphrase
                    )
                except paramiko.ssh_exception.SSHException:
                    pkey = paramiko.ECDSAKey.from_private_key_file(
                        self.config.ssh_key_path, password=passphrase
                    )
        elif self.config.ssh_private_key:
            key_file = io.StringIO(self.config.ssh_private_key)
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

        try:
            client.connect(
                hostname=self.config.hostname,
                port=self.config.port,
                username=self.config.username,
                pkey=pkey,
                timeout=self.config.connection_timeout,
            )
        except Exception as e:
            auth_method = (
                "key file" if self.config.ssh_key_path else "key content"
            )
            raise RuntimeError(
                f"Failed to connect to {self.config.hostname}:"
                f"{self.config.port} as {self.config.username} "
                f"using {auth_method}: {e}"
            ) from e

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
                import paramiko

                if isinstance(self._client, paramiko.SSHClient):
                    self._client.close()
            except Exception:
                pass
            finally:
                self._client = None

    def _get_client(self) -> "paramiko.SSHClient":
        """Get the underlying paramiko client, ensuring it is connected.

        Returns:
            The active paramiko SSHClient.

        Raises:
            RuntimeError: If not connected.
        """
        import paramiko

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

        _, stdout_ch, stderr_ch = client.exec_command(command, get_pty=get_pty)
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
        """
        transport = client.get_transport()
        if transport is None:
            raise RuntimeError("SSH transport is not available.")

        channel = transport.open_session()
        if combine_stderr:
            channel.set_combine_stderr(True)
        if get_pty:
            channel.get_pty()
        channel.exec_command(command)

        stdout_chunks: list[str] = []
        buf_size = 4096

        while True:
            if channel.recv_ready():
                data = channel.recv(buf_size).decode("utf-8", errors="replace")
                stdout_chunks.append(data)
                # Stream each line to the logger
                for line in data.splitlines():
                    if line.strip():
                        logger.info("[remote] %s", line.rstrip())

            if channel.exit_status_ready() and not channel.recv_ready():
                break

        exit_code = channel.recv_exit_status()
        channel.close()

        return RemoteCommandResult(
            exit_code=exit_code,
            stdout="".join(stdout_chunks),
            stderr="",
        )

    def put_text(
        self, remote_path: str, content: str, *, mode: int = 0o600
    ) -> None:
        """Upload text content to a file on the remote host via SFTP.

        Args:
            remote_path: Absolute path on the remote host.
            content: Text content to write.
            mode: File permissions (default: owner read/write only).
        """
        client = self._get_client()
        sftp = client.open_sftp()
        try:
            with sftp.file(remote_path, "w") as f:
                f.write(content)
            sftp.chmod(remote_path, mode)
        finally:
            sftp.close()

    def read_text(self, remote_path: str) -> str:
        """Read a remote file's text contents via SFTP.

        Args:
            remote_path: Absolute path on the remote host.

        Returns:
            The file contents as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
            RuntimeError: If reading fails for another reason.
        """
        client = self._get_client()
        sftp = client.open_sftp()
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
        finally:
            sftp.close()

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists on the remote host.

        Args:
            remote_path: Absolute path on the remote host.

        Returns:
            True if the file exists, False otherwise.
        """
        result = self.exec(f"test -f {remote_path}")
        return result.exit_code == 0
