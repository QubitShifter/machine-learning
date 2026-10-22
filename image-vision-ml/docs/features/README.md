# Feature documentation

This directory holds one Markdown file per significant Image Vision ML capability.

- Index: [`../feature_registry.md`](../feature_registry.md)
- Bug history: [`../bug_fix_history.md`](../bug_fix_history.md)
- Change history: [`../change_history.md`](../change_history.md)
- Layout: `satellite/`, `weather/`, `soil/`, `integration/`, `forecasting/`, `sources/`, `aoi/`, `ui/`

Validate with:

```bash
python -m scripts.check_feature_docs
```

Implemented features document the equations actually used in this repository. Planned features (in-situ soil moisture, SoilGrids properties, plant-available water, agricultural forecasting, NDMI/B11) are marked `planned` and must not be described as implemented. Modeled ERA5-Land soil water is implemented separately from measured soil moisture. Scene histograms are computed on the server from processed rasters; display RGB is not reflectance.
