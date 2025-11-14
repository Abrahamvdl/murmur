"""IPC server for handling communication between CLI and daemon."""

import json
import logging
import os
import socket
import threading
from pathlib import Path
from typing import Callable, Dict, Any


logger = logging.getLogger(__name__)


class IPCServer:
    """Unix socket server for inter-process communication."""

    def __init__(self, socket_path: str = "/tmp/whisper-daemon.sock"):
        self.socket_path = socket_path
        self.server_socket = None
        self.running = False
        self.command_handlers: Dict[str, Callable] = {}
        self.lock = threading.Lock()

    def register_handler(self, command: str, handler: Callable):
        """Register a command handler function."""
        with self.lock:
            self.command_handlers[command] = handler
        logger.debug(f"Registered handler for command: {command}")

    def start(self):
        """Start the IPC server."""
        # Remove existing socket file if it exists
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        # Create socket directory if it doesn't exist
        socket_dir = Path(self.socket_path).parent
        socket_dir.mkdir(parents=True, exist_ok=True)

        # Create Unix domain socket
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(5)

        # Set socket permissions so user can connect
        os.chmod(self.socket_path, 0o600)

        self.running = True
        logger.info(f"IPC server started on {self.socket_path}")

        # Start accepting connections in a separate thread
        threading.Thread(target=self._accept_connections, daemon=True).start()

    def _accept_connections(self):
        """Accept and handle incoming connections."""
        while self.running:
            try:
                client_socket, _ = self.server_socket.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True
                ).start()
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")

    def _handle_client(self, client_socket: socket.socket):
        """Handle a client connection."""
        try:
            # Receive data (max 4KB)
            data = client_socket.recv(4096).decode("utf-8")
            if not data:
                return

            # Parse command
            try:
                message = json.loads(data)
                command = message.get("command")
                args = message.get("args", {})
            except json.JSONDecodeError:
                response = {"status": "error", "message": "Invalid JSON"}
                client_socket.sendall(json.dumps(response).encode("utf-8"))
                return

            # Execute command handler
            with self.lock:
                handler = self.command_handlers.get(command)

            if handler:
                try:
                    result = handler(**args)
                    response = {"status": "success", "result": result}
                except Exception as e:
                    logger.error(f"Error executing command '{command}': {e}", exc_info=True)
                    response = {"status": "error", "message": str(e)}
            else:
                response = {"status": "error", "message": f"Unknown command: {command}"}

            # Send response
            client_socket.sendall(json.dumps(response).encode("utf-8"))

        except Exception as e:
            logger.error(f"Error handling client: {e}", exc_info=True)
        finally:
            client_socket.close()

    def stop(self):
        """Stop the IPC server."""
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"Error closing server socket: {e}")

        # Remove socket file
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except Exception as e:
                logger.error(f"Error removing socket file: {e}")

        logger.info("IPC server stopped")


class IPCClient:
    """Client for communicating with the daemon via Unix socket."""

    def __init__(self, socket_path: str = "/tmp/whisper-daemon.sock"):
        self.socket_path = socket_path

    def send_command(self, command: str, **args) -> Dict[str, Any]:
        """Send a command to the daemon and return the response."""
        try:
            # Connect to daemon
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.settimeout(5.0)  # 5 second timeout
            client_socket.connect(self.socket_path)

            # Send command
            message = {"command": command, "args": args}
            client_socket.sendall(json.dumps(message).encode("utf-8"))

            # Receive response
            data = client_socket.recv(4096).decode("utf-8")
            response = json.loads(data)

            client_socket.close()
            return response

        except FileNotFoundError:
            return {
                "status": "error",
                "message": "Daemon is not running. Start it with: systemctl --user start whisper-daemon"
            }
        except socket.timeout:
            return {"status": "error", "message": "Command timed out"}
        except Exception as e:
            return {"status": "error", "message": f"Communication error: {str(e)}"}
