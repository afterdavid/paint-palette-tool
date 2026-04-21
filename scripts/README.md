# Build Scripts

## `generate_ase.py`

Planned path:
- read seed palette JSON
- validate records
- generate Adobe Swatch Exchange output in `ase/`

Current state:
- scaffold only
- writes a placeholder file so the pipeline shape is concrete

Next implementation steps:
1. point it at the real seed palette file
2. validate against `data/color-schema.json`
3. implement ASE serialization or a conversion bridge
