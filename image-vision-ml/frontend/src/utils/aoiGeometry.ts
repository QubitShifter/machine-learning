export const MIN_AREA_KM2 = 0.01;
export const MAX_AREA_KM2 = 2500;
export const MAX_EDGE_DEG = 2;

export interface DraftGeometry {
  type: "bbox" | "polygon";
  bbox: number[];
  coordinates: number[][];
}

export function bboxAreaKm2(west: number, south: number, east: number, north: number): number {
  const meanLat = ((south + north) / 2) * (Math.PI / 180);
  const widthM = Math.abs(east - west) * 111320 * Math.cos(meanLat);
  const heightM = Math.abs(north - south) * 110574;
  return (widthM * heightM) / 1_000_000;
}

export function validateBbox(bbox: number[]): string | null {
  if (bbox.length !== 4) return "Bounding box must be [west, south, east, north].";
  const [west, south, east, north] = bbox;
  if (west >= east) return "West must be less than east.";
  if (south >= north) return "South must be less than north.";
  if (east - west > MAX_EDGE_DEG || north - south > MAX_EDGE_DEG) {
    return `Edges must be at most ${MAX_EDGE_DEG} degrees in this phase.`;
  }
  const area = bboxAreaKm2(west, south, east, north);
  if (area < MIN_AREA_KM2) return `Area ${area.toFixed(4)} km² is below the minimum.`;
  if (area > MAX_AREA_KM2) return `Area ${area.toFixed(1)} km² exceeds the maximum.`;
  return null;
}

export function polygonAreaKm2(ring: number[][]): number {
  if (ring.length < 4) return 0;
  const originLat = ring.slice(0, -1).reduce((sum, vertex) => sum + vertex[1], 0) / (ring.length - 1);
  const metersLon = 111320 * Math.cos(originLat * (Math.PI / 180));
  const xs = ring.map((vertex) => (vertex[0] - ring[0][0]) * metersLon);
  const ys = ring.map((vertex) => (vertex[1] - ring[0][1]) * 110574);
  let twice = 0;
  for (let index = 0; index < xs.length - 1; index += 1) {
    twice += xs[index] * ys[index + 1] - xs[index + 1] * ys[index];
  }
  return Math.abs(twice) / 2 / 1_000_000;
}
