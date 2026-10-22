export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      // Keep the status text when the body is not JSON.
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export function sceneRgbUrl(datasetId: string, sceneId: string): string {
  return `/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/scenes/${encodeURIComponent(sceneId)}/rgb`;
}

export function sceneNdviUrl(datasetId: string, sceneId: string): string {
  return `/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/scenes/${encodeURIComponent(sceneId)}/ndvi/preview`;
}

export function sceneMapRgbUrl(datasetId: string, sceneId: string, cacheId?: string | null): string {
  const base = `/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/scenes/${encodeURIComponent(sceneId)}/map/rgb`;
  return cacheId ? `${base}?v=${encodeURIComponent(cacheId)}` : base;
}

export function sceneMapNdviUrl(datasetId: string, sceneId: string, cacheId?: string | null): string {
  const base = `/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/scenes/${encodeURIComponent(sceneId)}/map/ndvi`;
  return cacheId ? `${base}?v=${encodeURIComponent(cacheId)}` : base;
}

export function sceneMapSclUrl(datasetId: string, sceneId: string, cacheId?: string | null): string {
  const base = `/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/scenes/${encodeURIComponent(sceneId)}/map/scl`;
  return cacheId ? `${base}?v=${encodeURIComponent(cacheId)}` : base;
}
