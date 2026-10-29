import { formatCurrency } from "@/lib/utils";
import { useEffect, useMemo, useRef, useState } from "react";
import { NODE_WIDTH, SankeyData, computeLayout } from "./sankeyLayout";

const formatCurrencyShort = (value: number, currency: string) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);

interface SankeyFlowProps {
  data: SankeyData;
  currency?: string;
  /** Clic sur un nœud de catégorie de dépense (drill-down vers les transactions) */
  onCategoryClick?: (categoryId: number, name: string) => void;
}
interface TooltipState {
  x: number;
  y: number;
  title: string;
  value: number;
}

export function SankeyFlow({ data, currency = "EUR", onCategoryClick }: SankeyFlowProps) {
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
                {...(onCategoryClick && data.nodes[nd.index]?.category_id != null
                  ? {
                      role: "button",
                      className: "cursor-pointer",
                      onClick: () => onCategoryClick(data.nodes[nd.index].category_id!, nd.name),
                    }
                  : {})}
              >
                {/* Zone de clic élargie : la barre d'une petite catégorie ne fait que quelques pixels */}
                {onCategoryClick && data.nodes[nd.index]?.category_id != null && (
                  <rect x={nd.x - 4} y={Math.min(nd.y, cy - 16)} width={NODE_WIDTH + 100} height={Math.max(nd.height, 32)} fill="transparent" />
                )}
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
