#!/usr/bin/env python3

import argparse
import logging
import time

from ipc_file import IPCFile, RecordType

DEFAULT_TIMEOUT = 3.0
DEFAULT_POLL_INTERVAL = 0.1
DEFAULT_IPC_PATH = "/tmp/ipc_file"


class Client:
    def __init__(self, ipc_path: str, timeout: float, poll_interval: float, debug: bool):
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.logger = logging.getLogger("client")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.ipc = IPCFile(ipc_path, self.logger)

    def _write_request(self, payload: str):
        try:
            with self.ipc.open_rw_locked():
                try:
                    state, seq, _ = self.ipc.read_state()
                except ValueError as e:
                    self.logger.error(f"Invalid state in file: {e}")
                    new_seq = 1
                else:
                    if state == RecordType.Request:
                        self.logger.warning("Server busy (pending request)")
                        return None
                    new_seq = seq + 1

                self.ipc.write_state(RecordType.Request, new_seq, payload)
                self.logger.info(f"Sent request seq={new_seq}, payload={payload}")
                return new_seq
        except FileNotFoundError:
            self.logger.error("Server not available (file missing)")
            return None
        except OSError as e:
            self.logger.error(f"Open error: {e}")
            return None

    def _wait_response(self, seq: int) -> None:
        deadline = time.time() + self.timeout

        while time.time() < deadline:
            try:
                with self.ipc.open_r():
                    try:
                        state, r_seq, payload = self.ipc.read_state()
                    except ValueError as e:
                        self.logger.error(f"Invalid response: {e}")
                        return

                    if r_seq == seq:
                        if state == RecordType.Response:
                            self.logger.info(f"Got response seq={r_seq}, payload={payload}")
                            return
                        elif state == RecordType.Error:
                            self.logger.error(f"Got error seq={r_seq}, payload={payload}")
                            return
            except OSError as e:
                self.logger.error(f"Reopen error: {e}")
                return

            time.sleep(self.poll_interval)
        self.logger.error("Timeout waiting for response")

    def send(self, payload: str) -> None:
        seq = self._write_request(payload)
        if seq is None:
            return
        self._wait_response(seq)

    def run_shell(self) -> None:
        self.logger.info(f"Client is started. IPC file: {self.ipc.path}")
        self.logger.info("Available commands: ping | any_text (as payload) | exit/quit/q")
        while True:
            try:
                cmd = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.logger.info("Bye")
                break

            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit", "q"):
                self.logger.info("Bye")
                break

            self.send(cmd)


def main():
    parser = argparse.ArgumentParser(description="IPC file client")
    parser.add_argument(
        "-p",
        "--path",
        default=DEFAULT_IPC_PATH,
        help=f"Path to IPC file (default: {DEFAULT_IPC_PATH})",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout waiting for server response in seconds (default: {DEFAULT_TIMEOUT})",
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
        format='[client %(levelname)-5s] %(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    client = Client(args.path, args.timeout, args.interval, args.debug)
    client.run_shell()


if __name__ == "__main__":
    main()
