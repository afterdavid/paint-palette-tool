# Catalog Import Plan

## Goal

Import complete manufacturer color catalogs into normalized JSON files.

## Why this needs a pipeline

This is not a one-page copy job.

Different manufacturers expose color data in different ways:
- public browse pages
- search endpoints
- nested site navigation
- dynamic pages
- partial metadata on listing pages and fuller metadata on detail pages

A reliable catalog import needs repeatable scripts and provenance tracking.

## Import stages

### 1. Source discovery
For each manufacturer, identify:
- browse URL
- searchable color endpoints if any
- detail page structure
- whether color code, name, and RGB/HEX are available publicly

### 2. Raw capture
Store raw discovered records before normalization.

Suggested location:
- `data/raw/<manufacturer>/`

### 3. Normalization
Convert raw records into canonical schema records.

Suggested location:
- `data/catalogs/<manufacturer>.json`

### 4. Validation
Validate normalized records against `data/color-schema.json`.

### 5. Derived outputs
Generate:
- full-brand `.ase`
- curated subsets
- later search indexes

## Manufacturer notes so far

### Sherwin-Williams
- browse page found
- likely requires deeper source discovery for full catalog extraction

### Benjamin Moore
- public color section exists and claims 3,500+ colors
- likely dynamic; needs import-specific source handling

### Behr
- public color section exists with category browsing
- likely supports fuller discovery with more work

### Glidden
- initial attempted URL returned 404; needs source discovery

### Dunn-Edwards
- attempted browse URL was wrong, but the site clearly has color browsing and downloadable digital swatches
- promising source; needs correct endpoint discovery

### Valspar
- browse page exposes many colors and likely supports deeper extraction

## Immediate next engineering tasks

1. create `data/raw/` structure
2. create importer script skeleton per manufacturer or a generic importer harness
3. capture first raw source for one manufacturer end to end
4. normalize that one manufacturer into canonical JSON
5. expand manufacturer by manufacturer

## Practical rule

Do not hand-build thousands of entries directly in normalized files.

Use scripts.
Keep raw captures.
Track provenance.
