import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

interface Props {
  bbox: number[] | null | undefined;
}

export function AoiMap({ bbox }: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!container.current || mapRef.current) return;
    const [west, south, east, north] = bbox && bbox.length === 4
      ? bbox
      : [24.65, 42.05, 24.68, 42.08];
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
        data: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "Polygon",
            coordinates: [[
              [west, south],
              [east, south],
              [east, north],
              [west, north],
              [west, south],
            ]],
          },
        },
      });
      map.addLayer({
        id: "aoi-fill",
        type: "fill",
        source: "aoi",
        paint: { "fill-color": "#4fb87a", "fill-opacity": 0.18 },
      });
      map.addLayer({
        id: "aoi-line",
        type: "line",
        source: "aoi",
        paint: { "line-color": "#7dce9a", "line-width": 2 },
      });
      map.fitBounds([[west, south], [east, north]], { padding: 40, maxZoom: 14 });
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [bbox]);

  return (
    <div className="overflow-hidden rounded-lg border border-ink-600">
      <div ref={container} className="h-80 w-full" data-testid="aoi-map" />
      <p className="bg-ink-800 px-3 py-1 text-[11px] text-slate-400">
        WGS84 study AOI. Scene PNGs are shown separately; they are not stretched onto this map.
      </p>
    </div>
  );
}
