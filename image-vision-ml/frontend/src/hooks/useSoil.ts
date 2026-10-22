import { useQuery } from "@tanstack/react-query";
import {
  getCombinedSoilWeather,
  getSoilDaily,
  getSoilDataset,
  getSoilMonthly,
  getSoilQuality,
  getWetness,
  listSoilDatasets,
} from "@/services/soil";

export const soilKeys = {
  datasets: ["soil", "datasets"] as const,
  dataset: (id: string) => ["soil", "dataset", id] as const,
  quality: (id: string) => ["soil", "quality", id] as const,
  monthly: (id: string) => ["soil", "monthly", id] as const,
  daily: (id: string, start?: string, end?: string) =>
    ["soil", "daily", id, start ?? "", end ?? ""] as const,
  wetness: (id: string, start?: string, end?: string) =>
    ["soil", "wetness", id, start ?? "", end ?? ""] as const,
  combined: (soilId: string, weatherId: string, start?: string, end?: string) =>
    ["soil", "combined", soilId, weatherId, start ?? "", end ?? ""] as const,
};

export function useSoilDatasets() {
  return useQuery({
    queryKey: soilKeys.datasets,
    queryFn: listSoilDatasets,
  });
}

export function useSoilDataset(datasetId: string | undefined) {
  return useQuery({
    queryKey: soilKeys.dataset(datasetId ?? ""),
    queryFn: () => getSoilDataset(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useSoilQuality(datasetId: string | undefined) {
  return useQuery({
    queryKey: soilKeys.quality(datasetId ?? ""),
    queryFn: () => getSoilQuality(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useSoilMonthly(datasetId: string | undefined) {
  return useQuery({
    queryKey: soilKeys.monthly(datasetId ?? ""),
    queryFn: () => getSoilMonthly(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useSoilDaily(
  datasetId: string | undefined,
  startDate?: string,
  endDate?: string,
) {
  return useQuery({
    queryKey: soilKeys.daily(datasetId ?? "", startDate, endDate),
    queryFn: () => getSoilDaily(datasetId!, startDate, endDate),
    enabled: Boolean(datasetId),
  });
}

export function useWetness(
  weatherDatasetId: string | undefined,
  startDate?: string,
  endDate?: string,
) {
  return useQuery({
    queryKey: soilKeys.wetness(weatherDatasetId ?? "", startDate, endDate),
    queryFn: () => getWetness(weatherDatasetId!, startDate, endDate),
    enabled: Boolean(weatherDatasetId),
  });
}

export function useCombinedSoilWeather(
  soilDatasetId: string | undefined,
  weatherDatasetId: string | undefined,
  startDate?: string,
  endDate?: string,
) {
  return useQuery({
    queryKey: soilKeys.combined(
      soilDatasetId ?? "",
      weatherDatasetId ?? "",
      startDate,
      endDate,
    ),
    queryFn: () => getCombinedSoilWeather(soilDatasetId!, weatherDatasetId!, startDate, endDate),
    enabled: Boolean(soilDatasetId && weatherDatasetId),
  });
}
