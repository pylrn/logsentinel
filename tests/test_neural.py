from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
import torch

from logsentinel.detection import EncodedSequence
from logsentinel.neural import (
    DeepLogDetector,
    DeepLogModel,
    EventTokenCodec,
    QLoRADependencies,
    QLoRASettings,
    make_next_event_examples,
    next_event_statistics,
    prepare_qwen_qlora,
    train_qwen_adapter,
)


def test_event_token_codec_freezes_vocabulary_and_round_trips() -> None:
    codec = EventTokenCodec.fit([("E2", "E1"), ("E1", "E3")])
    assert codec.tokens == ("<EVT_000000>", "<EVT_000001>", "<EVT_000002>")
    serialized = codec.serialize(("E1", "E3", "UNKNOWN"))
    assert serialized.endswith("<EVT_UNK>")
    assert codec.deserialize(serialized.split()) == ("E1", "E3", "<UNK>")
    assert codec.event_ids == ("E1", "E2", "E3")


def test_deeplog_forward_shape_and_input_validation() -> None:
    model = DeepLogModel(vocabulary_size=5, embedding_dim=4, hidden_dim=8)
    logits = model(torch.tensor([[0, 1, 2], [2, 3, 4]], dtype=torch.long))
    assert logits.shape == (2, 3, 5)
    with pytest.raises(ValueError, match="vocabulary_size"):
        DeepLogModel(vocabulary_size=1)


def test_next_event_statistics_computes_rank_topk_nll_and_entropy() -> None:
    logits = np.array([2.0, 0.0, 1.0])
    stats = next_event_statistics(logits, true_index=2, top_k=2)
    assert stats.rank == 2
    assert stats.top_k_miss == 0
    assert stats.negative_log_likelihood > 0
    assert stats.entropy > 0
    assert stats.expected_indices == (0, 2)


def test_next_event_statistics_rejects_invalid_target() -> None:
    with pytest.raises(ValueError, match="true_index"):
        next_event_statistics(np.array([1.0, 2.0]), true_index=3)


def test_qlora_settings_lock_single_gpu_defaults() -> None:
    settings = QLoRASettings()
    assert settings.base_model == "Qwen/Qwen2.5-1.5B"
    assert settings.load_in_4bit is True
    assert settings.target_modules == "all-linear"
    assert settings.gradient_checkpointing is True


def test_make_next_event_examples_never_crosses_sequence_boundaries() -> None:
    examples = make_next_event_examples(
        [(0, 1, 2, 3), (4, 5)], context_size=2
    )
    assert examples == [((0,), 1), ((0, 1), 2), ((1, 2), 3), ((4,), 5)]


def test_prepare_qwen_qlora_adds_event_tokens_and_wraps_adapter() -> None:
    calls: dict[str, object] = {}

    class FakeTokenizer:
        pad_token = None
        eos_token = "<EOS>"

        def add_special_tokens(self, value):
            calls["tokens"] = value

        def __len__(self):
            return 101

    class FakeModel:
        def resize_token_embeddings(self, size):
            calls["resize"] = size

        def gradient_checkpointing_enable(self):
            calls["checkpointing"] = True

    tokenizer = FakeTokenizer()
    model = FakeModel()

    def tokenizer_loader(name):
        calls["tokenizer_name"] = name
        return tokenizer

    def model_loader(name, **kwargs):
        calls["model_name"] = name
        calls["model_kwargs"] = kwargs
        return model

    dependencies = QLoRADependencies(
        tokenizer_loader=tokenizer_loader,
        model_loader=model_loader,
        quantization_factory=lambda **kwargs: ("quant", kwargs),
        lora_factory=lambda **kwargs: ("lora", kwargs),
        prepare_kbit=lambda value: value,
        peft_wrapper=lambda value, config: (value, config),
    )
    codec = EventTokenCodec.fit([("E1", "E2")])
    wrapped, returned_tokenizer = prepare_qwen_qlora(
        codec, settings=QLoRASettings(), dependencies=dependencies
    )
    assert returned_tokenizer is tokenizer
    assert wrapped[0] is model
    assert wrapped[1][1]["target_modules"] == "all-linear"
    assert calls["resize"] == 101
    assert calls["checkpointing"] is True
    assert tokenizer.pad_token == "<EOS>"
    assert "<EVT_000000>" in calls["tokens"]["additional_special_tokens"]


def _encoded(index: int, ids: tuple[str, ...], label: int = 0) -> EncodedSequence:
    start = datetime(2025, 1, 1, tzinfo=UTC) + timedelta(minutes=index)
    return EncodedSequence(
        sequence_id=f"n-{index}",
        event_ids=ids,
        label=label,
        started_at=start,
        ended_at=start + timedelta(seconds=len(ids)),
    )


def test_deeplog_detector_trains_and_returns_finite_sequence_scores() -> None:
    torch.manual_seed(3)
    train = [
        _encoded(0, ("E1", "E2", "E3", "E1")),
        _encoded(1, ("E1", "E2", "E3", "E2")),
        _encoded(2, ("E1", "E2", "E3", "E1")),
    ]
    detector = DeepLogDetector(
        context_size=3,
        embedding_dim=4,
        hidden_dim=8,
        layers=1,
        epochs=1,
        batch_size=4,
        random_state=3,
    ).fit(train)
    scores = detector.score(
        [_encoded(4, ("E1", "E2", "E3")), _encoded(5, ("X", "Y", "Z"))]
    )
    assert scores.shape == (2,)
    assert np.isfinite(scores).all()


def test_train_qwen_adapter_executes_trainer_and_saves_adapter(tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    class FakeTokenizer:
        pad_token_id = 0

        def __call__(self, text, **kwargs):
            calls.setdefault("texts", []).append(text)
            return {
                "input_ids": torch.tensor([1, 2, 0, 0]),
                "attention_mask": torch.tensor([1, 1, 0, 0]),
            }

        def save_pretrained(self, path):
            calls["tokenizer_saved"] = str(path)

    class FakeModel:
        def save_pretrained(self, path):
            calls["model_saved"] = str(path)

    class FakeTrainer:
        def __init__(self, **kwargs):
            calls["trainer_kwargs"] = kwargs

        def train(self):
            calls["trained"] = True

    codec = EventTokenCodec.fit([("E1", "E2")])
    summary = train_qwen_adapter(
        codec=codec,
        sequences=[("E1", "E2"), ("E1", "E2", "E1")],
        output_dir=tmp_path,
        model=FakeModel(),
        tokenizer=FakeTokenizer(),
        trainer_factory=FakeTrainer,
        training_arguments_factory=lambda **kwargs: kwargs,
        epochs=1,
    )
    assert calls["trained"] is True
    assert calls["model_saved"] == str(tmp_path)
    assert calls["tokenizer_saved"] == str(tmp_path)
    assert summary.training_sequences == 2
    dataset = calls["trainer_kwargs"]["train_dataset"]
    assert dataset[0]["labels"].tolist() == [1, 2, -100, -100]
