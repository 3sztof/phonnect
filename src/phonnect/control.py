"""A tiny local request channel from sidebar windows to the tray app.

The tray is the only process that changes settings on the phone (rotation,
density) and in config.json, so sidebars ask it to. One JSON object per line,
one reply line. It listens on 127.0.0.1 only, and every request must carry a
random token, which sidebars receive through their environment.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import socket
import socketserver
import threading
from collections.abc import Callable

from phonnect import paths

log = logging.getLogger(__name__)

ENV_VAR = "PHONNECT_CONTROL"
MAX_REQUEST = 64 * 1024


class ControlServer:
    def __init__(self, handler: Callable[[dict], dict]):
        self.token = secrets.token_hex(16)
        outer = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                line = self.rfile.readline(MAX_REQUEST)
                try:
                    msg = json.loads(line)
                    if not isinstance(msg, dict) or not secrets.compare_digest(str(msg.get("token", "")), outer.token):
                        reply = {"ok": False, "error": "unauthorized"}
                    else:
                        reply = handler(msg)
                except Exception as exc:
                    log.exception("Control request failed")
                    reply = {"ok": False, "error": str(exc)}
                self.wfile.write((json.dumps(reply) + "\n").encode("utf-8"))

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True
            allow_reuse_address = False

        self._server = Server(("127.0.0.1", 0), Handler)
        host, port = self._server.server_address[:2]
        self.address = f"{host}:{port}"
        self._thread = threading.Thread(target=self._server.serve_forever, name="control", daemon=True)

    def start(self) -> ControlServer:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def request(address: str, token: str, msg: dict, timeout: float = 5.0) -> dict:
    host, _, port = address.rpartition(":")
    with socket.create_connection((host, int(port)), timeout=timeout) as sock:
        sock.sendall((json.dumps({**msg, "token": token}) + "\n").encode("utf-8"))
        with sock.makefile("rb") as f:
            return json.loads(f.readline(MAX_REQUEST) or b"{}")


def parse_env(value: str | None) -> tuple[str, str] | None:
    """'127.0.0.1:5000 <token>' -> (address, token)."""
    if not value or " " not in value:
        return None
    address, token = value.split(" ", 1)
    return address, token.strip()


def write_endpoint(address: str, token: str) -> None:
    """Let `phonnect mirror` find the running tray. Readable by this user only."""
    path = paths.state_dir() / "control"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as f:
            f.write(f"{address} {token}")
    except OSError as exc:
        log.warning("Could not write %s: %s", path, exc)


def read_endpoint() -> tuple[str, str] | None:
    try:
        return parse_env((paths.state_dir() / "control").read_text(encoding="ascii"))
    except OSError:
        return None


def remove_endpoint() -> None:
    try:
        (paths.state_dir() / "control").unlink(missing_ok=True)
    except OSError:
        pass
