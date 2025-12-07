#!/usr/bin/env python3

import argparse
import logging
import time

from transport_file import TransportFile, RecordType

DEFAULT_POLL_INTERVAL = 0.1
DEFAULT_TFILE_PATH = "/tmp/transport_file"


class Server:
    def __init__(self, tfile_path: str, poll_interval: float, debug: bool):
        self.poll_interval = poll_interval
        self.logger = logging.getLogger("server")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.tfile = TransportFile(tfile_path, self.logger)
        self.tfile.init()

    def handle_request(self) -> None:
        try:
            with self.tfile.open_rw_locked():
                try:
                    state, seq, payload = self.tfile.read()
                except ValueError as e:
                    self.tfile.write(RecordType.Error, 0, f"invalid_state:{e}")
                    self.logger.error(f"Invalid state: {e}")
                    return

                if state == RecordType.Request:
                    msg = payload.strip().lower()
                    if msg.lower() == "ping":
                        self.logger.info(f"Got request seq={seq}")
                        self.tfile.write(RecordType.Response, seq, "pong")
                    else:
                        self.logger.error(f"Got bad request seq={seq}, payload={payload}")
                        self.tfile.write(RecordType.Error, seq, "bad_request")
        except OSError as e:
            self.logger.error(f"Open error: {e}")
            time.sleep(self.poll_interval)
            return

    def start(self) -> None:
        self.logger.info(f"Server is started. Listening on {self.tfile.path}...")
        try:
            while True:
                self.handle_request()
                time.sleep(self.poll_interval)
        except (EOFError, KeyboardInterrupt):
            self.logger.info("Bye")


def main():
    parser = argparse.ArgumentParser(description="Transport file server")
    parser.add_argument(
        "-p",
        "--path",
        default=DEFAULT_TFILE_PATH,
        help=f"Path to transport file (default: {DEFAULT_TFILE_PATH})",
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
