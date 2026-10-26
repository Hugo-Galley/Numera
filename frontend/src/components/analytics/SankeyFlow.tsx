import { useEffect, useMemo, useRef, useState } from "react";
import { formatCurrency } from "@/lib/utils";

const formatCurrencyShort = (value: number, currency: string) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);

interface SankeyNode {
  name: string;
  color?: string | null;
  value?: number;
}

interface SankeyLink {
  source: number;
  target: number;
  value: number;
  color?: string;
}

interface SankeyData {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

interface SankeyFlowProps {
  data: SankeyData;
  currency?: string;
}

// Layout maison (au lieu du <Sankey> de recharts) : recharts envoie tous les nœuds terminaux
// dans la dernière colonne, si bien que les flux Épargne / Investissements traversaient la
// colonne des groupes, et sa relaxation itérative croisait les liens. Ici le placement est
// déterministe : chaque nœud reste à sa profondeur naturelle, les colonnes sont ordonnées
// d'après leurs parents et les enfants descendent en cascade sous leur parent.
const DEFAULT_MARGIN = { top: 16, right: 170, bottom: 16, left: 16 };
// Écran étroit : marge droite réduite (libellés plus courts, coupés au besoin) pour laisser de la place aux flux
const NARROW_WIDTH = 520;
const MARGIN_NARROW = { top: 12, right: 92, bottom: 12, left: 10 };
const NODE_WIDTH = 4;
const LABEL_HEIGHT = 30; // hauteur réservée à un libellé de deux lignes
const NODE_GAP = 8;
const MAIN_COLUMN_HEIGHT = 320; // hauteur visée pour la colonne la plus chargée
const DEFAULT_COLOR = "#94a3b8";

interface LaidNode {
  index: number;
  name: string;
  color: string;
  value: number;
  depth: number;
  x: number;
  y: number; // haut de la barre
  height: number;
}

interface LaidLink {
  index: number;
  source: LaidNode;
  target: LaidNode;
  value: number;
  width: number;
  sy: number; // centre du lien côté source
  ty: number; // centre du lien côté cible
}

function computeLayout(data: SankeyData, width: number) {
  const MARGIN = width < NARROW_WIDTH ? MARGIN_NARROW : DEFAULT_MARGIN;
  const n = data.nodes.length;
  const links = data.links.filter((l) => l.value > 0 && l.source < n && l.target < n);
  const outLinks: number[][] = Array.from({ length: n }, () => []);
  const inLinks: number[][] = Array.from({ length: n }, () => []);
  links.forEach((l, i) => {
    outLinks[l.source].push(i);
    inLinks[l.target].push(i);
  });

  const used = data.nodes.map((_, i) => outLinks[i].length + inLinks[i].length > 0);
  const inSum = inLinks.map((ls) => ls.reduce((s, i) => s + links[i].value, 0));
  const outSum = outLinks.map((ls) => ls.reduce((s, i) => s + links[i].value, 0));
  const value = data.nodes.map((_, i) => Math.max(inSum[i], outSum[i]));

  // Profondeur = plus long chemin depuis une source (borné en cas de cycle)
  const depth = new Array(n).fill(0);
  for (let pass = 0; pass < n; pass++) {
    let changed = false;
    for (const l of links) {
      if (depth[l.target] < depth[l.source] + 1) {
        depth[l.target] = depth[l.source] + 1;
        changed = true;
      }
    }
    if (!changed) break;
  }
  const maxDepth = Math.max(1, ...depth.filter((_, i) => used[i]));
  const columns: number[][] = Array.from({ length: maxDepth + 1 }, () => []);
  data.nodes.forEach((_, i) => used[i] && columns[depth[i]].push(i));

  const maxColumnValue = Math.max(
    1,
    ...columns.map((col) => col.reduce((s, i) => s + value[i], 0)),
  );
  const k = MAIN_COLUMN_HEIGHT / maxColumnValue;
  const barHeight = (i: number) => Math.max(value[i] * k, 2);
  const slotHeight = (i: number) => Math.max(barHeight(i), LABEL_HEIGHT);

  const columnStep = (width - MARGIN.left - MARGIN.right - NODE_WIDTH) / maxDepth;
  const rank = new Array(n).fill(0);
  const y = new Array(n).fill(0);

  // Décalage (centre) d'un lien dans la barre source : liens triés par colonne puis rang de la cible.
  const sourceOffset = (linkIdx: number) => {
    const l = links[linkIdx];
    const sorted = [...outLinks[l.source]].sort(
      (a, b) => depth[links[a].target] - depth[links[b].target] || rank[links[a].target] - rank[links[b].target],
    );
    let offset = (barHeight(l.source) - outSum[l.source] * k) / 2;
    for (const i of sorted) {
      const w = links[i].value * k;
      if (i === linkIdx) return offset + w / 2;
      offset += w;
    }
    return offset;
  };

  columns.forEach((col, c) => {
    if (c === 0) {
      col.sort((a, b) => value[b] - value[a]);
    } else {
      // Ordre hérité du parent principal (le plus haut), puis ordre des liens fourni par l'API
      const key = (i: number) => {
        const first = [...inLinks[i]].sort((a, b) => y[links[a].source] - y[links[b].source])[0];
        const parent = links[first].source;
        return [y[parent], outLinks[parent].indexOf(first)];
      };
      const keys = new Map(col.map((i) => [i, key(i)]));
      col.sort((a, b) => keys.get(a)![0] - keys.get(b)![0] || keys.get(a)![1] - keys.get(b)![1]);
    }
    col.forEach((i, r) => (rank[i] = r));

    let cursor = MARGIN.top;
    for (const i of col) {
      const slot = slotHeight(i);
      let desiredTop = cursor;
      if (c > 0) {
        // Centré sur l'arrivée de ses flux entrants, sans jamais remonter au-dessus du voisin
        const total = inSum[i] || 1;
        const center = inLinks[i].reduce(
          (s, li) => s + (y[links[li].source] + sourceOffset(li)) * links[li].value,
          0,
        ) / total;
        desiredTop = center - slot / 2;
      }
      const top = Math.max(desiredTop, cursor);
      y[i] = top + (slot - barHeight(i)) / 2;
      cursor = top + slot + NODE_GAP;
    }
  });

  const laidNodes: LaidNode[] = data.nodes.map((node, i) => ({
    index: i,
    name: node.name,
    color: node.color || DEFAULT_COLOR,
    value: value[i],
    depth: depth[i],
    x: MARGIN.left + depth[i] * columnStep,
    y: y[i],
    height: barHeight(i),
  }));

  const laidLinks: LaidLink[] = links.map((l, i) => {
    const sorted = [...inLinks[l.target]].sort((a, b) => y[links[a].source] - y[links[b].source]);
    let offset = (barHeight(l.target) - inSum[l.target] * k) / 2;
    for (const j of sorted) {
      if (j === i) break;
      offset += links[j].value * k;
    }
    const w = l.value * k;
    return {
      index: i,
      source: laidNodes[l.source],
      target: laidNodes[l.target],
      value: l.value,
      width: w,
      sy: y[l.source] + sourceOffset(i),
      ty: y[l.target] + offset + w / 2,
    };
  });

  const bottom = Math.max(
    ...laidNodes.filter((_, i) => used[i]).map((nd) => nd.y + nd.height / 2 + LABEL_HEIGHT / 2),
  );

  return {
    nodes: laidNodes.filter((_, i) => used[i]),
    links: laidLinks,
    height: Math.max(240, bottom + MARGIN.bottom),
    narrow: width < NARROW_WIDTH,
  };
}

interface TooltipState {
  x: number;
  y: number;
  title: string;
  value: number;
}

export function SankeyFlow({ data, currency = "EUR" }: SankeyFlowProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);

  const isEmpty = !data || !data.nodes || data.nodes.length === 0 || !data.links || data.links.length === 0;

  // Dépend de isEmpty : pendant le chargement l'état vide est rendu sans le conteneur mesuré,
  // il faut donc (re)brancher l'observer quand les données arrivent.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(el);
    setWidth(el.clientWidth);
    return () => observer.disconnect();
  }, [isEmpty]);

  const layout = useMemo(
    () => (isEmpty || width < 200 ? null : computeLayout(data, width)),
    [data, width, isEmpty],
  );

  if (isEmpty) {
    return (
      <div className="flex items-center justify-center h-[200px] text-slate-400">
        {/* `data` vaut null tant que l'API n'a pas répondu : ce n'est pas encore « pas de données » */}
        {data ? "Pas assez de données pour générer le diagramme de flux." : "Chargement du diagramme…"}
      </div>
    );
  }

  const showTooltip = (e: React.MouseEvent, title: string, value: number) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top, title, value });
  };
  const hideTooltip = () => {
    setTooltip(null);
    setHovered(null);
  };

  return (
    <div
      ref={containerRef}
      className="relative w-full bg-white border border-slate-200 rounded-sm overflow-hidden"
      style={{ height: layout?.height ?? 400 }}
    >
      {layout && (
        <svg width={width} height={layout.height} className="block">
          <defs>
            {layout.links.map((l) => (
              // userSpaceOnUse : en objectBoundingBox, un lien parfaitement horizontal (boîte de hauteur nulle) n'est pas peint
              <linearGradient
                key={l.index}
                id={`sankey-link-${l.index}`}
                gradientUnits="userSpaceOnUse"
                x1={l.source.x + NODE_WIDTH}
                y1={0}
                x2={l.target.x}
                y2={0}
              >
                <stop offset="0%" stopColor={l.source.color} />
                <stop offset="100%" stopColor={l.target.color} />
              </linearGradient>
            ))}
          </defs>

          {layout.links.map((l) => {
            const x0 = l.source.x + NODE_WIDTH;
            const x1 = l.target.x;
            const xm = (x0 + x1) / 2;
            return (
              <path
                key={l.index}
                d={`M${x0},${l.sy} C${xm},${l.sy} ${xm},${l.ty} ${x1},${l.ty}`}
                fill="none"
                stroke={`url(#sankey-link-${l.index})`}
                strokeOpacity={hovered === null ? 0.25 : hovered === l.index ? 0.5 : 0.12}
                strokeWidth={Math.max(l.width, 1)}
                className="transition-[stroke-opacity] duration-150 cursor-default"
                onMouseMove={(e) => {
                  setHovered(l.index);
                  showTooltip(e, `${l.source.name} → ${l.target.name}`, l.value);
                }}
                onMouseLeave={hideTooltip}
              />
            );
          })}

          {layout.nodes.map((nd) => {
            const cy = nd.y + nd.height / 2;
            const labelX = nd.x + NODE_WIDTH + 6;
            // Écran étroit : libellé tronqué pour tenir dans la marge droite
            const label = layout.narrow && nd.name.length > 13 ? `${nd.name.slice(0, 12)}…` : nd.name;
            return (
              <g
                key={nd.index}
                onMouseMove={(e) => showTooltip(e, nd.name, nd.value)}
                onMouseLeave={hideTooltip}
              >
                <rect x={nd.x} y={nd.y} width={NODE_WIDTH} height={nd.height} fill={nd.color} />
                {/* Halo blanc pour rester lisible quand le libellé passe sur les flux sortants */}
                <text
                  x={labelX}
                  y={cy - 3}
                  fontSize="11"
                  fontWeight="600"
                  fill="#1e293b"
                  stroke="#ffffff"
                  strokeWidth={3}
                  paintOrder="stroke"
                >
                  {label}
                </text>
                <text
                  x={labelX}
                  y={cy + 10}
                  fontSize="10"
                  fontWeight="500"
                  fill="#64748b"
                  stroke="#ffffff"
                  strokeWidth={3}
                  paintOrder="stroke"
                  className="amount-blur"
                >
                  {formatCurrencyShort(nd.value, currency)}
                </text>
              </g>
            );
          })}
        </svg>
      )}

      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 bg-white border border-slate-200 shadow-md px-2 py-1.5 text-xs"
          style={{
            left: Math.min(tooltip.x + 12, width - 180),
            top: tooltip.y + 12,
          }}
        >
          <div className="font-semibold text-slate-800">{tooltip.title}</div>
          <div className="text-slate-500 amount-blur">{formatCurrency(tooltip.value, currency)}</div>
        </div>
      )}
    </div>
  );
}
