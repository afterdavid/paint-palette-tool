# Sherwin-Williams / Benjamin Moore import notes — 2026-04-21

## What was confirmed

### Benjamin Moore
- Official sitemap index: `https://www.benjaminmoore.com/sitemap.xml`
- Official colors sitemap: `https://www.benjaminmoore.com/sitemaps/colors.xml`
- The colors sitemap exposes thousands of color-detail URLs.
- Public color pages are Next.js pages with a `__NEXT_DATA__` build id.
- Detail payloads can also be requested from `_next/data/<buildId>/...json`.
- In practice, Benjamin Moore starts returning `403 Access Denied` after some sustained automated fetches, including on `_next/data` JSON routes.

### Sherwin-Williams
- Official family pages are AEM pages under `/en-us/color/color-family/...`.
- Family pages expose structured AEM component JSON at paths like:
  - `/en-us/color/color-family/green-paint-colors/_jcr_content/root/container/color_by_group_grid.model.json`
- The site JS exposes an official API base:
  - `https://api.sherwin-williams.com/shared-color-service`
- Confirmed detail endpoint:
  - `/shared-color-service/color/byColorNumber/SW6206`
- Confirmed group metadata endpoint:
  - `/shared-color-service/color/group/identifier/<uuid>`
- I did **not** confirm a complete public official enumeration endpoint for all Sherwin-Williams colors in one pass.
- Current Sherwin-Williams import therefore uses an official graph crawl seeded from family-page model JSON and expanded through related-color links (`colorStripColors`, `similarColors`, `coordinatingColors`).

## Data captured this pass

### Benjamin Moore
- Raw sitemap saved to `data/raw/benjamin-moore/colors-sitemap.xml`
- Raw detail URL list saved to `data/raw/benjamin-moore/detail-urls.txt`
- Build id saved to `data/raw/benjamin-moore/next-build-id.txt`
- Raw fetch log saved to `data/raw/benjamin-moore/detail-pages.jsonl`
- Normalized catalog written to `data/catalogs/benjamin-moore.json`

Status:
- Useful official importer groundwork exists.
- Current normalized file is **partial** because the site throttled/blocked most automated detail fetches during this pass.

### Sherwin-Williams
- Raw sitemap saved to `data/raw/sherwin-williams/sitemap.xml`
- Raw family model payloads saved to `data/raw/sherwin-williams/family-models.json`
- Seed codes saved to `data/raw/sherwin-williams/seed-codes.txt`
- Raw graph-crawl responses saved to `data/raw/sherwin-williams/crawl-records.json`
- Normalized catalog written to `data/catalogs/sherwin-williams.json`

Status:
- Current normalized file is **partial by design**.
- Records came from official Sherwin-Williams API responses, but the repo should not claim complete Sherwin-Williams coverage yet.

## Practical next steps

1. **Benjamin Moore:** add rate limiting / resume support / backoff and continue the official `_next/data` crawl in smaller batches.
2. **Benjamin Moore:** investigate whether the publicly exposed `occapi.benjaminmoore.com` configuration leads to a more stable color endpoint.
3. **Sherwin-Williams:** keep probing for a complete official list endpoint; otherwise continue expanding the official graph crawl with stronger seeding.
4. Add schema validation and importer resume checkpoints so long runs can be continued safely.
