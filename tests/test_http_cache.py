import concurrent.futures as cf
import os
import tempfile

from core.http_cache import _write_json


def test_concurrent_writes_same_key():
    # Every team thread fetches the same team-id map on a cold start; none of them may fail.
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "same.json")
        with cf.ThreadPoolExecutor(16) as ex:
            list(ex.map(lambda i: _write_json(path, {"i": i}), range(200)))
        assert os.path.exists(path)
        assert not [f for f in os.listdir(d) if f.endswith(".tmp")]


if __name__ == "__main__":
    test_concurrent_writes_same_key()
    print("ok")
