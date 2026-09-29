"""Single model request in a subprocess that the controller can terminate."""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Prevent forwarding endpoint credentials through redirects."""

    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        """Decline all HTTP redirects.

        Args:
            req: Original request.
            fp: Response stream.
            code: Redirect status code.
            msg: HTTP status message.
            headers: Response headers.
            newurl: Proposed redirect destination.
        """
        return None


def main() -> None:
    """Read request configuration and emit only result JSON or a sanitized error."""
    try:
        config = json.load(sys.stdin)
        request = urllib.request.Request(
            config["url"],
            data=json.dumps(config["body"]).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer "
                + os.environ.get("ENDLESS_API_KEY", "nokey"),
            },
        )
        with urllib.request.build_opener(NoRedirect).open(
            request, timeout=config["timeout"]
        ) as response:
            payload = response.read(4_000_001)
        if len(payload) > 4_000_000:
            result = {"error": "Model response exceeds 4 MB limit"}
        else:
            result = {"data": json.loads(payload)}
    except urllib.error.HTTPError as exc:
        result = {
            "error": f"Model HTTP error {exc.code}; request was not retried"
        }
    except Exception:
        result = {
            "error": "Model transport or response decoding failed; request was not retried"
        }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
