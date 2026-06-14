import time


class Storage:
    def __init__(self):
        # Struktur data: { key: {"value": any, "expires_at": float atau None} }
        self._kv_store = {}

    def set(self, key: str, value: any, ttl: int = None) -> str:
        """
        Menyimpan data dengan key dan value.
        Jika ttl (Time To Live) diisi (dalam satuan detik), hitung waktu kedaluwarsanya.
        """
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl

        self._kv_store[key] = {"value": value, "expires_at": expires_at}
        return "OK"

    def get(self, key: str) -> any:
        """
        Mengambil data berdasarkan key.
        Jika key sudah kedaluwarsa, hapus dari memori dan kembalikan None.
        """
        if key not in self._kv_store:
            return None

        data = self._kv_store[key]
        expires_at = data["expires_at"]

        # Cek apakah sudah kedaluwarsa (Lazy Expiration)
        if expires_at is not None and time.time() > expires_at:
            self.delete(key)  # Hapus secara pasif untuk menghemat memori
            return None

        return data["value"]

    def delete(self, key: str) -> int:
        """
        Menghapus key dari storage.
        Mengembalikan 1 jika key berhasil dihapus, atau 0 jika key tidak ditemukan.
        """
        if key in self._kv_store:
            del self._kv_store[key]
            return 1
        return 0

    def exists(self, key: str) -> int:
        """
        Memeriksa apakah suatu key ada dan belum kedaluwarsa.
        Mengembalikan 1 jika ada, 0 jika tidak ada.
        """
        # Kita panggil get(key) untuk memanfaatkan pengecekan expiry otomatis di atas
        if self.get(key) is not None:
            return 1
        return 0

    def get_expiry(self, key: str) -> float | None:
            if key not in self._kv_store:
                return None
            return self._kv_store[key]["expires_at"]


# --- CONTOH PENGGUNAAN ---
if __name__ == "__main__":
    db = Storage()

    print("--- Uji Coba SET dan GET biasa ---")
    print(db.set("nama", "Gemini"))  # OK
    print(db.get("nama"))  # Gemini

    print("\n--- Uji Coba EXISTS dan DELETE ---")
    print(db.exists("nama"))  # 1
    print(db.delete("nama"))  # 1
    print(db.get("nama"))  # None
    print(db.exists("nama"))  # 0

    print("\n--- Uji Coba EXPIRE (TTL: 2 detik) ---")
    db.set("session_token", "ABC123XYZ", ttl=2)
    print("Langsung ambil:", db.get("session_token"))  # ABC123XYZ

    print("Tunggu 2.5 detik...")
    time.sleep(2.5)

    print(
        "Ambil setelah delay:", db.get("session_token")
    )  # None (Sudah terhapus otomatis)
