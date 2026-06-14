import time

from storage import Storage


class CommandHandler:
    def __init__(self, storage: Storage):
        """
        Menerima instance dari Storage sebagai dependency injection.
        """
        self.storage = storage

    def handle(self, cmd_args: list) -> any:
        """
        Method utama untuk me-route/mengarahkan argumen dari client
        ke fungsi yang tepat secara dinamis.
        """
        if not cmd_args:
            return Exception("ERR empty command")

        # Ambil command utama (misal: "GET", "SET") dan jadikan uppercase
        cmd_name = str(cmd_args[0]).upper()
        args = cmd_args[1:]

        # Mapping string command ke method di class ini
        methods = {
            "PING": self.ping,
            "SET": self.set,
            "GET": self.get,
            "DEL": self.delete,
            "EXISTS": self.exists,
            "EXPIRE": self.expire,
            "TTL": self.ttl,
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
