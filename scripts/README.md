# Build Scripts

## `generate_ase.py`

Path:
- read catalog or seed palette JSON
- generate Adobe Swatch Exchange output in `ase/`

Current state:
- writes real ASE binary files with RGB swatches

Example:

```bash
python3 scripts/generate_ase.py data/catalogs/ppg.json ase/ppg-full.ase
```

## `build_accessible_catalog.py`

Builds the current best combined catalog from the strongest available source per brand:

```bash
python3 scripts/build_accessible_catalog.py
```
