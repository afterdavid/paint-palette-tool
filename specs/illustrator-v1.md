# Illustrator V1 Technical Spec

## Objective

Build the first working Illustrator integration for Paint Palette Tool.

The goal is not a custom paint interface. The goal is to let artists work normally in Illustrator with a constrained swatch set, then scan the document and export a paint-spec summary.

## UX model

Illustrator remains the main interface.

V1 uses:
- native Illustrator swatches
- a loaded `.ase` palette
- script commands run on demand

V1 does **not** use:
- click logging
- background tracking of every color interaction
- a custom replacement color picker

## Commands

### 1. Refresh Used Colors

Scans the current document and reports which colors are actually applied to artwork.

Responsibilities:
- inspect page items in the current document
- read fill and stroke colors
- resolve them to swatches when possible
- aggregate usage by swatch/color
- identify colors outside the approved palette

### 2. Export Paint Spec

Performs the same scan, then writes a structured export.

V1 output priority:
1. JSON
2. HTML
3. PDF later

## Source of truth

The source of truth is the current artwork state, not the user's selection history.

A color belongs in the export if it is actually applied to visible artwork at scan time.

## V1 inclusion rules

Include:
- visible vector page items with solid fills
- visible vector page items with solid strokes
- named swatches when available

Warn or defer:
- gradients
- patterns
- meshes
- raster images
- effects that make area estimation ambiguous
- ad hoc colors not tied to approved swatches

## Data to collect per used color

- swatch name if available
- internal color key
- RGB preview value
- LAB value if available from dataset
- object count
- fill usage count
- stroke usage count
- approximate area contribution
- nearest stock matches if present in dataset
- flags/warnings

## Area estimation

V1 can use approximate geometry-based area estimation.

Acceptable first-pass behavior:
- sum simple vector areas for filled closed paths
- record stroke usage separately
- if exact area is hard, output relative usage plus a warning

The data does not need to be perfect in the first pass. It needs to be useful and explain its limits.

## Output schema direction

The Illustrator script should output a structured JSON object with:
- document metadata
- scan timestamp
- warnings
- used colors array

Suggested top-level shape:

```json
{
  "document": {
    "name": "mural-east-wall.ai",
    "artboards": 2
  },
  "generatedAt": "2026-04-21T15:00:00Z",
  "warnings": [],
  "usedColors": []
}
```

Each used color should include fields like:

```json
{
  "name": "Sky Blue 03",
  "swatchName": "AM Sky Blue 03",
  "rgb": "#6EAEDB",
  "lab": { "l": 68.1, "a": -7.2, "b": -24.4 },
  "objectCount": 12,
  "fillCount": 10,
  "strokeCount": 2,
  "approxAreaSqIn": 1840.5,
  "nearestMatches": [
    { "brand": "Sherwin-Williams", "code": "SW-xxxx", "name": "Example" }
  ],
  "flags": []
}
```

## V1 implementation notes

- Start with solid fills and strokes only.
- Prefer named swatch resolution over raw color values.
- Keep the script readable and inspectable.
- Save difficult cases as warnings, not silent failures.
- Do not try to solve Photoshop problems here.

## Exit condition

One real Illustrator mural comp can be scanned and produce:
- a trustworthy used-colors list
- a structured export
- enough information to draft a paint-store materials sheet
