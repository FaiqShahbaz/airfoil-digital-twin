# Tests

This directory will contain unit and smoke tests for the ML/GNN/digital-twin workflow.

Current and planned tests:

- dataset manifest parsing
- graph tensor shape validation
- normalization statistics
- train/validation/test split logic
- model forward passes with configurable dimensions
- digital-twin inference wrapper behavior

Large CFD cases and generated graph datasets should not be required by default unit tests.
