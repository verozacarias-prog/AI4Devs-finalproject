"""Case 14: the server itself never logs the client IP or the requested address."""

from __future__ import annotations

import io
import json
import socket
import threading
import time

import pytest

from app.adapters.inbound.api.app import create_app
from app.adapters.inbound.api.server import build_server
from app.settings import load_settings

pytestmark = pytest.mark.integration

WEBSOCKET_UPGRADE = (
    "GET /healthz?token=abc123 HTTP/1.1\r\n"
    "Host: localhost\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
    "Sec-WebSocket-Version: 13\r\n"
    "\r\n"
)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


def test_a_websocket_attempt_leaves_no_ip_token_or_address_in_the_logs(database_url: str) -> None:
    stream = io.StringIO()
    settings = load_settings({"DATABASE_URL": database_url, "APP_VERSION": "test"})
    port = free_port()
    server = build_server(create_app(settings, log_stream=stream), host="127.0.0.1", port=port)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started, "the server did not start"
        with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
            client.sendall(WEBSOCKET_UPGRADE.encode())
            client.recv(4096)
    finally:
        server.should_exit = True
        thread.join(timeout=10)

    raw = stream.getvalue()
    assert raw, "the server left no log line"
    for line in raw.splitlines():
        json.loads(line)
    assert "127.0.0.1" not in raw
    assert "abc123" not in raw
    assert "/healthz" not in raw
