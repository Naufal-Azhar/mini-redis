# 🔴 Mini-Redis — 1 Week Challenge

Build Redis dari scratch pake Python murni. Tanpa library eksternal.

## Struktur Project

```
mini-redis/
├── server.py        ← Entry point, TCP server
├── protocol.py      ← RESP protocol parser
├── storage.py       ← In-memory storage engine
├── commands.py      ← Command handler (SET, GET, dll)
├── README.md
└── tests/
    └── test_commands.py
```

## Cara Jalanin

```bash
# Jalanin server
python server.py

# Di terminal lain, konek pake redis-cli
redis-cli -p 6379

# Coba command
127.0.0.1:6379> PING
PONG
127.0.0.1:6379> SET nama Budi
OK
127.0.0.1:6379> GET nama
"Budi"
```

## Cara Jalanin Tests

```bash
python -m unittest tests/test_commands.py -v
```

## Roadmap Mingguan

| Hari | Target                          |
| ---- | ------------------------------- |
| 1-2  | TCP server + PING jalan         |
| 3-4  | SET, GET, DEL, EXISTS           |
| 5-6  | EXPIRE, TTL, concurrent clients |
| 7    | Polish, README, push ke GitHub  |

## Commands yang Harus Diimplementasi

- [x] `PING` — test koneksi
- [ ] `SET key value` — simpen data
- [ ] `GET key` — ambil data
- [ ] `DEL key` — hapus data
- [ ] `EXISTS key` — cek keberadaan key
- [ ] `EXPIRE key seconds` — set waktu kedaluwarsa
- [ ] `TTL key` — cek sisa waktu

## BONUS Commands (kalau waktunya masih)

- [ ] `INCR key` — increment integer
- [ ] `APPEND key value` — append string
- [ ] `MSET` / `MGET` — set/get multiple keys

## Definisi Lulus

> Jalanin `redis-cli`, lalu `SET nama "Budi"` → `GET nama` → balik `"Budi"`.
> Kalau itu jalan, lo LULUS. ✅
