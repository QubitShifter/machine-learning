# Agricultural data-source registry

Machine-readable catalogue: [`registry.yaml`](registry.yaml).

Statuses:

- `operational` — downloaded, processed, and used in the current archive.
- `implemented` — code and configuration exist; a complete live archive may still be pending.
- `planned` — investigated, not ingested.
- `paused` — official access route is unavailable.

This registry does not download data. ERA5-Land soil-water live CDS retrieval is opt-in through `python -m scripts.soil_dataset download`.
