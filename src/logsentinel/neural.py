from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from logsentinel.detection import EncodedSequence
from logsentinel.storage import configure_local_storage


@dataclass(frozen=True)
class EventTokenCodec:
    event_ids: tuple[str, ...]
    tokens: tuple[str, ...]

    @classmethod
    def fit(cls, sequences: list[tuple[str, ...]]) -> EventTokenCodec:
        event_ids = tuple(sorted({event for sequence in sequences for event in sequence}))
        tokens = tuple(f"<EVT_{index:06d}>" for index in range(len(event_ids)))
        return cls(event_ids=event_ids, tokens=tokens)

    @property
    def added_tokens(self) -> tuple[str, ...]:
        return (*self.tokens, "<EVT_UNK>", "<SEQ_END>")

    def serialize(self, sequence: tuple[str, ...]) -> str:
        mapping = dict(zip(self.event_ids, self.tokens, strict=True))
        encoded = [mapping.get(event, "<EVT_UNK>") for event in sequence]
        return " ".join(encoded)

    def deserialize(self, tokens: list[str]) -> tuple[str, ...]:
        reverse = dict(zip(self.tokens, self.event_ids, strict=True))
        decoded = []
        for token in tokens:
            if token == "<SEQ_END>":
                break
            decoded.append(reverse.get(token, "<UNK>"))
        return tuple(decoded)


class DeepLogModel(nn.Module):
    def __init__(
        self,
        *,
        vocabulary_size: int,
        embedding_dim: int = 64,
        hidden_dim: int = 128,
        layers: int = 2,
    ) -> None:
        super().__init__()
        if vocabulary_size < 2:
            raise ValueError("vocabulary_size must be at least two")
        self.embedding = nn.Embedding(vocabulary_size, embedding_dim)
        self.lstm = nn.LSTM(
            embedding_dim,
            hidden_dim,
            num_layers=layers,
            batch_first=True,
        )
        self.output = nn.Linear(hidden_dim, vocabulary_size)

    def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
        encoded = self.embedding(input_ids)
        states, _ = self.lstm(encoded)
        return self.output(states)


class DeepLogDetector:
    def __init__(
        self,
        *,
        context_size: int = 32,
        embedding_dim: int = 64,
        hidden_dim: int = 128,
        layers: int = 2,
        epochs: int = 5,
        batch_size: int = 128,
        learning_rate: float = 1e-3,
        random_state: int = 42,
        device: str | None = None,
    ) -> None:
        self.context_size = context_size
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.layers = layers
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.event_index: dict[str, int] = {}
        self.unknown_index: int | None = None
        self.padding_index: int | None = None
        self.model: DeepLogModel | None = None

    def fit(self, sequences: list[EncodedSequence]) -> DeepLogDetector:
        if not sequences or any(row.label != 0 for row in sequences):
            raise ValueError("DeepLog requires non-empty normal-only training sequences")
        events = tuple(sorted({event for row in sequences for event in row.event_ids}))
        self.event_index = {event: index for index, event in enumerate(events)}
        self.unknown_index = len(events)
        self.padding_index = len(events) + 1
        numeric = [tuple(self.event_index[event] for event in row.event_ids) for row in sequences]
        examples = make_next_event_examples(numeric, context_size=self.context_size)
        if not examples:
            raise ValueError("DeepLog requires at least one sequence with two or more events")
        torch.manual_seed(self.random_state)
        self.model = DeepLogModel(
            vocabulary_size=len(events) + 2,
            embedding_dim=self.embedding_dim,
            hidden_dim=self.hidden_dim,
            layers=self.layers,
        ).to(self.device)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        loss_function = nn.CrossEntropyLoss()
        loader = DataLoader(
            examples,
            batch_size=self.batch_size,
            shuffle=True,
            collate_fn=lambda batch: _collate_next_events(batch, self.padding_index or 0),
        )
        self.model.train()
        for _ in range(self.epochs):
            for inputs, lengths, targets in loader:
                inputs = inputs.to(self.device)
                targets = targets.to(self.device)
                optimizer.zero_grad()
                logits = self.model(inputs)
                positions = (lengths - 1).to(self.device)
                selected = logits[torch.arange(len(inputs), device=self.device), positions]
                loss = loss_function(selected, targets)
                loss.backward()
                optimizer.step()
        return self

    def score(self, sequences: list[EncodedSequence]) -> np.ndarray:
        if self.model is None or self.unknown_index is None:
            raise RuntimeError("DeepLog detector has not been fitted")
        self.model.eval()
        scores = []
        with torch.no_grad():
            for row in sequences:
                numeric = tuple(
                    self.event_index.get(event, self.unknown_index) for event in row.event_ids
                )
                examples = make_next_event_examples([numeric], context_size=self.context_size)
                losses = []
                for context, target in examples:
                    inputs = torch.tensor([context], dtype=torch.long, device=self.device)
                    logits = self.model(inputs)[0, -1]
                    log_probabilities = torch.log_softmax(logits, dim=-1)
                    losses.append(float(-log_probabilities[target].cpu()))
                scores.append(float(np.mean(losses)) if losses else 0.0)
        return np.asarray(scores, dtype=float)


@dataclass(frozen=True)
class NextEventStatistics:
    negative_log_likelihood: float
    rank: int
    top_k_miss: int
    entropy: float
    expected_indices: tuple[int, ...]


@dataclass(frozen=True)
class TransformerSequenceScore:
    negative_log_likelihood: float
    mean_rank: float
    top_k_miss_rate: float
    entropy: float
    expected_event_ids: tuple[str, ...]

    def feature_vector(self) -> tuple[float, float, float, float]:
        return (
            self.negative_log_likelihood,
            self.mean_rank,
            self.top_k_miss_rate,
            self.entropy,
        )


@dataclass(frozen=True)
class QwenInferenceDependencies:
    tokenizer_loader: Callable[..., Any]
    model_loader: Callable[..., Any]
    adapter_loader: Callable[..., Any]


class QwenAdapterScorer:
    """Teacher-forced next-event inference over a fitted event-token vocabulary."""

    def __init__(
        self,
        *,
        codec: EventTokenCodec,
        model: Any,
        tokenizer: Any,
        top_k: int = 5,
    ) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        self.codec = codec
        self.model = model
        self.tokenizer = tokenizer
        self.top_k = top_k
        self._event_tokens = (*codec.tokens, "<EVT_UNK>")
        self._candidate_token_ids = tuple(
            int(tokenizer.convert_tokens_to_ids(token)) for token in self._event_tokens
        )
        self.model.eval()

    @classmethod
    def from_pretrained(
        cls,
        adapter_path: Path | str,
        *,
        storage_root: Path | str | None = None,
        device: str | None = None,
        top_k: int = 5,
        dependencies: QwenInferenceDependencies | None = None,
    ) -> QwenAdapterScorer:
        adapter = Path(adapter_path).expanduser().resolve()
        try:
            payload = json.loads(
                (adapter / "logsentinel_adapter.json").read_text(encoding="utf-8")
            )
            codec_payload = payload["codec"]
            codec = EventTokenCodec(
                event_ids=tuple(str(item) for item in codec_payload["event_ids"]),
                tokens=tuple(str(item) for item in codec_payload["tokens"]),
            )
            base_model = str(payload["base_model"])
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("adapter metadata is missing or invalid") from exc
        if len(codec.event_ids) != len(codec.tokens) or not codec.event_ids:
            raise RuntimeError("adapter event-token vocabulary is invalid")
        layout = configure_local_storage(storage_root)
        dependencies = dependencies or _load_qwen_inference_dependencies()
        selected_device = device or _best_inference_device()
        model_kwargs: dict[str, Any] = {
            "cache_dir": layout.environment["HF_HUB_CACHE"],
            "low_cpu_mem_usage": True,
        }
        if selected_device == "cuda":
            model_kwargs.update(device_map="auto", torch_dtype=torch.bfloat16)
        elif selected_device == "mps":
            model_kwargs["torch_dtype"] = torch.float16
        else:
            model_kwargs["torch_dtype"] = torch.float32
        tokenizer = dependencies.tokenizer_loader(
            str(adapter), local_files_only=True
        )
        base = dependencies.model_loader(base_model, **model_kwargs)
        if callable(getattr(base, "resize_token_embeddings", None)):
            base.resize_token_embeddings(len(tokenizer))
        model = dependencies.adapter_loader(
            base, str(adapter), local_files_only=True
        )
        if selected_device != "cuda" and callable(getattr(model, "to", None)):
            model = model.to(selected_device)
        return cls(
            codec=codec,
            model=model,
            tokenizer=tokenizer,
            top_k=top_k,
        )

    def score(self, sequences: list[EncodedSequence]) -> list[TransformerSequenceScore]:
        return [self._score_one(row.event_ids) for row in sequences]

    def _score_one(self, event_ids: tuple[str, ...]) -> TransformerSequenceScore:
        if not event_ids:
            return TransformerSequenceScore(0.0, 0.0, 0.0, 0.0, ())
        encoded = self.tokenizer(
            self.codec.serialize(event_ids),
            add_special_tokens=False,
            return_tensors="pt",
        )
        device = getattr(self.model, "device", torch.device("cpu"))
        model_inputs = {
            name: value.to(device) if isinstance(value, torch.Tensor) else value
            for name, value in encoded.items()
        }
        with torch.inference_mode():
            logits = self.model(**model_inputs).logits[0].detach().float().cpu().numpy()
        candidate_logits = logits[:, self._candidate_token_ids]
        mapping = {event: index for index, event in enumerate(self.codec.event_ids)}
        unknown_index = len(self.codec.event_ids)
        transition_stats = []
        for position in range(1, len(event_ids)):
            true_index = mapping.get(event_ids[position], unknown_index)
            transition_stats.append(
                next_event_statistics(
                    candidate_logits[position - 1],
                    true_index=true_index,
                    top_k=self.top_k,
                )
            )
        latest = next_event_statistics(
            candidate_logits[len(event_ids) - 1],
            true_index=unknown_index,
            top_k=self.top_k,
        )
        expected = tuple(
            self.codec.event_ids[index] if index < len(self.codec.event_ids) else "<UNK>"
            for index in latest.expected_indices
        )
        if not transition_stats:
            return TransformerSequenceScore(0.0, 0.0, 0.0, 0.0, expected)
        return TransformerSequenceScore(
            negative_log_likelihood=float(
                np.mean([item.negative_log_likelihood for item in transition_stats])
            ),
            mean_rank=float(np.mean([item.rank for item in transition_stats])),
            top_k_miss_rate=float(
                np.mean([item.top_k_miss for item in transition_stats])
            ),
            entropy=float(np.mean([item.entropy for item in transition_stats])),
            expected_event_ids=expected,
        )


def transformer_signal_matrix(
    scores: list[TransformerSequenceScore],
) -> np.ndarray:
    if not scores:
        return np.empty((0, 4), dtype=float)
    return np.asarray([item.feature_vector() for item in scores], dtype=float)


def next_event_statistics(
    logits: np.ndarray, *, true_index: int, top_k: int = 5
) -> NextEventStatistics:
    values = np.asarray(logits, dtype=float)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("logits must be a non-empty one-dimensional array")
    if not 0 <= true_index < len(values):
        raise ValueError("true_index is outside the logits vocabulary")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    shifted = values - np.max(values)
    probabilities = np.exp(shifted)
    probabilities /= np.sum(probabilities)
    ordered = np.argsort(-probabilities)
    rank = int(np.where(ordered == true_index)[0][0]) + 1
    selected = tuple(int(item) for item in ordered[: min(top_k, len(values))])
    return NextEventStatistics(
        negative_log_likelihood=float(-np.log(max(probabilities[true_index], 1e-12))),
        rank=rank,
        top_k_miss=int(true_index not in selected),
        entropy=float(-np.sum(probabilities * np.log(np.maximum(probabilities, 1e-12)))),
        expected_indices=selected,
    )


@dataclass(frozen=True)
class QLoRASettings:
    base_model: str = "Qwen/Qwen2.5-1.5B"
    load_in_4bit: bool = True
    target_modules: str = "all-linear"
    rank: int = 16
    alpha: int = 32
    dropout: float = 0.05
    gradient_checkpointing: bool = True
    max_length: int = 1024

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.base_model):
            raise ValueError("base_model must be a Hugging Face repository identifier")
        if self.rank <= 0 or self.alpha <= 0 or self.max_length <= 1:
            raise ValueError("rank, alpha and max_length must be positive")


@dataclass(frozen=True)
class QLoRADependencies:
    tokenizer_loader: Callable[..., Any]
    model_loader: Callable[..., Any]
    quantization_factory: Callable[..., Any]
    lora_factory: Callable[..., Any]
    prepare_kbit: Callable[[Any], Any]
    peft_wrapper: Callable[[Any, Any], Any]


def make_next_event_examples(
    sequences: list[tuple[int, ...]], *, context_size: int = 32
) -> list[tuple[tuple[int, ...], int]]:
    if context_size <= 0:
        raise ValueError("context_size must be positive")
    examples = []
    for sequence in sequences:
        for position in range(1, len(sequence)):
            start = max(0, position - context_size)
            examples.append((sequence[start:position], sequence[position]))
    return examples


def prepare_qwen_qlora(
    codec: EventTokenCodec,
    *,
    settings: QLoRASettings | None = None,
    dependencies: QLoRADependencies | None = None,
) -> tuple[Any, Any]:
    settings = settings or QLoRASettings()
    dependencies = dependencies or _load_qlora_dependencies()
    tokenizer = dependencies.tokenizer_loader(settings.base_model)
    tokenizer.add_special_tokens(
        {"additional_special_tokens": list(codec.added_tokens)}
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    quantization = dependencies.quantization_factory(
        load_in_4bit=settings.load_in_4bit,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = dependencies.model_loader(
        settings.base_model,
        quantization_config=quantization,
        device_map="auto",
    )
    model.resize_token_embeddings(len(tokenizer))
    model = dependencies.prepare_kbit(model)
    if settings.gradient_checkpointing:
        model.gradient_checkpointing_enable()
    lora = dependencies.lora_factory(
        r=settings.rank,
        lora_alpha=settings.alpha,
        lora_dropout=settings.dropout,
        target_modules=settings.target_modules,
        bias="none",
        task_type="CAUSAL_LM",
        modules_to_save=["embed_tokens", "lm_head"],
    )
    return dependencies.peft_wrapper(model, lora), tokenizer


def _load_qlora_dependencies() -> QLoRADependencies:
    try:
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    except ImportError as exc:
        raise RuntimeError(
            "Qwen QLoRA training requires the 'ml' extra: pip install 'logsentinel[ml]'"
        ) from exc
    return QLoRADependencies(
        tokenizer_loader=AutoTokenizer.from_pretrained,
        model_loader=AutoModelForCausalLM.from_pretrained,
        quantization_factory=BitsAndBytesConfig,
        lora_factory=LoraConfig,
        prepare_kbit=prepare_model_for_kbit_training,
        peft_wrapper=get_peft_model,
    )


def _load_qwen_inference_dependencies() -> QwenInferenceDependencies:
    try:
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "Qwen adapter inference requires the 'ml' extra: pip install 'logsentinel[ml]'"
        ) from exc
    return QwenInferenceDependencies(
        tokenizer_loader=AutoTokenizer.from_pretrained,
        model_loader=AutoModelForCausalLM.from_pretrained,
        adapter_loader=PeftModel.from_pretrained,
    )


def _best_inference_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class CausalEventDataset(Dataset):
    def __init__(
        self,
        *,
        codec: EventTokenCodec,
        sequences: list[tuple[str, ...]],
        tokenizer: Any,
        max_length: int,
    ) -> None:
        self.codec = codec
        self.sequences = sequences
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        encoded = self.tokenizer(
            self.codec.serialize(self.sequences[index]),
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        input_ids = _squeeze_batch(encoded["input_ids"]).long()
        attention_mask = _squeeze_batch(encoded["attention_mask"]).long()
        labels = input_ids.clone()
        labels[attention_mask == 0] = -100
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


@dataclass(frozen=True)
class TransformerTrainingSummary:
    output_dir: str
    training_sequences: int
    event_vocabulary_size: int
    base_model: str


def train_qwen_adapter(
    *,
    codec: EventTokenCodec,
    sequences: list[tuple[str, ...]],
    output_dir: Any,
    settings: QLoRASettings | None = None,
    model: Any | None = None,
    tokenizer: Any | None = None,
    dependencies: QLoRADependencies | None = None,
    trainer_factory: Callable[..., Any] | None = None,
    training_arguments_factory: Callable[..., Any] | None = None,
    epochs: int = 3,
    batch_size: int = 1,
    gradient_accumulation_steps: int = 16,
    learning_rate: float = 2e-4,
) -> TransformerTrainingSummary:
    if not sequences:
        raise ValueError("Qwen adapter training requires at least one sequence")
    settings = settings or QLoRASettings()
    if model is None or tokenizer is None:
        model, tokenizer = prepare_qwen_qlora(
            codec, settings=settings, dependencies=dependencies
        )
    if trainer_factory is None or training_arguments_factory is None:
        try:
            from transformers import Trainer, TrainingArguments
        except ImportError as exc:
            raise RuntimeError(
                "Qwen training requires the 'ml' extra: pip install 'logsentinel[ml]'"
            ) from exc
        trainer_factory = trainer_factory or Trainer
        training_arguments_factory = training_arguments_factory or TrainingArguments
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    dataset = CausalEventDataset(
        codec=codec,
        sequences=sequences,
        tokenizer=tokenizer,
        max_length=settings.max_length,
    )
    arguments = training_arguments_factory(
        output_dir=str(target),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        logging_steps=10,
        save_strategy="epoch",
        report_to="none",
        remove_unused_columns=False,
    )
    trainer = trainer_factory(model=model, args=arguments, train_dataset=dataset)
    trainer.train()
    model.save_pretrained(target)
    tokenizer.save_pretrained(target)
    (target / "logsentinel_adapter.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "base_model": settings.base_model,
                "settings": asdict(settings),
                "codec": {
                    "event_ids": list(codec.event_ids),
                    "tokens": list(codec.tokens),
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return TransformerTrainingSummary(
        output_dir=str(target),
        training_sequences=len(sequences),
        event_vocabulary_size=len(codec.event_ids),
        base_model=settings.base_model,
    )


def _collate_next_events(
    batch: list[tuple[tuple[int, ...], int]], padding_index: int
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    contexts = [torch.tensor(item[0], dtype=torch.long) for item in batch]
    lengths = torch.tensor([len(item) for item in contexts], dtype=torch.long)
    inputs = nn.utils.rnn.pad_sequence(
        contexts, batch_first=True, padding_value=padding_index
    )
    targets = torch.tensor([item[1] for item in batch], dtype=torch.long)
    return inputs, lengths, targets


def _squeeze_batch(value: Any) -> torch.Tensor:
    tensor = value if isinstance(value, torch.Tensor) else torch.tensor(value)
    return tensor.squeeze(0) if tensor.ndim > 1 and tensor.shape[0] == 1 else tensor
