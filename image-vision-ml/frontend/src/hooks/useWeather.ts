import { useQuery } from "@tanstack/react-query";
import {
  getWeatherDaily,
  getWeatherDataset,
  getWeatherMonthly,
  getWeatherQuality,
  getWeatherSummary,
  listWeatherDatasets,
} from "@/services/weather";

export const weatherKeys = {
  datasets: ["weather", "datasets"] as const,
  dataset: (id: string) => ["weather", "dataset", id] as const,
  quality: (id: string) => ["weather", "quality", id] as const,
  monthly: (id: string) => ["weather", "monthly", id] as const,
  daily: (id: string, start?: string, end?: string) =>
    ["weather", "daily", id, start ?? "", end ?? ""] as const,
  summary: (id: string, start?: string, end?: string) =>
    ["weather", "summary", id, start ?? "", end ?? ""] as const,
};

export function useWeatherDatasets() {
  return useQuery({
    queryKey: weatherKeys.datasets,
    queryFn: listWeatherDatasets,
  });
}

export function useWeatherDataset(datasetId: string | undefined) {
  return useQuery({
    queryKey: weatherKeys.dataset(datasetId ?? ""),
    queryFn: () => getWeatherDataset(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useWeatherQuality(datasetId: string | undefined) {
  return useQuery({
    queryKey: weatherKeys.quality(datasetId ?? ""),
    queryFn: () => getWeatherQuality(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useWeatherMonthly(datasetId: string | undefined) {
  return useQuery({
    queryKey: weatherKeys.monthly(datasetId ?? ""),
    queryFn: () => getWeatherMonthly(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useWeatherDaily(
  datasetId: string | undefined,
  startDate?: string,
  endDate?: string,
) {
  return useQuery({
    queryKey: weatherKeys.daily(datasetId ?? "", startDate, endDate),
    queryFn: () => getWeatherDaily(datasetId!, startDate, endDate),
    enabled: Boolean(datasetId),
  });
}

export function useWeatherSummary(
  datasetId: string | undefined,
  startDate?: string,
  endDate?: string,
) {
  return useQuery({
    queryKey: weatherKeys.summary(datasetId ?? "", startDate, endDate),
    queryFn: () => getWeatherSummary(datasetId!, startDate, endDate),
    enabled: Boolean(datasetId),
  });
}
