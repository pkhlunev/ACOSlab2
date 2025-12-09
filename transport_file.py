import fcntl
import os
from logging import Logger
from pathlib import Path
from contextlib import contextmanager
from enum import IntEnum
from typing import NamedTuple


class RecordType(IntEnum):
    Error = -1
    Response = 0
    Request = 1


class TransportRecord(NamedTuple):
    state: RecordType
    seq: int
    payload: str



class TransportFile:
    def __init__(self, path_str: str, logger: Logger) -> None:
        self.path: Path = Path(path_str)
        self.fd: int = -1
        self.logger: Logger = logger

    def _ensure_file(self) -> int:
        if self.fd == -1:
            raise ValueError("file is not opened")
        return self.fd

    @staticmethod
    def _parse_line(line: str) -> TransportRecord:
        parts = line.strip().split(";", 2)
        if len(parts) != 3:
            raise ValueError("bad format")
        try:
            state = RecordType(int(parts[0].strip()))
        except (ValueError, KeyError) as e:
            raise ValueError("bad state") from e
        try:
            seq = int(parts[1].strip())
        except ValueError as e:
            raise ValueError("bad seq") from e
        payload = parts[2]
        return TransportRecord(state, seq, payload)

    def _open(self, flags: int, mode: int = 0o666) -> int:
        self._close()
        self.fd = os.open(self.path, flags, mode)
        return self.fd

    def _close(self) -> None:
        if self.fd != -1:
            try:
                os.close(self.fd)
            except OSError:
                pass
        self.fd = -1

    def init(self) -> None:
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o666)

        try:
            fcntl.flock(fd, fcntl.LOCK_EX)

            size = os.lseek(fd, 0, os.SEEK_END)
            if size == 0:
                os.lseek(fd, 0, os.SEEK_SET)
                line = f"{RecordType.Response.value};0;\n".encode()
                os.write(fd, line)
                os.fsync(fd)

        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        self.logger.debug(f"Opened file {self.path}")

    def read(self) -> TransportRecord:
        fd = self._ensure_file()

        os.lseek(fd, 0, os.SEEK_SET)
        data = os.read(fd, 4096)
        if not data:
            raise ValueError("empty file")
        first_line = data.splitlines()[0].decode()
        return self._parse_line(first_line)

    def write(self, state: RecordType, seq: int, payload: str) -> None:
        fd = self._ensure_file()
        line = f"{state.value};{seq};{payload}\n".encode()
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, line)
        os.fsync(fd)
        self.logger.debug(f"Wrote to file {self.path} (fd={fd}): {line.strip()}")

    @contextmanager
    def open_r(self):
        self._open(os.O_RDONLY)
        try:
            yield self
        finally:
            self._close()

    @contextmanager
    def open_rw_locked(self):
        fd = self._open(os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield self
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            self._close()