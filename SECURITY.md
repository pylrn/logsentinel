# Security Policy and Threat Boundaries

## Supported security properties

- Raw input is redacted before parser fitting, prepared-data persistence, or API result storage.
- Tenant/environment lookups use an enum-controlled directory boundary and validated artifact identifiers.
- Parsers, vocabularies, QLoRA adapters, detectors, thresholds, feedback, and anomaly records are isolated by environment.
- Immutable artifact directories contain SHA-256 checksums for metadata, parser state, detector files, and every packaged adapter file.
- API requests cap message length and batch size and require timezone-aware timestamps.
- Explanations are generated from component contributions and never by sending logs to an external model.

## Trust boundaries

`joblib` uses Python pickle semantics. Checksums detect accidental or post-training modification, but loading an attacker-controlled model file can execute code. Load artifacts only from trusted local training output with restricted filesystem permissions.

Hugging Face datasets and base-model files are external dependencies. Pin revisions and verify provenance/checksums for regulated or production use. The current manifest records installed versions and prepared-data checksums; production deployments should also record immutable dataset and model revisions.

The local/Colab inference path does not transmit logs to Hugging Face. Hugging Face is contacted only when explicitly downloading public datasets or the shared base checkpoint. Configure `LOGSENTINEL_STORAGE_ROOT` on an encrypted external disk when local retention requirements apply; model, dataset, Transformers, Torch, and pip caches are routed below that directory.

## Threats considered

- Secret/PII leakage through prepared data, error messages, dashboards, or explanations.
- Path traversal and cross-environment artifact lookup.
- Artifact corruption or replacement.
- Oversized batches, malformed timestamps, empty sequences, and parser template flooding.
- Log injection designed to imitate known normal templates.
- Slow distribution drift that moves below a fixed anomaly threshold.
- Membership leakage from a fine-tuned adapter.

## Operational mitigations

- Run a source-specific redaction audit before onboarding each organization.
- Keep raw retention short and encrypt raw and prepared stores separately.
- Restrict artifact write permissions to the training role and serve them read-only.
- Treat adapters as sensitive environment data even though the base Qwen checkpoint is public and shared.
- Review unseen-template rate, score distribution, alert volume, and analyst feedback before recalibration.
- Rate-limit `/v1/score` at the deployment boundary and cap tenant ingestion independently.
- Require analyst confirmation before automated remediation.
- Test adapters with canary strings and membership-inference probes before release.
- Roll back by selecting a previously verified immutable artifact version.

## Reporting vulnerabilities

Do not include real secrets, customer logs, or exploit payloads in a public report. Provide a minimal synthetic reproduction, affected version, impact, and proposed mitigation through the repository owner's private security channel.
