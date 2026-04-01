"use client";

import { useDeferredValue, useMemo, useState } from "react";

import { searchEntities } from "@/lib/demo";

export function useSearch(initialQuery = "") {
  const [query, setQuery] = useState(initialQuery);
  const deferredQuery = useDeferredValue(query);

  const results = useMemo(() => searchEntities(deferredQuery), [deferredQuery]);

  return {
    query,
    setQuery,
    results,
  };
}
