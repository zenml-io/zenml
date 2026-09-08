"""Bounded Docker subprocess transport."""

import os
import selectors
import subprocess
import time
from dataclasses import dataclass

MAX_OUTPUT = 256 * 1024


@dataclass
class DockerCommand:
    """Execute Docker CLI commands using the resolved executable."""

    executable: str

    def __call__(
        self,
        args: list[str],
        *,
        timeout: float = 30,
        input_data: bytes | None = None,
        limit: int = MAX_OUTPUT,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        """Run Docker with bounded streamed output and a total deadline.

        Args:
            args: Docker command arguments.
            timeout: Maximum subprocess duration in seconds.
            input_data: Optional bytes sent through a temporary stdin file.
            limit: Maximum captured output bytes.
            check: Whether nonzero exit status raises an error.

        Returns:
            Completed process with bounded output.

        Raises:
            TimeoutError: Docker exceeded the deadline.
            RuntimeError: Output exceeded the cap or Docker failed.
        """
        import tempfile

        with tempfile.TemporaryFile() as stdin:
            if input_data is not None:
                stdin.write(input_data)
                stdin.seek(0)
            process = subprocess.Popen(
                [self.executable, *args],
                stdin=stdin,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            assert process.stdout is not None
            output = bytearray()
            end = time.monotonic() + timeout
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while True:
                        remaining = end - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError(f"Docker {args[0]} timed out")
                        if not selector.select(min(remaining, 0.2)):
                            continue
                        chunk = os.read(process.stdout.fileno(), 65536)
                        if not chunk:
                            break
                        output.extend(chunk)
                        if len(output) > limit:
                            raise RuntimeError(
                                f"Docker {args[0]} output exceeds {limit} bytes"
                            )
                code = process.wait(timeout=max(0.01, end - time.monotonic()))
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                process.stdout.close()
            result = subprocess.CompletedProcess(args, code, bytes(output))
            if check and code:
                raise RuntimeError(
                    f"Docker {args[0]} failed ({code}): {output.decode(errors='replace')[:2000]}"
                )
            return result
