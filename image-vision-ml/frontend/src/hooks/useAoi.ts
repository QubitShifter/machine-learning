import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createAoiDraft, listAoiAreas } from "@/services/aoi";

export const aoiKeys = {
  areas: ["aoi", "areas"] as const,
};

export function useAoiRegistry() {
  return useQuery({
    queryKey: aoiKeys.areas,
    queryFn: listAoiAreas,
  });
}

export function useCreateAoiDraft() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: createAoiDraft,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: aoiKeys.areas });
    },
  });
}
