# Tests

This folder is reserved for automated verification of the trainer.

High-priority tests should eventually cover filter-response accuracy, stimulus generation, A/B randomization behavior, scoring logic, adaptive-threshold state changes, and data logging.

Automobile simulation coverage should also include:
- cabin/AC/loudness conditioning output sanity checks
- deterministic seeded conditioning consistency across A/B trial pairs
- one-click preset mapping validation (preset -> monitoring/cabin/AC/loudness values)
