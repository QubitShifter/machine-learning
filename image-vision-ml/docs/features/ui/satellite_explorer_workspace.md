---
feature_id: ui.satellite_explorer_workspace
name: Satellite Explorer sticky map and scientific inspector
category: ui
status: implemented
mathematical_method: CSS Grid equal-height workspace; independent inspector overflow; no scientific resampling
input_datasets: []
source_code:
- frontend/src/pages/SatelliteExplorerPage.tsx
- frontend/src/styles/index.css
- frontend/src/components/satellite/InspectorSection.tsx
- frontend/src/components/satellite/PixelInspector.tsx
- frontend/src/components/maps/SatelliteMap.tsx
- frontend/src/hooks/usePersistedBoolean.ts
- frontend/src/components/layout/AppShell.tsx
configuration:
- frontend/src/styles/index.css
outputs:
- Satellite Explorer split workspace
- independently scrolling scientific inspector
tests:
- frontend/src/app/App.test.tsx
- frontend/src/components/maps/SatelliteMap.test.tsx
documentation: docs/features/ui/satellite_explorer_workspace.md
last_verified: '2026-10-22T13:53:14Z'
related_bugs:
- BUG-0011
---

## 1. Feature ID and name

`ui.satellite_explorer_workspace` — Satellite Explorer sticky map and scientific inspector.

## 2. Status and version

Status: `implemented`. Overlay render version remains `map-overlay-v2`. Layout is CSS Grid, not a MapLibre or raster change.

## 3. Purpose

Keep the georeferenced satellite map visible while a user inspects pixel measurements, scene quality, and SCL classes. Pixel Inspector is the primary panel after a map click.

## 4. Scientific background

MapLibre displays a resampled PNG overlay. Scientific values still come from processed GeoTIFFs through `GET .../map/pixel`. Layout must not alter those samples, NDVI, reflectance, SCL assignment, or quality thresholds.

## 5. Mathematical formula or algorithm

Desktop workspace:

`grid-template-columns: minmax(0, 1fr) minmax(17.5rem, 21.25rem)` (about 75–80% map, 20–25% inspector, inspector never below 17.5 rem).

Map and inspector share visual height `clamp(22.5rem, calc(100dvh - 14.5rem), 47.5rem)` where `--workspace-chrome: 14.5rem` accounts for the 4 rem AppShell header, scene selector, and map chrome.

Page-level `position: sticky` is not used. `AppShell` `main` has `overflow-x-hidden`, which can create a scroll container and would let a sticky map overlap Historical NDVI. The workspace is a bounded equal-height grid: the map stays in view while the inspector scrolls; the whole workspace then scrolls away as a unit into charts.

Medium screens (`1024px`–`1279px`) use `minmax(16.5rem, 18.75rem)` for the inspector. Below `1024px` the grid is one column: map first (`clamp(17.5rem, 48dvh, 30rem)`), inspector below (`clamp(13.75rem, 38dvh, 26.25rem)`). Hide inspector remains available.

## 6. Explanation of every variable and unit

- `--workspace-header-offset`: 4 rem, AppShell header height.
- `--workspace-chrome`: 14.5 rem, header plus scene-selector and map toolbar allowance.
- Inspector `overflow-y: auto` with `overscroll-behavior: contain`.
- sessionStorage keys: `explorer.inspectorCollapsed`, `explorer.sceneInfoOpen` (default false), `explorer.legendOpen` (default true), `explorer.pixelOpen` (default true). Values `"1"` / `"0"`.

## 7. Worked numerical example

A 1100 px tall desktop viewport yields map height `clamp(360px, 1100px - 232px, 760px) = 868px` capped at 760 px. The inspector uses the same 760 px max-height and scrolls internally.

## 8. Source datasets and provenance

No new datasets. Pixel values continue to come from processed rasters documented under [`satellite.pixel_inspector`](../satellite/pixel_inspector.md).

## 9. Input requirements

An overlay-ready scene. Inspector panels render empty or loading states when samples or quality payloads are missing.

## 10. Processing steps

1. Render `.satellite-workspace` with map panel and inspector aside.
2. On map click, expand Pixel Inspector, scroll the aside to top (not `window`), issue pixel inspect, drop stale responses by request id.
3. Place a MapLibre marker at the clicked WGS84 coordinate without `flyTo`.
4. Changing `scene` query param clears the selected pixel.

## 11. Implementation paths and functions

`SatelliteExplorerPage`, `InspectorSection`, `PixelInspector`, `SatelliteMap` (`fillParent`, `ResizeObserver` → `map.resize()`, selected-pixel `Marker`), `usePersistedBoolean`.

Source files:

- `frontend/src/pages/SatelliteExplorerPage.tsx`
- `frontend/src/styles/index.css`
- `frontend/src/components/satellite/InspectorSection.tsx`
- `frontend/src/components/satellite/PixelInspector.tsx`
- `frontend/src/components/maps/SatelliteMap.tsx`
- `frontend/src/hooks/usePersistedBoolean.ts`
- `frontend/src/components/layout/AppShell.tsx`

## 12. Configuration parameters

CSS custom properties in `frontend/src/styles/index.css`. Breakpoint 1023 px / 1279 px. No satellite YAML changes.

## 13. Outputs and units

DOM workspace: `data-testid="satellite-workspace"` and `data-testid="satellite-inspector"`. Pixel Inspector remains `data-testid="pixel-inspector"`. Selected marker `data-testid="selected-pixel-marker"`.

## 14. Validation criteria

Map remains beside the inspector on desktop. Pixel Inspector is first. Scene Information collapsed summary still shows date, scene ID, quality, and calibration. Rejected / requires-review status is visible while collapsed. Map modes NDVI/RGB/SCL still switch overlays. Scene change clears the pixel. `window.scrollTo` is not used on inspect.

## 15. Missing-value handling

Unchanged. Masked or out-of-coverage samples stay JSON null, never measured zero. Loading state may show coordinates from the pending click before the raster response arrives.

## 16. Temporal leakage considerations

Inspection still reads only the selected scene. Layout does not join weather or soil values into the pixel sample.

## 17. Tests and expected assertions

Layout order, inspect, repeated inspect, no `window.scrollTo`, scene-change reset, collapsible `aria-expanded`, hide/show inspector, keyboard-focusable toggles, SCL/NDVI mode, MapLibre `resize` after ready.

- `frontend/src/app/App.test.tsx`
- `frontend/src/components/maps/SatelliteMap.test.tsx`

jsdom tests are not proof that sticky/overflow behaviour holds in a real browser.

## 18. Scientific limitations

Equal-height CSS does not change raster sampling. Mobile inspector height is reduced; users still expand Pixel Inspector after a click. Browser-level sticky scrolling was intentionally not used.

## 19. Related feature dependencies

- [`satellite.pixel_inspector`](../satellite/pixel_inspector.md)
- [`satellite.scl_map_overlay`](../satellite/scl_map_overlay.md)
- [`satellite.scene_histograms`](../satellite/scene_histograms.md)

## 20. Related bug/fix IDs

[`BUG-0011`](../../bugs/BUG-0011.md) — map scrolled out of view before Pixel Inspector.

## 21. Last reviewed timestamp in UTC

`2026-10-22T13:53:14Z`
