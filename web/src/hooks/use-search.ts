"use client";

import { useDeferredValue, useEffect, useState } from "react";

import type { EntitySummary } from "@/types/domain";

export function useSearch(initialQuery = "") {
  const [query, setQuery] = useState(initialQuery);
  const deferredQuery = useDeferredValue(query);
  const [results, setResults] = useState<EntitySummary[]>([]);

  useEffect(() => {
    const controller = new AbortController();

    void (async () => {
      try {
        const searchParams = new URLSearchParams();
        if (deferredQuery) {
          searchParams.set("query", deferredQuery);
        }
        const response = await fetch(`/api/investigate/search?${searchParams.toString()}`, {
          signal: controller.signal,
          cache: "no-store",
        });
        const payload = (await response.json()) as { results?: EntitySummary[] };
        if (!response.ok) {
          setResults([]);
          return;
        }
        setResults(payload.results ?? []);
      } catch (error) {
        if ((error as Error).name === "AbortError") {
          return;
        }
        setResults([]);
      }
    })();

    return () => controller.abort();
  }, [deferredQuery]);

  return {
    query,
    setQuery,
    results,
  };
}
