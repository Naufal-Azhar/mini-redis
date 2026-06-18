import json
import os
import threading
import time
import fnmatch


class Storage:

    def incr(self, key: str) -> int:
        current_val = self.get(key)

        if current_val is None:
            new_val = 1
        else:
            try:
                new_val = int(current_val) + 1
            except (ValueError, TypeError):
                raise Exception("ERR value is not an integer or out of range")

        self.set(key, str(new_val))
        return new_val

    def append(self, key: str, value: str) -> int:
        current_val = self.get(key)

        if current_val is None:
            new_val = value
        else:
            new_val = str(current_val) + value

        self.set(key, new_val)
        return len(new_val)

    def get_all_keys(self, pattern: str) -> list:
        matched_keys = []
        now = time.time()

        for k, v in list(self._kv_store.items()):
            if v["expires_at"] is not None and now > v["expires_at"]:
                del self._kv_store[k]
                continue

            if fnmatch.fnmatch(k, pattern):
                matched_keys.append(k)

        return matched_keys

    def __init__(self):
        self._kv_store = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: any, ttl: int = None) -> str:
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl

        self._kv_store[key] = {"value": value, "expires_at": expires_at}
        return "OK"

    def get(self, key: str) -> any:
        if key not in self._kv_store:
            return None

        data = self._kv_store[key]
        expires_at = data["expires_at"]

        if expires_at is not None and time.time() > expires_at:
            self.delete(key)
            return None

        return data["value"]

    def delete(self, key: str) -> int:
        if key in self._kv_store:
            del self._kv_store[key]
            return 1
        return 0

    def exists(self, key: str) -> int:
        if self.get(key) is not None:
            return 1
        return 0

    def get_expiry(self, key: str) -> float | None:
        if key not in self._kv_store:
            return None
        return self._kv_store[key]["expires_at"]

    def save_to_file(self, filepath="dump.json"):
        with self._lock:
            try:
                with open(filepath, "w") as f:
                    json.dump(self._kv_store, f, indent=4)
                print(f"[RDB] Snapshot saved to {filepath}")
                return True
            except Exception as e:
                print(f"[RDB Error] Failed to save: {e}")
                return False

    def load_from_file(self, filepath="dump.json"):
        if not os.path.exists(filepath):
            return False

        with self._lock:
            try:
                with open(filepath, "r") as f:
                    raw_data = json.load(f)

                now = time.time()
                self._kv_store = {
                    k: v
                    for k, v in raw_data.items()
                    if v["expires_at"] is None or v["expires_at"] > now
                }
                print(f"[RDB] Loaded {len(self._kv_store)} keys from {filepath}")
                return True
            except Exception as e:
                print(f"[RDB Error] Failed to load: {e}")
                return False


if __name__ == "__main__":
    db = Storage()

    print("--- SET & GET ---")
    print(db.set("nama", "Gemini"))
    print(db.get("nama"))

    print("\n--- EXISTS & DELETE ---")
    print(db.exists("nama"))
    print(db.delete("nama"))
    print(db.get("nama"))
    print(db.exists("nama"))

    print("\n--- EXPIRE (TTL: 2 detik) ---")
    db.set("session_token", "ABC123XYZ", ttl=2)
    print("Ambil:", db.get("session_token"))

    print("Tunggu 2.5 detik...")
    time.sleep(2.5)
    print("Ambil setelah delay:", db.get("session_token"))
