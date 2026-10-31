"""Live test against the real Sonic Pad (T014). Run with ``make test-live`` (needs ``--live``).

Read-only: two GETs before and after. It never prints, uploads or changes anything.
Uses ``~/.config/cr10s/config.toml`` (or ``CR10S_PAD_URL``) to find the Pad.
"""

import httpx
import pytest

from cr10s import config

pytestmark = pytest.mark.live

KLIPPY_STATES = {"ready", "startup", "shutdown", "error", "disconnected"}


@pytest.fixture(scope="module")
def pad():
    cfg = config.load().pad
    with httpx.Client(base_url=cfg.url, timeout=cfg.timeout_s) as client:
        yield client


def print_state(pad: httpx.Client) -> str:
    resp = pad.get("/printer/objects/query", params={"print_stats": ""})
    resp.raise_for_status()
    return resp.json()["result"]["status"]["print_stats"]["state"]


def test_server_info_reports_klippy_state(pad):
    resp = pad.get("/server/info")
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["klippy_state"] in KLIPPY_STATES


def test_printer_is_standby_before_and_after_probing(pad):
    before = print_state(pad)
    pad.get("/server/info").raise_for_status()
    after = print_state(pad)
    assert before == "standby"
    assert after == "standby"
