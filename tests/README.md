# Tests

This directory contains unit and smoke tests for the ML/GNN/digital-twin workflow.

Current tests cover:

- dataset manifest parsing
- graph tensor shape validation
- normalization statistics
- train/validation/test split logic
- model forward passes with configurable dimensions
- digital-twin inference wrapper behavior
- dashboard helper behavior

Large CFD cases and generated graph datasets should not be required by default unit tests.
