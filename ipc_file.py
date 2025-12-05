import fcntl
import logging
import os
from contextlib import contextmanager
from enum import IntEnum
from typing import IO, NamedTuple


class RecordType(IntEnum):
    Error = -1
    Response = 0
    Request = 1


class IPCRecord(NamedTuple):
    state: RecordType
    seq: int
    payload: str



class IPCFile:
    def __init__(self, path: str, logger: logging.Logger) -> None:
        self.path = path
        self.file = None
        self.logger = logger

    def _ensure_file(self) -> IO:
        if self.file is None or self.file.closed:
            raise ValueError("file is not opened")
        return self.file

    def close(self) -> None:
        if self.file is not None and not self.file.closed:
            self.file.close()
        self.file = None

    def init(self) -> None:
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o666)
        f = os.fdopen(fd, "r+", buffering=1)
        with f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0, os.SEEK_END)
            if f.tell() == 0:
                f.seek(0)
                f.write(f"{RecordType.Response.value};0;\n")
                f.flush()
                os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)
        self.logger.debug(f"Opened file {self.path}")

    @staticmethod
    def _parse_line(line: str) -> IPCRecord:
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
        return IPCRecord(state, seq, payload)

    def read_state(self) -> IPCRecord:
        file = self._ensure_file()
        file.seek(0)
        data = file.read()
        if not data:
            raise ValueError("empty file")
        line = data.splitlines()[0]
        return self._parse_line(line)

    def write_state(self, state: RecordType, seq: int, payload: str) -> None:
        file = self._ensure_file()
        line = f"{state.value};{seq};{payload}\n"
        file.seek(0)
        file.truncate()
        file.write(line)
        file.flush()
        os.fsync(file.fileno())
        self.logger.debug(f"Wrote to file {self.path} (fd={file.fileno()}): {line.strip()}")

    def _open(self, flags: int, mode: str) -> IO:
        self.close()
        fd = os.open(self.path, flags)
        self.file = os.fdopen(fd, mode, buffering=1)
        return self.file

    @contextmanager
    def open_r(self):
        self._open(os.O_RDONLY, "r")
        try:
            yield self
        finally:
            self.close()

    @contextmanager
    def open_rw_locked(self):
        f = self._open(os.O_RDWR, "r+")
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            yield self
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            self.close()
