"""Moonraker client for the endpoints in contracts/moonraker-subset.md, and only those.

There is deliberately no method that starts a print.
"""

import time
from pathlib import Path
from urllib.parse import quote

import httpx

from cr10s import cli
from cr10s.log import Logger

QUERY_OBJECTS = ("webhooks", "print_stats", "virtual_sdcard", "extruder", "heater_bed")


class Moonraker:
    def __init__(self, url: str, timeout_s: float, logger: Logger | None = None):
        self.url = url.rstrip("/")
        self._log = logger
        # httpx timeouts apply per operation, so a slow but moving upload has no total cap.
        self._http = httpx.Client(base_url=self.url, timeout=httpx.Timeout(timeout_s))

    @classmethod
    def from_context(cls, ctx: cli.Context) -> "Moonraker":
        return cls(ctx.config.pad.url, ctx.config.pad.timeout_s, ctx.log)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Moonraker":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def server_info(self) -> dict:
        return self._result(self._request("GET", "/server/info"))

    def query_objects(self, objects: tuple[str, ...] = QUERY_OBJECTS) -> dict:
        resp = self._request("GET", "/printer/objects/query?" + "&".join(objects))
        return self._result(resp)["status"]

    def upload(
        self, local: Path, remote_dir: str | None, checksum: str, name: str | None = None
    ) -> dict:
        """Upload to the gcodes root. ``print`` is always ``false``: nothing here starts a print."""
        local = Path(local)
        data = {"root": "gcodes", "print": "false", "checksum": checksum}
        if remote_dir:
            data["path"] = remote_dir
        with local.open("rb") as handle:
            resp = self._request(
                "POST",
                "/server/files/upload",
                data=data,
                files={"file": (name or local.name, handle)},
                log_extra={"file": str(local), "sha256": checksum},
            )
        return self._result(resp)

    def metadata(self, filename: str) -> dict | None:
        """File metadata, or None while the host has none (404)."""
        resp = self._request(
            "GET", f"/server/files/metadata?filename={quote(filename)}", allow_404=True
        )
        return None if resp.status_code == 404 else self._result(resp)

    def delete_gcode(self, path: str) -> dict:
        return self._result(self._request("DELETE", f"/server/files/gcodes/{quote(path)}"))

    def list_config(self) -> list[dict]:
        return self._result(self._request("GET", "/server/files/list?root=config"))

    def get_config_file(self, name: str) -> bytes:
        return self._request("GET", f"/server/files/config/{quote(name)}").content

    def _request(
        self,
        method: str,
        path: str,
        *,
        allow_404: bool = False,
        log_extra: dict | None = None,
        **kwargs,
    ) -> httpx.Response:
        start = time.monotonic()
        try:
            resp = self._http.request(method, path, **kwargs)
        except httpx.TransportError as err:
            raise cli.Unreachable(f"cannot reach {self.url}: {type(err).__name__}") from err
        ms = round((time.monotonic() - start) * 1000)
        shown = path.split("?")[0]
        if self._log:
            self._log.debug(
                "http_request",
                f"{method} {shown} -> {resp.status_code}",
                method=method,
                path=shown,
                status=resp.status_code,
                ms=ms,
                **(log_extra or {}),
            )
        if resp.is_success or (allow_404 and resp.status_code == 404):
            return resp
        message = self._error_message(resp)
        if self._log:
            self._log.error(
                "http_error", f"{method} {shown} -> {resp.status_code}", status=resp.status_code
            )
        if resp.status_code == 422 and path == "/server/files/upload":
            raise cli.ChecksumMismatch(f"Pad rejected the upload: {message}", resp.status_code)
        raise cli.Rejected(f"HTTP {resp.status_code} from the Pad: {message}", resp.status_code)

    @staticmethod
    def _error_message(resp: httpx.Response) -> str:
        try:
            return str(resp.json()["error"]["message"])
        except (ValueError, KeyError, TypeError):
            return resp.text[:100] or resp.reason_phrase

    @staticmethod
    def _result(resp: httpx.Response):
        try:
            return resp.json()["result"]
        except (ValueError, KeyError, TypeError):
            raise cli.Rejected("unexpected response from the Pad", resp.status_code) from None
