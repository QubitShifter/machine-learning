import type { AoiDraft, AoiRegistry } from "@/types/api";
import { getJson } from "./api";

export async function listAoiAreas(): Promise<AoiRegistry> {
  return getJson("/api/v1/aoi/areas");
}

export async function createAoiDraft(payload: {
  name?: string;
  geometry_type: "bbox" | "polygon";
  bbox?: number[];
  coordinates?: number[][];
}): Promise<AoiDraft> {
  const response = await fetch("/api/v1/aoi/drafts", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Keep status text.
    }
    throw new Error(detail);
  }
  return (await response.json()) as AoiDraft;
}
