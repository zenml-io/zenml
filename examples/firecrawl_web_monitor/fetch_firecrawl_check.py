"""Pull Firecrawl monitor checks and convert them into pipeline payloads."""

from typing import Any, Dict, List, Optional

import requests

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v2"


def build_page_payloads(check: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert a check-details response into per-page pipeline payloads.

    The per-page objects returned by the checks API match the ``data``
    entries of a ``monitor.page`` webhook, so each page becomes one payload
    with the same envelope a webhook delivery would carry. ``monitorId`` and
    ``checkId`` live on the parent check object in API responses, so they
    are merged into each page.

    Args:
        check: The ``data`` object of a check-details response.

    Returns:
        One ``monitor.page``-style payload per page result.
    """
    payloads: List[Dict[str, Any]] = []
    for page in check.get("pages", []):
        page_data = {
            "monitorId": check["monitorId"],
            "checkId": check["id"],
            **page,
        }
        payloads.append(
            {
                "success": True,
                "type": "monitor.page",
                "id": check["id"],
                "webhookId": "api-pull",
                "data": [page_data],
                "metadata": {"source": "fetch_firecrawl_check"},
            }
        )
    return payloads


def fetch_check(
    api_key: str, monitor_id: str, check_id: Optional[str] = None
) -> Dict[str, Any]:
    """Fetch a monitor check, defaulting to the latest completed one.

    Args:
        api_key: Firecrawl API key.
        monitor_id: Monitor to read checks from.
        check_id: Specific check to fetch. Defaults to the most recent
            completed check.

    Raises:
        RuntimeError: If the monitor has no completed checks yet.

    Returns:
        The ``data`` object of the check-details response.
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    if check_id is None:
        response = requests.get(
            f"{FIRECRAWL_API_URL}/monitor/{monitor_id}/checks",
            headers=headers,
            params={"status": "completed"},
            timeout=30,
        )
        response.raise_for_status()
        checks = response.json().get("data", [])
        if not checks:
            raise RuntimeError(
                f"Monitor {monitor_id} has no completed checks yet."
            )
        check_id = checks[0]["id"]

    response = requests.get(
        f"{FIRECRAWL_API_URL}/monitor/{monitor_id}/checks/{check_id}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    data: Dict[str, Any] = response.json()["data"]
    return data
