# LogSentinel Model Card

## Model description

LogSentinel is a tenant-isolated log anomaly detection prototype. Its default deployable artifact combines template rarity, PCA reconstruction error, Isolation Forest scores, and logistic calibration. It also includes executable DeepLog and Qwen2.5-1.5B QLoRA training paths for controlled experiments.

The base transformer is `Qwen/Qwen2.5-1.5B`. Each environment receives its own event vocabulary, adapter output, calibration threshold, parser state, and artifact version. The base checkpoint may be shared; environment artifacts may not.

## Intended use

- Research on HDFS block sessions and BGL time windows.
- DevOps, SRE, and SOC demonstrations where analysts review ranked deviations.
- Normal-only onboarding followed by validation-label calibration when labels become available.
- Comparison of traditional, sequential, transformer, and hybrid anomaly signals.

The model is not intended to autonomously block traffic, disable accounts, remediate infrastructure, or replace incident responders.

## Inputs and outputs

Input is an ordered, redacted sequence of deterministic event-template IDs. The serving API accepts raw log messages but redacts them before template matching.

Outputs include an anomaly score, threshold decision, component scores, expected next templates, recent event-ID context, and a rule-based explanation. No external generative service receives raw logs.

## Training

- Base detectors train only on the chronological normal portion of the training partition.
- The fusion model and threshold use the chronological validation partition.
- The final chronological test partition remains locked until evaluation.
- QLoRA defaults to NF4 4-bit loading, all-linear LoRA targets, rank 16, alpha 32, trainable event embeddings/LM head, gradient checkpointing, and 1,024-token contexts.
- DeepLog uses next-event cross-entropy over event-ID sequences.

## Evaluation

Required metrics are precision, recall, F1, PR-AUC, ROC-AUC, false alerts per 1,000 normal sequences, latency percentiles, and bootstrap F1 intervals. HDFS is evaluated at block level; BGL is evaluated at 60-second window level.

This repository contains no claimed HDFS or BGL benchmark scores. Synthetic smoke outputs are labeled `synthetic-smoke-test` and `not_a_public_benchmark: true`.

## Limitations

- Rare but valid operational changes can resemble anomalies.
- Template parsing can hide meaningful parameter changes or create unstable event identities.
- Public supercomputer/distributed-system logs do not represent every enterprise application.
- QLoRA training quality depends on GPU runtime, split size, context length, and calibration data.
- An attacker may flood known templates, generate parser churn, or slowly shift event distributions.
- Detection-delay measurements from public labels are proxies, not true ticket-based MTTD.

## Privacy and security

Redaction occurs before parser fitting, prepared-data persistence, or API result storage. Artifact checksums detect corruption, but `joblib` artifacts are trusted-code inputs and must never be loaded from untrusted sources.

