# Missing and uncertain colors — 2026-04-21

## PPG pages skipped

The PPG importer found 3,267 `/ppg-colors/` URLs in the official sitemap. It wrote 3,225 normalized records and skipped 42 pages because those pages did not expose a parseable RGB block.

Skipped URLs:
- https://www.ppgpaints.com/ppg-colors/abundant-blue
- https://www.ppgpaints.com/ppg-colors/aqua-essence
- https://www.ppgpaints.com/ppg-colors/astute
- https://www.ppgpaints.com/ppg-colors/blessing
- https://www.ppgpaints.com/ppg-colors/bronzed-ochre
- https://www.ppgpaints.com/ppg-colors/bronzed-ginger
- https://www.ppgpaints.com/ppg-colors/bronzed-caramel
- https://www.ppgpaints.com/ppg-colors/champagne-dreams
- https://www.ppgpaints.com/ppg-colors/charmed-life
- https://www.ppgpaints.com/ppg-colors/clairvoyant
- https://www.ppgpaints.com/ppg-colors/copper-kiss
- https://www.ppgpaints.com/ppg-colors/crinkle
- https://www.ppgpaints.com/ppg-colors/fabled-foliage
- https://www.ppgpaints.com/ppg-colors/ferrous-forest
- https://www.ppgpaints.com/ppg-colors/flintlock
- https://www.ppgpaints.com/ppg-colors/flatter
- https://www.ppgpaints.com/ppg-colors/foundry
- https://www.ppgpaints.com/ppg-colors/frosted-ivory
- https://www.ppgpaints.com/ppg-colors/gilded-gold
- https://www.ppgpaints.com/ppg-colors/ginger-cress
- https://www.ppgpaints.com/ppg-colors/golden-chestnut
- https://www.ppgpaints.com/ppg-colors/golden-saffron
- https://www.ppgpaints.com/ppg-colors/hushed-copper
- https://www.ppgpaints.com/ppg-colors/iridescent-oyster
- https://www.ppgpaints.com/ppg-colors/mediterranean-night
- https://www.ppgpaints.com/ppg-colors/metallic-memories
- https://www.ppgpaints.com/ppg-colors/misty-frost
- https://www.ppgpaints.com/ppg-colors/mucho-mint
- https://www.ppgpaints.com/ppg-colors/mingle
- https://www.ppgpaints.com/ppg-colors/oxidized
- https://www.ppgpaints.com/ppg-colors/patisserie
- https://www.ppgpaints.com/ppg-colors/pink-blink
- https://www.ppgpaints.com/ppg-colors/pink-smolder
- https://www.ppgpaints.com/ppg-colors/primrose-promise
- https://www.ppgpaints.com/ppg-colors/rejoice
- https://www.ppgpaints.com/ppg-colors/sanguine
- https://www.ppgpaints.com/ppg-colors/sapphire-pebble
- https://www.ppgpaints.com/ppg-colors/silvery-orchid
- https://www.ppgpaints.com/ppg-colors/sly
- https://www.ppgpaints.com/ppg-colors/stannic
- https://www.ppgpaints.com/ppg-colors/totally-topiary
- https://www.ppgpaints.com/ppg-colors/whimsical-woods

## Other caveats

- PPG downloadable assets are linked from the official page but currently point to hosts that do not resolve from this machine. The importer preserves this in `data/raw/ppg/downloadable-palettes/manifest.json`.
- Behr's first-party payload contained duplicate color rows. The catalog now keeps the first record per stable Behr color id.
- The canonical Benjamin Moore detail crawl is partial and deduped. The combined catalog uses the larger official downloadable Benjamin Moore ASE import instead.
- The canonical Sherwin-Williams graph crawl is partial. The combined catalog uses the official downloadable Sherwin-Williams ASE import instead.
- Valspar has a public browse-colors source but no official public downloadable ASE/ACO library found in this pass.
