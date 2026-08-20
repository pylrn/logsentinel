from datetime import UTC

import pytest

from logsentinel.data import DatasetAdapter, iter_public_records
from logsentinel.parsing import DrainTemplateParser
from logsentinel.schemas import DatasetName


def test_hdfs_adapter_hashes_group_before_redacting_message() -> None:
    record = {
        "date": "081109",
        "time": "203518",
        "component": "dfs.DataNode$DataXceiver",
        "level": "INFO",
        "content": "Receiving block blk_-1608999687919862906 from 10.250.19.102:54106",
        "block_id": "blk_-1608999687919862906",
        "anomaly": 1,
    }
    event = DatasetAdapter(DatasetName.HDFS).normalize(record)
    assert event.timestamp.tzinfo == UTC
    assert event.group_hash is not None
    assert "blk_-1608999687919862906" not in event.message
    assert "10.250.19.102" not in event.message
    assert "<BLOCK_ID>" in event.message
    assert "<IP>" in event.message


def test_bgl_adapter_uses_epoch_timestamp_and_hashes_host() -> None:
    record = {
        "timestamp": 1_117_838_570,
        "node": "R02-M1-N0-C:J12-U11",
        "component": "KERNEL",
        "level": "INFO",
        "content": "instruction cache parity error corrected",
        "anomaly": 0,
    }
    event = DatasetAdapter(DatasetName.BGL).normalize(record)
    assert event.timestamp.tzinfo == UTC
    assert event.timestamp.timestamp() == 1_117_838_570
    assert event.host_hash != record["node"]
    assert event.group_hash is None


def test_adapter_rejects_missing_hdfs_block_identifier() -> None:
    adapter = DatasetAdapter(DatasetName.HDFS)
    with pytest.raises(ValueError, match="block_id"):
        adapter.normalize(
            {
                "date": "081109",
                "time": "203518",
                "component": "DataNode",
                "level": "INFO",
                "content": "message",
                "anomaly": 0,
            }
        )


def test_iter_public_records_is_lazy_and_respects_limit() -> None:
    requested: dict[str, object] = {}

    def loader(name: str, *, split: str, streaming: bool):
        requested.update(name=name, split=split, streaming=streaming)
        return iter(
            [
                {
                    "timestamp": 1_117_838_570 + index,
                    "node": "node",
                    "component": "kernel",
                    "level": "INFO",
                    "content": f"event {index}",
                    "anomaly": 0,
                }
                for index in range(5)
            ]
        )

    events = list(iter_public_records(DatasetName.BGL, limit=2, loader=loader))
    assert len(events) == 2
    assert requested == {
        "name": "logfit-project/BGL",
        "split": "train",
        "streaming": True,
    }


def test_drain_parser_redacts_before_fitting_and_does_not_mutate_during_match() -> None:
    class Cluster:
        cluster_id = 7

        def get_template(self):
            return "login from <IP>"

    class FakeDrain:
        def __init__(self) -> None:
            self.fitted: list[str] = []
            self.matched: list[str] = []

        def add_log_message(self, message: str):
            self.fitted.append(message)
            return {"cluster_id": 7, "template_mined": "login from <IP>"}

        def match(self, message: str, **_kwargs):
            self.matched.append(message)
            return Cluster() if message.startswith("login") else None

    backend = FakeDrain()
    parser = DrainTemplateParser(backend=backend)
    trained = parser.fit("login from 10.1.2.3 token=secret-value")
    matched = parser.transform("login from 10.9.8.7 token=other-value")
    unknown = parser.transform("never seen 10.0.0.1")
    assert trained.event_id == matched.event_id
    assert unknown.event_id == "<UNK>"
    assert all("secret-value" not in message for message in backend.fitted)
    assert all("other-value" not in message for message in backend.matched)
