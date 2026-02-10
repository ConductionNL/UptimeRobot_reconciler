from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import requests


class UptimeRobotApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class Monitor:
    monitor_id: int
    friendly_name: str
    url: str
    interval: int
    monitor_type: int


class UptimeRobotClient:
    def __init__(self, api_key: str, base_url: str = "https://api.uptimerobot.com/v2") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def get_monitors(self) -> list[Monitor]:
        payload = {
            "logs": 0,
            "response_times": 0,
            "alert_contacts": 0,
        }
        data = self._post("getMonitors", payload)
        raw_monitors = data.get("monitors", [])

        monitors: list[Monitor] = []
        for raw in raw_monitors:
            monitor_type = int(raw.get("type", 0))
            if monitor_type != 1:
                continue

            monitor_id = int(raw["id"])
            friendly_name = str(raw.get("friendly_name", ""))
            url = str(raw.get("url", ""))
            interval = int(raw.get("interval", 0))
            monitors.append(
                Monitor(
                    monitor_id=monitor_id,
                    friendly_name=friendly_name,
                    url=url,
                    interval=interval,
                    monitor_type=monitor_type,
                )
            )
        return monitors

    def create_http_monitor(self, friendly_name: str, url: str, interval: int) -> dict[str, Any]:
        payload = {
            "type": 1,
            "friendly_name": friendly_name,
            "url": url,
            "interval": interval,
        }
        return self._post("newMonitor", payload)

    def edit_http_monitor(self, monitor_id: int, url: str, interval: int) -> dict[str, Any]:
        payload = {
            "id": monitor_id,
            "url": url,
            "interval": interval,
        }
        return self._post("editMonitor", payload)

    def delete_monitor(self, monitor_id: int) -> dict[str, Any]:
        payload = {"id": monitor_id}
        return self._post("deleteMonitor", payload)

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        request_data = {
            "api_key": self.api_key,
            "format": "json",
        }
        request_data.update(payload)

        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.post(url, data=request_data, timeout=30)
        except requests.RequestException as exc:
            raise UptimeRobotApiError(f"request to '{endpoint}' failed: {exc}") from exc

        if not response.ok:
            raise UptimeRobotApiError(
                f"'{endpoint}' returned HTTP {response.status_code}: {response.text[:400]}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise UptimeRobotApiError(f"'{endpoint}' did not return valid JSON.") from exc

        if body.get("stat") != "ok":
            error = body.get("error")
            detail = _normalize_error(error)
            raise UptimeRobotApiError(f"'{endpoint}' failed: {detail}")

        return body


def _normalize_error(error: Optional[Any]) -> str:
    if isinstance(error, dict):
        message = error.get("message")
        if message:
            return str(message)
        error_type = error.get("type")
        if error_type:
            return str(error_type)
        return str(error)
    if error is None:
        return "unknown API error"
    return str(error)
