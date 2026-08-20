# LogSentinel Dataset Card

## Sources

LogSentinel supports the provenance-linked Hugging Face mirrors:

- `logfit-project/HDFS_v1`, sourced from LogHub HDFS_v1.
- `logfit-project/BGL`, sourced from LogHub BGL.

The mirrors preserve line-level fields needed for project-owned redaction, template extraction, sequence construction, and temporal splitting. Review both mirror cards and the original LogHub terms before downloading or redistributing data.

## Canonical event schema

Each source record becomes:

- timezone-aware timestamp;
- dataset identifier;
- emitting source/component;
- hashed host identifier;
- severity;
- redacted message;
- binary ground-truth label;
- hashed grouping identifier for HDFS.

## Processing

1. Validate source fields and binary labels.
2. Hash host and HDFS block identifiers with purpose-specific salts.
3. Replace sensitive/variable values with typed placeholders.
4. Mine templates with Drain3 during training and freeze the resulting vocabulary.
5. Group HDFS by block ID; group BGL into non-overlapping 60-second windows.
6. Sort chronologically and split 60% training, 20% validation, and 20% test.
7. Remove anomalous sequences from the detector-training portion only.

Parser state, scalers, vocabularies, and feature statistics are fitted from the training partition only.

## Labels and evaluation units

HDFS line labels are aggregated to block-level sequence labels using `any anomaly`. BGL line labels are aggregated to 60-second window labels using the same rule. Results from different evaluation units must not be compared without an explicit conversion protocol.

## Privacy

The project replaces IP addresses, block IDs, paths, emails, UUIDs, secret-like assignments, and long numeric identifiers before persistence. Redaction reduces exposure but cannot guarantee removal of every organization-specific identifier; new sources require a redaction audit.

## Known limitations

- Dataset labels and historical collection environments may not match current production systems.
- Temporal splits are intentionally harder than random splits and are not directly comparable with papers using other protocols.
- A bounded JSON prepared format is used locally. Full multi-million-sequence work should use sharded Parquet or another columnar store.
- Public data does not demonstrate real tenant privacy or production drift by itself.

