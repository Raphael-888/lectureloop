// Group a lecture's concepts into a few topic blocks for the tree views.
//
// The concept graph (C) is flat: concepts with page numbers and prerequisite links. The
// overview and the concept map show them as 2–4 blocks in lecture order, so the page does not
// become a wall of chips. Blocks are cut where the slide numbers jump the most, which is where
// a lecturer usually changes topic. If C adds a `topic` field later, use it here instead.

import type { Concept } from "./types";

export interface ConceptBlock {
  n: number;
  title: string;
  pages: string; // "4–8"
  concepts: Concept[];
}

const firstPage = (c: Concept) => Math.min(...c.pages);

export function groupConcepts(concepts: Concept[]): ConceptBlock[] {
  if (concepts.length === 0) return [];
  const sorted = [...concepts].sort((a, b) => firstPage(a) - firstPage(b));
  const wanted = Math.min(4, Math.max(1, Math.round(sorted.length / 4)));

  // cut at the (wanted - 1) largest jumps in page number
  const gaps = sorted.slice(1).map((c, i) => ({ at: i + 1, size: firstPage(c) - firstPage(sorted[i]) }));
  const cuts = gaps
    .filter((g) => g.size >= 2)
    .sort((a, b) => b.size - a.size)
    .slice(0, wanted - 1)
    .map((g) => g.at)
    .sort((a, b) => a - b);

  const blocks: Concept[][] = [];
  let start = 0;
  for (const cut of [...cuts, sorted.length]) {
    blocks.push(sorted.slice(start, cut));
    start = cut;
  }

  return blocks.map((group, i) => {
    const lo = Math.min(...group.map(firstPage));
    const hi = Math.max(...group.flatMap((c) => c.pages));
    return {
      n: i + 1,
      title: blockTitle(group),
      pages: lo === hi ? `${lo}` : `${lo}–${hi}`,
      concepts: group,
    };
  });
}

// "Loss function vs metric · Expected risk · …": the first two names, which is what a
// student recognises; a nicer title can come from the model later.
function blockTitle(group: Concept[]): string {
  const names = group.map((c) => c.name);
  if (names.length <= 2) return names.join(" & ");
  return `${names[0]} → ${names[names.length - 1]}`;
}
