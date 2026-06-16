import selectors
import socket
import time

from commands import CommandHandler
from protocol import RESPCodec
from storage import Storage


class MiniRedisServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 6379):
        self.host = host
        self.port = port
        self.selector = selectors.DefaultSelector()

        self.storage = Storage()
        self.handler = CommandHandler(self.storage)

        self.client_buffers = {}

    def start(self):
        self.storage.load_from_file()

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        server_socket.setblocking(False)

        self.selector.register(
            server_socket, selectors.EVENT_READ, data=self.accept_connection
        )

        print(f"Mini Redis Server running on {self.host}:{self.port}...")

        last_save = time.time()
        try:
            while True:
                events = self.selector.select(timeout=5)

                if time.time() - last_save > 60:
                    self.storage.save_to_file()
                    last_save = time.time()

                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj)
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            self.storage.save_to_file()
            self.selector.close()

    def accept_connection(self, server_socket):
        client_socket, client_address = server_socket.accept()
        print(f"Client connected: {client_address}")

        client_socket.setblocking(False)
        self.selector.register(
            client_socket, selectors.EVENT_READ, data=self.handle_client
        )
        self.client_buffers[client_socket] = b""

    def handle_client(self, client_socket):
        try:
            data = client_socket.recv(1024)

            if not data:
                self.close_connection(client_socket)
                return

            self.client_buffers[client_socket] += data

            while True:
                current_buffer = self.client_buffers[client_socket]

                cmd_args, remainder = RESPCodec.parse(current_buffer)

                if cmd_args is None:
                    break

                self.client_buffers[client_socket] = remainder

                raw_response = self.handler.handle(cmd_args)

                encoded_response = RESPCodec.encode(raw_response)

                client_socket.sendall(encoded_response)

                if not self.client_buffers[client_socket]:
                    break

        except ConnectionResetError:
            self.close_connection(client_socket)

    def close_connection(self, client_socket):
        print("Client disconnected.")
        if client_socket in self.client_buffers:
            del self.client_buffers[client_socket]
        self.selector.unregister(client_socket)
        client_socket.close()


if __name__ == "__main__":
    server = MiniRedisServer()
    server.start()
