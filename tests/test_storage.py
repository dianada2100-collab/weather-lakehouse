import pandas as pd
import pytest

from weather_pipeline.config import Settings
from weather_pipeline.storage import LocalStorage, get_storage


def test_local_json_roundtrip_and_listing(tmp_path):
    s = LocalStorage(tmp_path)
    s.write_json("a/b/one.json", {"x": 1})
    s.write_json("a/c/two.json", {"x": 2})
    assert s.read_json("a/b/one.json") == {"x": 1}
    assert s.list_keys("a/") == ["a/b/one.json", "a/c/two.json"]
    assert s.list_keys("missing/") == []


def test_local_overwrite_is_idempotent(tmp_path):
    s = LocalStorage(tmp_path)
    s.write_json("k.json", {"v": 1})
    s.write_json("k.json", {"v": 2})
    assert s.read_json("k.json") == {"v": 2}
    assert s.list_keys("") == ["k.json"]                 # no leftover .tmp files


def test_local_parquet_roundtrip(tmp_path):
    pytest.importorskip("pyarrow")
    s = LocalStorage(tmp_path)
    df = pd.DataFrame({"a": [1, 2], "b": [0.5, 1.5]})
    s.write_parquet("t/data.parquet", df)
    pd.testing.assert_frame_equal(s.read_parquet("t/data.parquet"), df)


def test_get_storage_backends(tmp_path):
    assert isinstance(get_storage(Settings("local", str(tmp_path), "", "")), LocalStorage)
    with pytest.raises(ValueError):
        get_storage(Settings("ftp", "", "", ""))
