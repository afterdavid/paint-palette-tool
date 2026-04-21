---
title: Paint Palette Tool
source: /Users/theo/Library/Mobile Documents/com~apple~CloudDocs/Theo/Theo/wiki/apps/paint-palette-tool.md
copied: 2026-04-21
status: inherited-spec
---

# Paint Palette Tool

> Adobe-native palette constraint + paint-store spec-sheet generator for muralists. Digital design is done in colors that a paint store can actually reproduce, and the output tells you exactly what to buy.

## The Problem

Muralists and their collaborators design in Photoshop / Illustrator using full RGB/CMYK gamut, but a lot of bright RGB colors (saturated teals, neon greens, pure digital reds) can't be physically reproduced by house acrylic paint. The designer finishes the comp, goes to the paint store, and either has to settle for a near-miss or spends hours picking stock matches from a fan deck.

Second problem: at the end of the design there's no native way to get a clean list of "which paint colors did I actually use, and how much of each do I need." The Photoshop Swatches panel remembers what you clicked, not what's visible. Muralists end up eyeballing this from the comp.

## Users

American Mural + muralist peers. Muralists who design digitally and execute with house acrylic paint (SW, BM, PPG, Behr, Valspar).

## v1 Scope

Two features that reinforce each other:

1. **Palette lock** — a constrained swatch library loaded into Adobe apps, so every color picked lands in the physically-achievable-in-paint gamut.
2. **Bill-of-materials output** — after the design is done, the tool reads the file, identifies every color used, and produces a paint-store deliverable.

## Output: Two formats, same data

Every color in the design produces:

- **LAB value** (brand-agnostic color specification) for pro paint desks (SW commercial, BM dealer) that will custom-match from a number.
- **Printed color card** on coated paper for retail counters (Home Depot / Behr, Lowe's / Valspar) where the workflow is "scan a physical sample with the spectrophotometer."
- **Nearest stock fan-deck matches** across SW, BM, Behr, Valspar (typed directly at the counter — cheapest, most consistent batch-to-batch).

A single project exports a **PDF spec sheet**: one row per color, with printed swatch, LAB value, nearest stock matches, coverage area (sq in or sq ft), and gallons estimated at one coat.
