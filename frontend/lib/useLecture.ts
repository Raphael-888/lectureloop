"use client";

// Load a lecture's concepts (polling while it is still processing). Shared by the
// overview and review pages.

import { useEffect, useMemo, useState } from "react";
import * as api from "@/lib/api";
import { groupConcepts } from "@/lib/groups";
import type { ConceptsResponse } from "@/lib/types";

export function useLecture(lectureId: string) {
  const [data, setData] = useState<ConceptsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        for (let i = 0; i < 160 && !cancelled; i++) {
          const c = await api.getConcepts(lectureId);
          if (c.status === "ready") return setData(c);
          if (c.status === "failed") throw new Error(c.error || "This lecture could not be processed.");
          await new Promise((r) => setTimeout(r, 1500));
        }
      } catch (e) {
        if (!cancelled) setError(api.errorMessage(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [lectureId]);

  const concepts = useMemo(() => data?.concepts ?? [], [data]);
  const blocks = useMemo(() => groupConcepts(concepts), [concepts]);
  const nameOf = useMemo(() => {
    const names = new Map(concepts.map((c) => [c.id, c.name]));
    return (id: string) => names.get(id) ?? id;
  }, [concepts]);

  return { lecture: data, concepts, blocks, nameOf, error };
}
