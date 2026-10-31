"""Fake Moonraker for integration tests (T012).

Serves exactly the endpoints in specs/001-klipper-print-workflow/contracts/moonraker-subset.md.
The ``fake_moonraker`` fixture also enforces the contract's rules at teardown:

* ``/printer/print/start`` must never be called.
* Every upload form must carry ``print=false`` (``print=true`` never appears).
* No request outside the contract's endpoint set.
"""

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field

import pytest
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response

HANG_MAX_S = 30.0

DEFAULT_CONFIG_FILES = {
    "printer.cfg": b"[stepper_x]\nstep_pin: PE3\n",
    "moonraker.conf": b"[server]\nport: 7125\n",
    "fluidd.cfg": b"[virtual_sdcard]\npath: ~/gcode_files\n",
}


@dataclass
class Request:
    method: str
    path: str
    args: dict[str, str]


@dataclass
class Upload:
    fields: dict[str, str]
    filename: str
    content: bytes
    sha256: str
    accepted: bool


@dataclass
class FakeMoonraker:
    url: str
    requests: list[Request] = field(default_factory=list)
    uploads: list[Upload] = field(default_factory=list)
    forbidden: list[Request] = field(default_factory=list)
    unexpected: list[Request] = field(default_factory=list)
    gcodes: dict[str, bytes] = field(default_factory=dict)
    config_files: dict[str, bytes] = field(default_factory=lambda: dict(DEFAULT_CONFIG_FILES))
    metadata_enabled: bool = True
    metadata_overrides: dict[str, dict] = field(default_factory=dict)
    checksum_mode: str = "enforce"  # "enforce", or "ignore" for a fork that skips the check
    pad_style: bool = (
        False  # mimic the Sonic Pad fork: bad checksum is a 500, upload reply unwrapped
    )
    server_info: dict = field(
        default_factory=lambda: {
            "klippy_connected": True,
            "klippy_state": "ready",
            "moonraker_version": "v0.0.0-fake",
            "api_version": [1, 0, 0],
            "components": [],
        }
    )
    _states: list = field(default_factory=list)
    _polls: int = 0
    _release: threading.Event = field(default_factory=threading.Event)
    _hanging: bool = False

    # ---- scripting -------------------------------------------------------------------------

    @staticmethod
    def state(
        print_state="standby",
        klippy="ready",
        filename="",
        progress=0.0,
        extruder=25.0,
        bed=24.0,
        message="",
    ) -> dict:
        """One ``printer/objects/query`` snapshot."""
        return {
            "webhooks": {"state": klippy, "state_message": message},
            "print_stats": {"state": print_state, "filename": filename, "message": message},
            "virtual_sdcard": {"progress": progress},
            "extruder": {"temperature": extruder},
            "heater_bed": {"temperature": bed},
        }

    def set_states(self, *items) -> None:
        """Script the next queries. An item is a snapshot dict or an int HTTP error status.

        The last item repeats once the script runs out.
        """
        self._states = list(items)
        self._polls = 0

    def hang(self, on: bool = True) -> None:
        """While on, every response is held back (until released or HANG_MAX_S passes)."""
        self._hanging = on
        if not on:
            self._release.set()

    def calls(self, path: str) -> list[Request]:
        return [r for r in self.requests if r.path == path]

    # ---- server ----------------------------------------------------------------------------

    def handle(self, request) -> Response:
        rec = Request(request.method, request.path, dict(request.args))
        self.requests.append(rec)
        if request.path == "/printer/print/start":
            self.forbidden.append(rec)
            return self._json(
                {"error": {"code": 403, "message": "tools must not start prints"}}, 403
            )
        if self._hanging:
            self._release.wait(HANG_MAX_S)
        route = self._route(request, rec)
        if route is None:
            self.unexpected.append(rec)
            return self._json({"error": {"code": 404, "message": "not in contract"}}, 404)
        return route

    def _route(self, request, rec) -> Response | None:
        method, path = request.method, request.path
        if method == "GET" and path == "/server/info":
            return self._json({"result": self.server_info})
        if method == "GET" and path == "/printer/objects/query":
            return self._query(request)
        if method == "POST" and path == "/server/files/upload":
            return self._upload(request)
        if method == "GET" and path == "/server/files/metadata":
            return self._metadata(request.args.get("filename", ""))
        if method == "DELETE" and path.startswith("/server/files/gcodes/"):
            return self._delete(path.removeprefix("/server/files/gcodes/"))
        if (
            method == "GET"
            and path == "/server/files/list"
            and request.args.get("root") == "config"
        ):
            items = [
                {"path": name, "modified": time.time(), "size": len(data), "permissions": "rw"}
                for name, data in sorted(self.config_files.items())
            ]
            return self._json({"result": items})
        if method == "GET" and path.startswith("/server/files/config/"):
            name = path.removeprefix("/server/files/config/")
            if name in self.config_files:
                return Response(
                    self.config_files[name], 200, content_type="application/octet-stream"
                )
            return self._json({"error": {"code": 404, "message": f"File {name} not found"}}, 404)
        return None

    def _query(self, request) -> Response:
        script = self._states or [self.state()]
        item = script[min(self._polls, len(script) - 1)]
        self._polls += 1
        if isinstance(item, int):
            return self._json({"error": {"code": item, "message": "scripted failure"}}, item)
        status = {name: item[name] for name in request.args if name in item}
        return self._json({"result": {"eventtime": time.monotonic(), "status": status}})

    def _upload(self, request) -> Response:
        upload = request.files.get("file")
        if upload is None:
            return self._json({"error": {"code": 400, "message": "no file part"}}, 400)
        content = upload.read()
        digest = hashlib.sha256(content).hexdigest()
        fields = dict(request.form)
        want = fields.get("checksum")
        ok = self.checksum_mode == "ignore" or want is None or want.lower() == digest
        self.uploads.append(Upload(fields, upload.filename, content, digest, ok))
        if not ok and self.pad_style:
            err = {
                "code": 500,
                "message": "Internal Server Error",
                "traceback": "ServerError: File checksum mismatch: expected x",
            }
            return self._json({"error": err}, 500)
        if not ok:
            return self._json({"error": {"code": 422, "message": "checksum mismatch"}}, 422)
        subdir = fields.get("path", "").strip("/")
        dest = f"{subdir}/{upload.filename}" if subdir else upload.filename
        self.gcodes[dest] = content  # replaced only after the checksum is accepted
        item = {"path": dest, "root": "gcodes", "size": len(content), "modified": time.time()}
        result = {"item": item, "print_started": False, "print_queued": False}
        reply = {**result, "action": "create_file"}
        return self._json(reply if self.pad_style else {"result": reply}, 201)

    def _metadata(self, filename: str) -> Response:
        if not self.metadata_enabled or filename not in self.gcodes:
            msg = f"Metadata not available for {filename}"
            return self._json({"error": {"code": 404, "message": msg}}, 404)
        data = {
            "filename": filename,
            "size": len(self.gcodes[filename]),
            "estimated_time": 3600.0,
            "filament_total": 1500.0,
            **self.metadata_overrides.get(filename, {}),
        }
        return self._json({"result": data})

    def _delete(self, name: str) -> Response:
        if name not in self.gcodes:
            return self._json({"error": {"code": 404, "message": f"File {name} not found"}}, 404)
        del self.gcodes[name]
        item = {"path": name, "root": "gcodes"}
        return self._json({"result": {"item": item, "action": "delete_file"}})

    @staticmethod
    def _json(body: dict, status: int = 200) -> Response:
        return Response(json.dumps(body), status, content_type="application/json")

    # ---- contract rules --------------------------------------------------------------------

    def contract_violations(self) -> list[str]:
        problems = [f"called {r.method} {r.path}" for r in self.forbidden]
        problems += [f"request outside the contract: {r.method} {r.path}" for r in self.unexpected]
        for up in self.uploads:
            if up.fields.get("print") != "false":
                problems.append(f"upload of {up.filename} without print=false: {up.fields}")
        return problems


@pytest.fixture(scope="session")
def make_httpserver():
    """Threaded server, so a hung response does not block other requests or teardown."""
    server = HTTPServer(host="127.0.0.1", port=0, threaded=True)
    server.start()
    yield server
    server.clear()
    if server.is_running():
        server.stop()


@pytest.fixture
def fake_moonraker(httpserver):
    fake = FakeMoonraker(url=httpserver.url_for("").rstrip("/"))
    httpserver.expect_request(re.compile(".*")).respond_with_handler(fake.handle)
    yield fake
    fake._release.set()
    problems = fake.contract_violations()
    assert not problems, "Moonraker contract broken:\n" + "\n".join(problems)
