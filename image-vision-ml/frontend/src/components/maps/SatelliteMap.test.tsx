import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SatelliteMap } from "./SatelliteMap";

const state = {
  resize: vi.fn(),
  setLngLat: vi.fn().mockReturnThis(),
  addTo: vi.fn().mockReturnThis(),
  markerRemove: vi.fn(),
  loadHandlers: [] as Array<() => void>,
};

vi.mock("maplibre-gl", () => ({
  default: {
    Map: vi.fn(() => ({
      addControl: vi.fn(),
      on: vi.fn((event: string, handler: () => void) => {
        if (event === "load") state.loadHandlers.push(handler);
      }),
      addSource: vi.fn(),
      addLayer: vi.fn(),
      remove: vi.fn(),
      resize: (...args: unknown[]) => state.resize(...args),
      getSource: vi.fn(),
      getLayer: vi.fn(),
      setLayoutProperty: vi.fn(),
      setPaintProperty: vi.fn(),
      fitBounds: vi.fn(),
    })),
    NavigationControl: vi.fn(),
    ScaleControl: vi.fn(),
    Marker: vi.fn(() => ({
      setLngLat: state.setLngLat,
      addTo: state.addTo,
      remove: state.markerRemove,
    })),
  },
}));

describe("SatelliteMap resize handling", () => {
  beforeEach(() => {
    state.resize.mockClear();
    state.setLngLat.mockClear();
    state.addTo.mockClear();
    state.loadHandlers.length = 0;
  });

  it("calls MapLibre resize after the map container is ready", async () => {
    render(
      <SatelliteMap
        bbox={[24.65, 42.05, 24.68, 42.08]}
        mode="ndvi"
        opacity={0.85}
        showAoi
        overlayAvailable={false}
        fillParent
      />,
    );
    expect(state.loadHandlers.length).toBeGreaterThan(0);
    state.loadHandlers.forEach((handler) => handler());
    await waitFor(() => {
      expect(state.resize).toHaveBeenCalled();
    });
  });
});
