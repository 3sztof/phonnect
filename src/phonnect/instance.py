"""Single-instance lock based on an OS file lock (released automatically if the process dies)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO

from phonnect import paths
from phonnect.osutil import IS_WINDOWS


class InstanceLock:
    def __init__(self, lock_path: Path | None = None, pid_path: Path | None = None):
        self.lock_path = lock_path or paths.lock_file()
        self.pid_path = pid_path or paths.pid_file()
        self._fh: IO | None = None

    def acquire(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(self.lock_path, "a+")  # noqa: SIM115 - stays open: holding it is the lock
        try:
            if IS_WINDOWS:
                import msvcrt

                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            return False
        self._fh = fh
        # The PID lives in a separate file: on Windows the locked byte can't be
        # read by other processes.
        self.pid_path.write_text(str(os.getpid()), encoding="ascii")
        return True

    def release(self) -> None:
        if self._fh is None:
            return
        try:
            self.pid_path.unlink(missing_ok=True)
        except OSError:
            pass
        self._fh.close()
        self._fh = None

    def __enter__(self) -> InstanceLock:
        return self

    def __exit__(self, *exc) -> None:
        self.release()


def running_pid() -> int | None:
    """PID of the running instance, or None if nothing holds the lock."""
    probe = InstanceLock()
    if probe.acquire():
        probe.release()
        return None
    try:
        return int(paths.pid_file().read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return -1  # locked, but PID unknown
