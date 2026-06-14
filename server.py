import selectors
import socket

from commands import CommandHandler
from protocol import RESPCodec
from storage import Storage


class MiniRedisServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 6379):
        self.host = host
        self.port = port
        self.selector = selectors.DefaultSelector()

        # Inisialisasi Storage Engine dan Command Handler
        self.storage = Storage()
        self.handler = CommandHandler(self.storage)

        # Buffer untuk menyimpan data stream per client socket
        # Struktur: { socket_obj: bytes_buffer }
        self.client_buffers = {}

    def start(self):
        # 1. Bikin TCP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Mengizinkan reuse port agar tidak error 'Address already in use' saat restart
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind ke host dan port (Default Redis: 6379)
        server_socket.bind((self.host, self.port))

        # 2. Listen untuk koneksi masuk
        server_socket.listen()
        server_socket.setblocking(False)  # Set non-blocking untuk selector

        # Daftarkan server_socket ke selector untuk memantau koneksi baru (EVENT_READ)
        self.selector.register(
            server_socket, selectors.EVENT_READ, data=self.accept_connection
        )

        print(f"🚀 Mini Redis Server berjalan di {self.host}:{self.port}...")

        # Main Server Loop
        try:
            while True:
                # Menunggu event I/O siap
                events = self.selector.select(timeout=None)
                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj)
        except KeyboardInterrupt:
            print("\n👋 Menutup server Mini Redis...")
        finally:
            self.selector.close()

    def accept_connection(self, server_socket):
        """Menerima koneksi baru dari client."""
        client_socket, client_address = server_socket.accept()
        print(f"🔌 Client terhubung dari: {client_address}")

        client_socket.setblocking(False)
        # Daftarkan client_socket ke selector untuk membaca data perintah (EVENT_READ)
        self.selector.register(
            client_socket, selectors.EVENT_READ, data=self.handle_client
        )
        # Inisialisasi buffer kosong untuk client ini
        self.client_buffers[client_socket] = b""

    def handle_client(self, client_socket):
        """Membaca data dari client, memproses command, dan mengirim balik response."""
        try:
            # 3. Terima data dari client (baca chunk 1024 bytes)
            data = client_socket.recv(1024)

            if not data:
                # Jika data kosong, artinya client memutus koneksi
                self.close_connection(client_socket)
                return

            # Tambahkan data yang baru masuk ke dalam buffer client tersebut
            self.client_buffers[client_socket] += data

            # Loop untuk menghandle jika client mengirim beberapa perintah sekaligus (pipelining)
            while True:
                current_buffer = self.client_buffers[client_socket]

                # 4. Parse data pake protocol.parse()
                cmd_args, remainder = RESPCodec.parse(current_buffer)

                # Jika hasil parse None, berarti data di buffer belum lengkap (nunggu data berikutnya)
                if cmd_args is None:
                    break

                # Update buffer dengan sisa data yang belum diproses
                self.client_buffers[client_socket] = remainder

                # 5 & 6. Routing dan Panggil method di CommandHandler
                # Format cmd_args dari RESP Array adalah list (contoh: ['SET', 'nama', 'budi'])
                raw_response = self.handler.handle(cmd_args)

                # 7. Encode response pake RESPCodec.encode()
                encoded_response = RESPCodec.encode(raw_response)

                # 8. Kirim balik ke client
                client_socket.sendall(encoded_response)

                # Jika buffer sudah habis, keluar dari loop internal
                if not self.client_buffers[client_socket]:
                    break

        except ConnectionResetError:
            # Mengatasi jika client terputus paksa (misal aplikasi di-force close)
            self.close_connection(client_socket)

    def close_connection(self, client_socket):
        """Membersihkan resource saat client terputus."""
        print("❌ Client terputus.")
        if client_socket in self.client_buffers:
            del self.client_buffers[client_socket]
        self.selector.unregister(client_socket)
        client_socket.close()


if __name__ == "__main__":
    # Jalankan server
    server = MiniRedisServer()
    server.start()
