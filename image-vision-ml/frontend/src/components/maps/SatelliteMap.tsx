import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { MapOverlayMetadata } from "@/types/api";

interface Props {
  bbox: number[] | null | undefined;
  metadata?: MapOverlayMetadata;
  overlayUrl?: string | null;
  mode: "rgb" | "ndvi";
  opacity: number;
  showAoi: boolean;
  overlayAvailable: boolean;
  overlayError?: string | null;
  isLoading?: boolean;
  onInspect?: (longitude: number, latitude: number) => void;
}

const DEFAULT_BBOX = [24.65, 42.05, 24.68, 42.08];

export function SatelliteMap({
  bbox,
  metadata,
  overlayUrl,
  mode,
  opacity,
  showAoi,
  overlayAvailable,
  overlayError,
  isLoading,
  onInspect,
}: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const inspectRef = useRef(onInspect);
  const [cursor, setCursor] = useState<string>("");
  const [ready, setReady] = useState(false);
  inspectRef.current = onInspect;

  const [west, south, east, north] = bbox && bbox.length === 4 ? bbox : DEFAULT_BBOX;

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: "https://tiles.openfreemap.org/styles/dark",
      center: [(west + east) / 2, (south + north) / 2],
      zoom: 12,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.on("load", () => {
      map.addSource("aoi", {
        type: "geojson",
        data: aoiFeature(west, south, east, north),
      });
      map.addLayer({
        id: "aoi-fill",
        type: "fill",
        source: "aoi",
        paint: { "fill-color": "#4fb87a", "fill-opacity": 0.12 },
      });
      map.addLayer({
        id: "aoi-line",
        type: "line",
        source: "aoi",
        paint: { "line-color": "#7dce9a", "line-width": 2 },
      });
      setReady(true);
    });
    map.on("mousemove", (event) => {
      setCursor(`${event.lngLat.lng.toFixed(5)}°E, ${event.lngLat.lat.toFixed(5)}°N`);
    });
    map.on("click", (event) => {
      inspectRef.current?.(event.lngLat.lng, event.lngLat.lat);
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      setReady(false);
    };
  }, [west, south, east, north]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const source = map.getSource("aoi") as maplibregl.GeoJSONSource | undefined;
    source?.setData(aoiFeature(west, south, east, north));
  }, [west, south, east, north, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const visibility = showAoi ? "visible" : "none";
    if (map.getLayer("aoi-fill")) map.setLayoutProperty("aoi-fill", "visibility", visibility);
    if (map.getLayer("aoi-line")) map.setLayoutProperty("aoi-line", "visibility", visibility);
  }, [showAoi, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const coordinates = metadata?.maplibre_coordinates;
    if (!overlayAvailable || !overlayUrl || !coordinates || coordinates.length !== 4) {
      if (map.getLayer("scene-overlay")) map.removeLayer("scene-overlay");
      if (map.getSource("scene-overlay")) map.removeSource("scene-overlay");
      return;
    }
    const existing = map.getSource("scene-overlay") as maplibregl.ImageSource | undefined;
    if (existing) {
      existing.updateImage({ url: overlayUrl, coordinates: coordinates as maplibregl.Coordinates });
    } else {
      map.addSource("scene-overlay", {
        type: "image",
        url: overlayUrl,
        coordinates: coordinates as maplibregl.Coordinates,
      });
      const before = map.getLayer("aoi-line") ? "aoi-line" : undefined;
      map.addLayer({
        id: "scene-overlay",
        type: "raster",
        source: "scene-overlay",
        paint: { "raster-opacity": opacity, "raster-fade-duration": 0 },
      }, before);
    }
  }, [overlayUrl, overlayAvailable, metadata, ready, opacity]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !map.getLayer("scene-overlay")) return;
    map.setPaintProperty("scene-overlay", "raster-opacity", opacity);
  }, [opacity, ready]);

  const fitAoi = () => {
    mapRef.current?.fitBounds([[west, south], [east, north]], { padding: 40, maxZoom: 15 });
  };
  const fitScene = () => {
    const extent = metadata?.geographic_extent;
    if (!extent || extent.west == null) return;
    mapRef.current?.fitBounds(
      [[extent.west, extent.south ?? south], [extent.east ?? east, extent.north ?? north]],
      { padding: 40, maxZoom: 16 },
    );
  };

  return (
    <div className="overflow-hidden rounded-lg border border-ink-600">
      <div className="flex flex-wrap gap-2 border-b border-ink-700 bg-ink-800 px-3 py-2 text-xs">
        <button type="button" className="rounded border border-ink-600 px-2 py-1" onClick={fitAoi}>
          Fit AOI
        </button>
        <button
          type="button"
          className="rounded border border-ink-600 px-2 py-1 disabled:opacity-40"
          onClick={fitScene}
          disabled={!metadata?.geographic_extent}
        >
          Fit scene
        </button>
        <span className="ml-auto font-mono text-slate-400" data-testid="map-cursor">
          {cursor || "Move over the map for WGS84 coordinates"}
        </span>
      </div>
      <div className="relative">
        <div ref={container} className="h-[36rem] w-full" data-testid="satellite-map" />
        {isLoading ? (
          <div className="absolute inset-x-0 top-0 bg-ink-950/70 px-3 py-1 text-xs text-sand-200">
            Loading {mode.toUpperCase()} overlay…
          </div>
        ) : null}
        {overlayError ? (
          <div className="absolute inset-x-0 top-0 bg-rust-500/20 px-3 py-1 text-xs" role="alert">
            {overlayError}
          </div>
        ) : null}
        {!isLoading && !overlayAvailable ? (
          <div className="absolute bottom-3 left-3 right-3 rounded bg-ink-950/80 px-3 py-2 text-xs text-slate-300">
            Overlay imagery is not available for this scene. The map shows the study AOI only.
          </div>
        ) : null}
      </div>
    </div>
  );
}

function aoiFeature(west: number, south: number, east: number, north: number) {
  return {
    type: "Feature" as const,
    properties: {},
    geometry: {
      type: "Polygon" as const,
      coordinates: [[
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
      ]],
    },
  };
}
