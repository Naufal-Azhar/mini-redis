import time

from protocol import RESPCodec
from storage import Storage


class CommandHandler:
    def __init__(self, storage: Storage):
        self.storage = storage

        # state baru untuk menampung pubsub
        self.channels = {}

    def handle(self, cmd_args: list, client_socket=None) -> any:
        if not cmd_args:
            return Exception("ERR empty command")

        cmd_name = str(cmd_args[0]).upper()
        args = cmd_args[1:]

        # Intersepsi khusus untuk SUBSCRIBE karena butuh object client_socket
        if cmd_name == "SUBSCRIBE":
            if not args:
                return Exception(
                    "ERR wrong number of arguments fot 'subscribe' command"
                )
            return self.subscribe(client_socket, *args)

        # Mapping string command ke method di class ini
        methods = {
            "PING": self.ping,
            "SET": self.set,
            "GET": self.get,
            "DEL": self.delete,
            "EXISTS": self.exists,
            "EXPIRE": self.expire,
            "TTL": self.ttl,
            "SAVE": self.save,
            "PUBLISH": self.publish,
            "INCR": self.incr,
            "APPEND": self.append,
            "MSET": self.mset,
            "MGET": self.mget,
            "KEYS": self.keys,
        }

        if cmd_name in methods:
            try:
                return methods[cmd_name](*args)
            except TypeError:
                # Menangani jika jumlah argumen yang dikirim client salah
                return Exception(
                    f"ERR wrong number of arguments for '{cmd_name.lower()}' command"
                )
        else:
            return Exception(f"ERR unknown command '{cmd_name.lower()}'")

    # === IMPLEMENTASI EXTENDED COMMANDS ===

    def incr(self, key: str):
        try:
            return self.storage.incr(key)
        except Exception as e:
            return e

    def append(self, key: str, value: str):
        return self.storage.append(key, value)

    def mset(self, *args) -> str:
        if len(args) % 2 != 0:
            return Exception("ERR wrong number of arguments for 'mset' command")

        for i in range(0, len(args), 2):
            self.storage.set(args[i], args[i+1])
        return "OK"

    def mget(self, *keys) -> list:
        return [self.storage.get(key) for key in keys]

    def keys(self, pattern: str) -> list:
        return self.storage.get_all_keys(pattern)


    def subscribe(self, client_socket,  *channel_names):
        responses = []
        for channel in channel_names:
            if channel not in self.channels:
                self.channels[channel] = set()

            self.channels[channel].add(client_socket)
            count = len(self.channels[channel])

            # karena client bisa subscribe ke banyak channel sekaligus, kita return per-channel
            responses.append(["subscribe", channel, count])

        # kembalikan sebagai list nested agar nanti di-encode jadi array oleh server
        return responses

    # === LOGIKA BARU: PUBLISH ===
    def publish(self, channel: str, message: str) -> int:
        if channel not in self.channels or not self.channels[channel]:
            return 0

        pubsub_msg = ["message", channel, message]
        encode_msg = RESPCodec.encode(pubsub_msg)

        subscribers_dead = []
        for sock in self.channels[channel]:
            try:
                sock.sendall(encode_msg)
            except Exception:
                subscribers_dead.append(sock)

        for dead_sock in subscribers_dead:
            self.unsubscribe_client(dead_sock)

        return len(self.channels[channel]) - len(subscribers_dead)

    # === LOGIKA BARU: CLEANUP DISCONNECT ===
    def unsubscribe_client(self, client_socket):
        for channel, subscribers in list(self.channels.items()):
            if client_socket in subscribers:
                subscribers.remove(client_socket)

            # ini opsional : hapus nama dari dict kalau udah ga ada subscribers sama sekali
            if not subscribers:
                del self.channels[channel]

    def ping(self, *args) -> str:
        # PING bisa menerima argumen opsional (misal: PING "halo" -> return "halo")
        if args:
            return args[0]
        return "PONG"

    def set(self, key: str, value: any, *args) -> str:
        # Mendukung syntax opsional: SET key value EX seconds
        ttl = None
        if len(args) >= 2 and str(args[0]).upper() == "EX":
            ttl = int(args[1])

        return self.storage.set(key, value, ttl=ttl)

    def get(self, key: str) -> any:
        return self.storage.get(key)

    def delete(self, *keys) -> int:
        # Redis DEL bisa menghapus banyak key sekaligus dan me-return total key yang terhapus
        count = 0
        for key in keys:
            count += self.storage.delete(key)
        return count

    def exists(self, *keys) -> int:
        # Redis EXISTS bisa mengecek banyak key sekaligus dan me-return total key yang ada
        count = 0
        for key in keys:
            count += self.storage.exists(key)
        return count

    def expire(self, key: str, seconds: str) -> int:
        value = self.storage.get(key)
        if value is None:
            return 0
        self.storage.set(key, value, ttl=int(seconds))
        return 1

    def ttl(self, key: str) -> int:
        if not self.storage.exists(key):
            return -2

        expires_at = self.storage.get_expiry(key)
        if expires_at is None:
            return -1

        sisa = int(round(expires_at - time.time()))
        if sisa <= 0:
            self.storage.delete(key)
            return -2
        return sisa

    def save(self) -> str:
        self.storage.save_to_file()
        return "OK"


# --- CONTOH PENGGUNAAN ---
if __name__ == "__main__":
    store = Storage()
    handler = CommandHandler(store)

    print("--- Test PING ---")
    print(handler.handle(["PING"]))  # PONG
    print(handler.handle(["PING", "hello"]))  # hello

    print("\n--- Test SET & GET ---")
    print(handler.handle(["SET", "user", "budi"]))  # OK
    print(handler.handle(["GET", "user"]))  # budi

    print("\n--- Test EXPIRE & TTL ---")
    print(handler.handle(["EXPIRE", "user", "10"]))  # 1 (Sukses)
    print(handler.handle(["TTL", "user"]))  # Sisa detik (misal: 10)

    print("\n--- Test Error Handling ---")
    print(handler.handle(["GET"]))  # Exception: ERR wrong number of arguments...
    print(handler.handle(["UNKNOWN_CMD"]))  # Exception: ERR unknown command...
