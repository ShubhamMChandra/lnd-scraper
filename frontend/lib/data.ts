import { EnrichedCompany } from "./types";
import resultsData from "./results.json";

export function getResults(): EnrichedCompany[] {
  return resultsData as EnrichedCompany[];
}

export function getAllSources(results: EnrichedCompany[]): string[] {
  const sources = new Set<string>();
  results.forEach((r) => r.company.sources.forEach((s) => sources.add(s)));
  return Array.from(sources).sort();
}
