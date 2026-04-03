import type { KpiStat } from "@/types/domain";
import type { LiveOverviewResponse } from "@/types/api";

type RawOverviewResponse = {
  headline: string;
  operational?: string[];
  stats?: KpiStat[];
};

export function normalizeOverviewResponse(payload: RawOverviewResponse): LiveOverviewResponse {
  return {
    headline: payload.headline,
    operational: payload.operational ?? [],
    stats: payload.stats ?? [],
  };
}
