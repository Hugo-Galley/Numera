import type { ReactNode } from "react";

/** Entrée de tooltip Recharts, réduite à ce que les formatters utilisent. */
interface TooltipItem {
  payload?: Record<string, unknown>;
}

type TooltipResult = ReactNode | [ReactNode, ReactNode];

/** Valeur numérique d'une entrée de tooltip (Recharts 3 type `value` comme nombre, chaîne ou tableau). */
export function toNumber(value: unknown): number {
  if (typeof value === "number") return value;
  if (Array.isArray(value)) return toNumber(value[0]);
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Adapte un formatter de tooltip écrit pour des montants (`(v: number) => …`) au type de Recharts 3.
 * Le formatter reçoit toujours un nombre ; le nom de la série est une chaîne.
 */
export function numberFormatter(
  fn: (value: number, name: string, item: TooltipItem) => TooltipResult,
): (value: unknown, name: unknown, item: TooltipItem) => TooltipResult {
  return (value, name, item) => fn(toNumber(value), String(name ?? ""), item);
}

/** `itemSorter` de Tooltip : conserve l'ordre des séries du graphique (Recharts 3 trie par nom par défaut). */
export const keepSeriesOrder = (): number => 0;
