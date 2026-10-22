import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { MapOverlayMetadata } from "@/types/api";
import type { DraftGeometry } from "@/utils/aoiGeometry";

interface Props {
  bbox: number[] | null | undefined;
  metadata?: MapOverlayMetadata;
  overlayUrl?: string | null;
  mode: "rgb" | "ndvi" | "scl";
  opacity: number;
  showAoi: boolean;
  overlayAvailable: boolean;
  overlayError?: string | null;
  isLoading?: boolean;
  onInspect?: (longitude: number, latitude: number) => void;
  interaction?: "inspect" | "draw-bbox" | "draw-polygon";
  onDraftGeometry?: (geometry: DraftGeometry) => void;
  draftGeometry?: DraftGeometry | null;
  selectedPoint?: { longitude: number; latitude: number } | null;
  fillParent?: boolean;
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
  interaction = "inspect",
  onDraftGeometry,
  draftGeometry,
  selectedPoint = null,
  fillParent = false,
}: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const inspectRef = useRef(onInspect);
  const draftRef = useRef(onDraftGeometry);
  const interactionRef = useRef(interaction);
  const verticesRef = useRef<number[][]>([]);
  const [cursor, setCursor] = useState<string>("");
  const [ready, setReady] = useState(false);
  const [draftHint, setDraftHint] = useState("");
  const markerRef = useRef<maplibregl.Marker | null>(null);
  inspectRef.current = onInspect;
  draftRef.current = onDraftGeometry;
  interactionRef.current = interaction;

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
      map.addSource("draft-aoi", {
        type: "geojson",
        data: emptyFeature(),
      });
      map.addLayer({
        id: "draft-fill",
        type: "fill",
        source: "draft-aoi",
        paint: { "fill-color": "#fbbf24", "fill-opacity": 0.12 },
      });
      map.addLayer({
        id: "draft-line",
        type: "line",
        source: "draft-aoi",
        paint: { "line-color": "#fbbf24", "line-width": 2, "line-dasharray": [2, 1] },
      });
      setReady(true);
    });
    map.on("mousemove", (event) => {
      setCursor(`${event.lngLat.lng.toFixed(5)}°E, ${event.lngLat.lat.toFixed(5)}°N`);
    });
    map.on("click", (event) => {
      const mode = interactionRef.current;
      const point = [event.lngLat.lng, event.lngLat.lat];
      if (mode === "draw-bbox") {
        verticesRef.current = [...verticesRef.current, point].slice(-2);
        if (verticesRef.current.length === 1) {
          setDraftHint("Click the opposite corner to close the bounding box.");
          return;
        }
        const [first, second] = verticesRef.current;
        const west = Math.min(first[0], second[0]);
        const east = Math.max(first[0], second[0]);
        const south = Math.min(first[1], second[1]);
        const north = Math.max(first[1], second[1]);
        verticesRef.current = [];
        setDraftHint("Bounding box captured. Save it as a draft; no download is started.");
        draftRef.current?.({
          type: "bbox",
          bbox: [west, south, east, north],
          coordinates: [
            [west, south], [east, south], [east, north], [west, north], [west, south],
          ],
        });
        return;
      }
      if (mode === "draw-polygon") {
        verticesRef.current = [...verticesRef.current, point];
        setDraftHint(`${verticesRef.current.length} vertices. Add at least 3, then close the polygon.`);
        return;
      }
      inspectRef.current?.(event.lngLat.lng, event.lngLat.lat);
    });
    mapRef.current = map;
    return () => {
      markerRef.current?.remove();
      markerRef.current = null;
      map.remove();
      mapRef.current = null;
      setReady(false);
    };
  }, [west, south, east, north]);

  useEffect(() => {
    const map = mapRef.current;
    const node = container.current;
    if (!map || !node || !ready) return;
    const observer = new ResizeObserver(() => {
      map.resize();
    });
    observer.observe(node);
    map.resize();
    return () => observer.disconnect();
  }, [ready, fillParent]);

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

  useEffect(() => {
    verticesRef.current = [];
    setDraftHint(
      interaction === "draw-bbox"
        ? "Click two corners to propose a bounding box."
        : interaction === "draw-polygon"
          ? "Click vertices for a proposed polygon."
          : "",
    );
  }, [interaction]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const source = map.getSource("draft-aoi") as maplibregl.GeoJSONSource | undefined;
    if (!draftGeometry?.coordinates?.length) {
      source?.setData(emptyFeature());
      return;
    }
    source?.setData({
      type: "Feature",
      properties: {},
      geometry: { type: "Polygon", coordinates: [draftGeometry.coordinates] },
    });
  }, [draftGeometry, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    if (!selectedPoint) {
      markerRef.current?.remove();
      markerRef.current = null;
      return;
    }
    const lngLat: [number, number] = [selectedPoint.longitude, selectedPoint.latitude];
    if (markerRef.current) {
      markerRef.current.setLngLat(lngLat);
      return;
    }
    const element = document.createElement("div");
    element.dataset.testid = "selected-pixel-marker";
    element.setAttribute("aria-hidden", "true");
    element.style.width = "12px";
    element.style.height = "12px";
    element.style.borderRadius = "999px";
    element.style.border = "2px solid #f8fafc";
    element.style.background = "#e08a5a";
    element.style.boxShadow = "0 0 0 2px rgba(7, 16, 24, 0.8)";
    markerRef.current = new maplibregl.Marker({ element, anchor: "center" })
      .setLngLat(lngLat)
      .addTo(map);
  }, [selectedPoint, ready]);

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
    <div className={`overflow-hidden rounded-lg border border-ink-600 ${fillParent ? "flex h-full min-h-0 flex-col" : ""}`}>
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
        {interaction === "draw-polygon" ? (
          <button
            type="button"
            className="rounded border border-ink-600 px-2 py-1"
            onClick={() => {
              const vertices = verticesRef.current;
              if (vertices.length < 3) {
                setDraftHint("A polygon needs at least three vertices.");
                return;
              }
              const ring = [...vertices, vertices[0]];
              const lons = vertices.map((item) => item[0]);
              const lats = vertices.map((item) => item[1]);
              verticesRef.current = [];
              setDraftHint("Polygon captured. Save it as a draft; no download is started.");
              draftRef.current?.({
                type: "polygon",
                bbox: [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)],
                coordinates: ring,
              });
            }}
          >
            Close polygon
          </button>
        ) : null}
        <span className="ml-auto font-mono text-slate-400" data-testid="map-cursor">
          {cursor || "Move over the map for WGS84 coordinates"}
        </span>
      </div>
      <div className={`relative min-h-0 ${fillParent ? "flex-1" : ""}`}>
        <div
          ref={container}
          className={fillParent ? "absolute inset-0 h-full w-full" : "h-[28rem] w-full"}
          data-testid="satellite-map"
        />
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
        {!isLoading && !overlayAvailable && interaction === "inspect" ? (
          <div className="absolute bottom-3 left-3 right-3 rounded bg-ink-950/80 px-3 py-2 text-xs text-slate-300">
            Overlay imagery is not available for this scene. The map shows the study AOI only.
          </div>
        ) : null}
        {draftHint ? (
          <div className="absolute bottom-3 left-3 right-3 rounded bg-ink-950/80 px-3 py-2 text-xs text-sand-200">
            {draftHint}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function emptyFeature() {
  return {
    type: "Feature" as const,
    properties: {},
    geometry: {
      type: "Polygon" as const,
      coordinates: [] as number[][][],
    },
  };
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
