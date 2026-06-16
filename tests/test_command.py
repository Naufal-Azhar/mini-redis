import os
import time
import unittest

from protocol import RESPCodec
from storage import Storage
from commands import CommandHandler


class TestRESPCodec(unittest.TestCase):
    def test_encode_simple_string(self):
        self.assertEqual(RESPCodec.encode("OK"), b"$2\r\nOK\r\n")

    def test_encode_bulk_string(self):
        self.assertEqual(RESPCodec.encode("hello"), b"$5\r\nhello\r\n")

    def test_encode_null(self):
        self.assertEqual(RESPCodec.encode(None), b"$-1\r\n")

    def test_encode_integer(self):
        self.assertEqual(RESPCodec.encode(100), b":100\r\n")

    def test_encode_array(self):
        result = RESPCodec.encode(["SET", "name", "budi"])
        expected = b"*3\r\n$3\r\nSET\r\n$4\r\nname\r\n$4\r\nbudi\r\n"
        self.assertEqual(result, expected)

    def test_encode_empty_array(self):
        self.assertEqual(RESPCodec.encode([]), b"*0\r\n")

    def test_encode_bytes(self):
        self.assertEqual(RESPCodec.encode(b"raw"), b"$3\r\nraw\r\n")

    def test_parse_ping(self):
        data = b"*1\r\n$4\r\nPING\r\n"
        result, rest = RESPCodec.parse(data)
        self.assertEqual(result, ["PING"])
        self.assertEqual(rest, b"")

    def test_parse_set_get(self):
        data = b"*3\r\n$3\r\nSET\r\n$4\r\nname\r\n$4\r\nbudi\r\n"
        result, rest = RESPCodec.parse(data)
        self.assertEqual(result, ["SET", "name", "budi"])

    def test_parse_multiple_commands(self):
        data = b"*1\r\n$4\r\nPING\r\n*1\r\n$4\r\nPING\r\n"
        first, rest = RESPCodec.parse(data)
        self.assertEqual(first, ["PING"])
        second, rest2 = RESPCodec.parse(rest)
        self.assertEqual(second, ["PING"])

    def test_parse_bulk_string_null(self):
        data = b"$-1\r\n"
        result, rest = RESPCodec.parse(data)
        self.assertIsNone(result)

    def test_parse_simple_string(self):
        data = b"+OK\r\n"
        result, rest = RESPCodec.parse(data)
        self.assertEqual(result, "OK")

    def test_parse_error(self):
        data = b"-ERR something went wrong\r\n"
        result, rest = RESPCodec.parse(data)
        self.assertIsInstance(result, Exception)
        self.assertEqual(str(result), "ERR something went wrong")

    def test_parse_integer(self):
        data = b":42\r\n"
        result, rest = RESPCodec.parse(data)
        self.assertEqual(result, 42)

    def test_parse_empty_array(self):
        data = b"*0\r\n"
        result, rest = RESPCodec.parse(data)
        self.assertEqual(result, [])

    def test_parse_incomplete_data_returns_none(self):
        data = b"*1\r\n$4\r\nPIN"
        result, rest = RESPCodec.parse(data)
        self.assertIsNone(result)
        self.assertEqual(rest, data)

    def test_parse_empty_data(self):
        result, rest = RESPCodec.parse(b"")
        self.assertIsNone(result)
        self.assertEqual(rest, b"")

    def test_encode_then_parse_roundtrip(self):
        original = ["PING"]
        encoded = RESPCodec.encode(original)
        parsed, rest = RESPCodec.parse(encoded)
        self.assertEqual(parsed, original)

    def test_encode_then_parse_roundtrip_multi(self):
        original = ["SET", "key", "value with spaces"]
        encoded = RESPCodec.encode(original)
        parsed, rest = RESPCodec.parse(encoded)
        self.assertEqual(parsed, original)

    def test_encode_then_parse_integer_roundtrip(self):
        for val in [0, 1, -1, 1000, -999]:
            encoded = RESPCodec.encode(val)
            parsed, _ = RESPCodec.parse(encoded)
            self.assertEqual(parsed, val)


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.store = Storage()

    def test_set_and_get(self):
        self.store.set("name", "budi")
        self.assertEqual(self.store.get("name"), "budi")

    def test_get_nonexistent_key(self):
        self.assertIsNone(self.store.get("nonexistent"))

    def test_set_overwrites_existing(self):
        self.store.set("key", "value1")
        self.store.set("key", "value2")
        self.assertEqual(self.store.get("key"), "value2")

    def test_delete_existing_key(self):
        self.store.set("key", "value")
        self.assertEqual(self.store.delete("key"), 1)
        self.assertIsNone(self.store.get("key"))

    def test_delete_nonexistent_key(self):
        self.assertEqual(self.store.delete("nonexistent"), 0)

    def test_exists_returns_1(self):
        self.store.set("key", "value")
        self.assertEqual(self.store.exists("key"), 1)

    def test_exists_returns_0(self):
        self.assertEqual(self.store.exists("nonexistent"), 0)

    def test_exists_after_delete(self):
        self.store.set("key", "value")
        self.store.delete("key")
        self.assertEqual(self.store.exists("key"), 0)

    def test_expiry_key_expires(self):
        self.store.set("temp", "data", ttl=1)
        self.assertEqual(self.store.get("temp"), "data")
        time.sleep(1.5)
        self.assertIsNone(self.store.get("temp"))

    def test_expiry_not_expired(self):
        self.store.set("temp", "data", ttl=10)
        self.assertEqual(self.store.get("temp"), "data")

    def test_get_expiry_returns_float(self):
        self.store.set("key", "val", ttl=10)
        expiry = self.store.get_expiry("key")
        self.assertIsNotNone(expiry)
        self.assertIsInstance(expiry, float)

    def test_get_expiry_none_for_no_ttl(self):
        self.store.set("key", "val")
        self.assertIsNone(self.store.get_expiry("key"))

    def test_get_expiry_nonexistent(self):
        self.assertIsNone(self.store.get_expiry("nonexistent"))

    def test_exists_after_expiry(self):
        self.store.set("temp", "data", ttl=1)
        time.sleep(1.5)
        self.assertEqual(self.store.exists("temp"), 0)


class TestCommandHandler(unittest.TestCase):
    def setUp(self):
        self.store = Storage()
        self.handler = CommandHandler(self.store)

    def test_ping(self):
        result = self.handler.handle(["PING"])
        self.assertEqual(result, "PONG")

    def test_ping_with_arg(self):
        result = self.handler.handle(["PING", "hello"])
        self.assertEqual(result, "hello")

    def test_set_and_get(self):
        self.handler.handle(["SET", "user", "budi"])
        result = self.handler.handle(["GET", "user"])
        self.assertEqual(result, "budi")

    def test_get_nonexistent(self):
        result = self.handler.handle(["GET", "nonexistent"])
        self.assertIsNone(result)

    def test_set_with_ex(self):
        self.handler.handle(["SET", "temp", "data", "EX", "5"])
        self.assertEqual(self.handler.handle(["GET", "temp"]), "data")
        expiry = self.store.get_expiry("temp")
        self.assertIsNotNone(expiry)

    def test_delete_single(self):
        self.handler.handle(["SET", "key", "val"])
        result = self.handler.handle(["DEL", "key"])
        self.assertEqual(result, 1)
        self.assertIsNone(self.handler.handle(["GET", "key"]))

    def test_delete_multiple(self):
        self.handler.handle(["SET", "a", "1"])
        self.handler.handle(["SET", "b", "2"])
        result = self.handler.handle(["DEL", "a", "b"])
        self.assertEqual(result, 2)

    def test_delete_nonexistent(self):
        result = self.handler.handle(["DEL", "nonexistent"])
        self.assertEqual(result, 0)

    def test_exists_single(self):
        self.handler.handle(["SET", "key", "val"])
        self.assertEqual(self.handler.handle(["EXISTS", "key"]), 1)

    def test_exists_multiple(self):
        self.handler.handle(["SET", "a", "1"])
        self.handler.handle(["SET", "b", "2"])
        self.assertEqual(self.handler.handle(["EXISTS", "a", "b", "c"]), 2)

    def test_exists_nonexistent(self):
        self.assertEqual(self.handler.handle(["EXISTS", "nonexistent"]), 0)

    def test_expire_sets_ttl(self):
        self.handler.handle(["SET", "key", "val"])
        result = self.handler.handle(["EXPIRE", "key", "60"])
        self.assertEqual(result, 1)
        expiry = self.store.get_expiry("key")
        self.assertIsNotNone(expiry)

    def test_expire_nonexistent_key(self):
        result = self.handler.handle(["EXPIRE", "nonexistent", "60"])
        self.assertEqual(result, 0)

    def test_ttl_returns_positive(self):
        self.handler.handle(["SET", "key", "val"])
        self.handler.handle(["EXPIRE", "key", "60"])
        result = self.handler.handle(["TTL", "key"])
        self.assertGreater(result, 0)
        self.assertLessEqual(result, 60)

    def test_ttl_no_expiry(self):
        self.handler.handle(["SET", "key", "val"])
        result = self.handler.handle(["TTL", "key"])
        self.assertEqual(result, -1)

    def test_ttl_nonexistent(self):
        result = self.handler.handle(["TTL", "nonexistent"])
        self.assertEqual(result, -2)

    def test_ttl_expired_key(self):
        self.handler.handle(["SET", "temp", "data", "EX", "1"])
        time.sleep(1.5)
        result = self.handler.handle(["TTL", "temp"])
        self.assertEqual(result, -2)

    def test_empty_command_returns_error(self):
        result = self.handler.handle([])
        self.assertIsInstance(result, Exception)
        self.assertIn("empty", str(result).lower())

    def test_unknown_command_returns_error(self):
        result = self.handler.handle(["UNKNOWN"])
        self.assertIsInstance(result, Exception)
        self.assertIn("unknown command", str(result).lower())

    def test_wrong_number_of_args_returns_error(self):
        result = self.handler.handle(["GET"])
        self.assertIsInstance(result, Exception)
        self.assertIn("wrong number of arguments", str(result).lower())

    def test_save_and_load_roundtrip(self):
        self.handler.handle(["SET", "persist_key", "persist_val"])
        result = self.handler.handle(["SAVE"])
        self.assertEqual(result, "OK")

        store2 = Storage()
        store2.load_from_file()
        self.assertEqual(store2.get("persist_key"), "persist_val")

    def test_full_integration(self):
        self.assertEqual(self.handler.handle(["PING"]), "PONG")
        self.assertEqual(self.handler.handle(["SET", "key1", "val1"]), "OK")
        self.assertEqual(self.handler.handle(["SET", "key2", "val2"]), "OK")
        self.assertEqual(self.handler.handle(["GET", "key1"]), "val1")
        self.assertEqual(self.handler.handle(["EXISTS", "key1"]), 1)
        self.assertEqual(self.handler.handle(["DEL", "key1"]), 1)
        self.assertEqual(self.handler.handle(["EXISTS", "key1"]), 0)
        self.assertEqual(self.handler.handle(["EXPIRE", "key2", "100"]), 1)
        self.assertGreater(self.handler.handle(["TTL", "key2"]), 0)


def setUpModule():
    global _orig_exists
    _orig_exists = os.path.exists


def tearDownModule():
    if os.path.exists("dump.json"):
        os.remove("dump.json")


if __name__ == "__main__":
    unittest.main()
