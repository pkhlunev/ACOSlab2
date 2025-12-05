#!/usr/bin/env python3

import argparse
import logging
import time

from ipc_file import IPCFile, RecordType

DEFAULT_POLL_INTERVAL = 0.1
DEFAULT_IPC_PATH = "/tmp/ipc_file"


class Server:
    def __init__(self, ipc_path: str, poll_interval: float, debug: bool):
        self.poll_interval = poll_interval
        self.logger = logging.getLogger("server")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.ipc = IPCFile(ipc_path, self.logger)
        self.ipc.init()

    def handle_request(self) -> None:
        try:
            with self.ipc.open_rw_locked():
                try:
                    state, seq, payload = self.ipc.read_state()
                except ValueError as e:
                    self.ipc.write_state(RecordType.Error, 0, f"invalid_state:{e}")
                    self.logger.error(f"Invalid state: {e}")
                    return

                if state == RecordType.Request:
                    msg = payload.strip().lower()
                    if msg.lower() == "ping":
                        self.logger.info(f"Got request seq={seq}")
                        self.ipc.write_state(RecordType.Response, seq, "pong")
                    else:
                        self.logger.error(f"Got bad request seq={seq}, payload={payload}")
                        self.ipc.write_state(RecordType.Error, seq, "bad_request")
        except OSError as e:
            self.logger.error(f"Open error: {e}")
            time.sleep(self.poll_interval)
            return

    def start(self) -> None:
        self.logger.info(f"Server is started. Listening on {self.ipc.path}...")
        try:
            while True:
                self.handle_request()
                time.sleep(self.poll_interval)
        except (EOFError, KeyboardInterrupt):
            self.logger.info("Bye")


def main():
    parser = argparse.ArgumentParser(description="IPC file server")
    parser.add_argument(
        "-p",
        "--path",
        default=DEFAULT_IPC_PATH,
        help=f"Path to IPC file (default: {DEFAULT_IPC_PATH})",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL,
        help=f"Polling interval in seconds (default: {DEFAULT_POLL_INTERVAL})",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='[server %(levelname)-5s] %(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    server = Server(args.path, args.interval, args.debug)
    server.start()


if __name__ == "__main__":
    main()
