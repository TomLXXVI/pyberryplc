from typing import Callable, Optional
import socket
import json
import time
# import select


class RemoteDeviceClient:
    """
    Client interface for communicating with a remote device over a network 
    socket connection.

    Provides a structured interface for establishing, managing, and terminating 
    a socket-based connection to a remote device, supporting command-based 
    communication and response handling.
    """
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 65432,
        logger: Optional[Callable[[str], None]] = None,
        timeout: float = 5,
        max_retries: int = 3,
        retry_delay: float = 2
    ) -> None:
        """
        Client for communicating with a remote device (slave) over a socket 
        connection.

        Parameters
        ----------
        host : str
            IP address or hostname of the remote device.
        port : int
            TCP port on which the remote device is listening.
        logger : Callable[[str], None] | None
            Logger function (e.g., self.logger.info) or None to use print.
        timeout : float
            Timeout in seconds for socket operations.
        max_retries : int
            Number of retries if connection fails.
        retry_delay : float
            Delay in seconds between retry attempts.
        """
        self.host: str = host
        self.port: int = port
        self.logger: Callable[[str], None] = logger or print
        self.timeout: float = timeout
        self.max_retries: int = max_retries
        self.retry_delay: float = retry_delay
        self.socket: Optional[socket.socket] = None
        self.stream: Optional[socket.SocketIO] = None

    def connect(self) -> None:
        """Establishes a connection to the remote device with retry mechanism."""
        attempt = 0
        while attempt < self.max_retries:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.timeout)
                self.socket.connect((self.host, self.port))
                self.stream = self.socket.makefile('r')
                self.socket.settimeout(None)
                self._log(f"Connected to device at {self.host}:{self.port}")
                return
            except Exception as e:
                attempt += 1
                self._log(f"Connection attempt {attempt} failed: {e}")
                time.sleep(self.retry_delay)
                continue
        raise ConnectionError(
            "Failed to connect to remote device after multiple attempts."
        )

    def send_command(self, command_dict: dict) -> None:
        """Sends a JSON-encoded command to the remote device."""
        msg = json.dumps(command_dict) + "\n"
        self.socket.sendall(msg.encode())

    def wait_for_done(self) -> None:
        """Waits for a JSON response from the remote device with status 'done'."""
        start_time = time.time()
        while True:
            if time.time() - start_time > self.timeout:
                raise TimeoutError(
                    "Timed out waiting for response from remote device."
                )
            # rlist, _, _ = select.select([self.socket], [], [], 0.1)
            # if rlist:
            line = self.stream.readline()
            if not line:
                raise ConnectionError(
                    "Connection to remote device was closed unexpectedly."
                )
            response = json.loads(line)
            if response.get("status") == "done":
                return
            elif response.get("status") == "error":
                raise RuntimeError(
                    f"Error from remote device: {response.get('message')}"
                )

    def shutdown(self) -> None:
        """Sends a shutdown command to the remote device."""
        try:
            self.send_command({"command": "shutdown"})
        except:
            self._log("Failed to send shutdown command.")

    def close(self) -> None:
        """Closes the socket connection."""
        try:
            if self.socket:
                self.socket.close()
        except:
            pass
        self._log("Connection to remote device closed.")

    def _log(self, msg: str) -> None:
        if callable(self.logger):
            self.logger(msg)
