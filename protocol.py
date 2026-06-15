class RESPCodec:
    @staticmethod
    def parse(data: bytes) -> tuple[any, bytes]:
        if not data:
            return None, b""

        if b"\r\n" not in data:
            return None, data

        line, rest = data.split(b"\r\n", 1)
        prefix = line[0:1]
        value = line[1:]

        if prefix == b"$":
            length = int(value)
            if length == -1:
                return None, rest

            if len(rest) < length + 2:
                return None, data

            bulk_data = rest[:length]
            remaining_data = rest[length + 2 :]
            return bulk_data.decode("utf-8"), remaining_data

        elif prefix == b"*":
            count = int(value)
            if count == -1:
                return None, rest

            items = []
            current_data = rest
            for _ in range(count):
                prev_data = current_data
                item, current_data = RESPCodec.parse(current_data)
                if item is None and current_data == prev_data:
                    return None, data
                items.append(item)
            return items, current_data

        elif prefix == b"+":
            return value.decode("utf-8"), rest

        elif prefix == b"-":
            return Exception(value.decode("utf-8")), rest

        elif prefix == b":":
            return int(value), rest

        else:
            raise ValueError(f"RESP unknown prefix: {prefix}")

    @staticmethod
    def encode(value: any) -> bytes:
        if value is None:
            return b"$-1\r\n"

        elif isinstance(value, int) and not isinstance(value, bool):
            return f":{value}\r\n".encode("utf-8")

        elif isinstance(value, (list, tuple)):
            res = f"*{len(value)}\r\n".encode("utf-8")
            for item in value:
                res += RESPCodec.encode(item)
            return res

        elif isinstance(value, str):
            encoded = value.encode("utf-8")
            return f"${len(encoded)}\r\n".encode("utf-8") + encoded + b"\r\n"

        elif isinstance(value, bytes):
            return f"${len(value)}\r\n".encode("utf-8") + value + b"\r\n"

        elif isinstance(value, Exception):
            return f"-{str(value)}\r\n".encode("utf-8")

        else:
            raise TypeError(f"Unsupported type: {type(value)}")


if __name__ == "__main__":
    print("--- ENCODE TEST ---")
    print(repr(RESPCodec.encode("OK")))
    print(repr(RESPCodec.encode(100)))
    print(repr(RESPCodec.encode(["GET", "name"])))

    print("\n--- PARSE TEST ---")
    req = b"*1\r\n$4\r\nPING\r\n"
    parsed, _ = RESPCodec.parse(req)
    print(f"Result: {parsed}")
