# Digital-Twin Configs

Digital-twin configs describe runtime inference behavior rather than training behavior.

They should include:

- Model checkpoint path.
- Normalization statistics path.
- Graph template or mesh source.
- Valid AoA/Re range.
- Warning policy for out-of-domain queries.

They should not include CFD solution fields as required inputs. Runtime inputs should be deployable quantities such as geometry, mesh representation, AoA, and Re.
