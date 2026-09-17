from defiagent_x_lite.canonical import canonical_bytes, sha256_hex


def test_canonical_key_order_is_stable() -> None:
    assert canonical_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    assert sha256_hex({"b": 2, "a": 1}) == sha256_hex({"a": 1, "b": 2})

