import i18n from "i18next"
import { appLocale } from "@/i18n/locale"
import React from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import { formatAmountWithShare, formatRate } from '@/lib/utils';

interface AllocationItem {
  name: string;
  value: number;
  percentage: number;
}

/** Compte d'un groupe d'allocation, tel qu'affiché dans le détail d'un clic sur un graphique. */
export interface DrillItem {
  account_id: number
  account_name?: string | null
  percentage_of_group?: number | null
  value: number
}

/** Nœud renvoyé par Recharts au clic : les données du groupe sont imbriquées dans `payload`, à des profondeurs variables. */
export interface DrillNode {
  name?: string
  items?: DrillItem[]
  payload?: DrillNode
}

/** Nœud de treemap renvoyé par Recharts au clic (`depth === 2` : une feuille). */
export type TreemapNode = DrillNode & { depth?: number }

interface AllocationTreemapProps {
  data: AllocationItem[];
  onItemClick?: (item: TreemapNode) => void;
}

const COLORS = [
  "#f43f5e", // Rose 500
  "#3b82f6", // Blue 500
  "#6366f1", // Indigo 500
  "#8b5cf6", // Violet 500
  "#ec4899", // Pink 500
  "#f97316", // Orange 500
  "#a855f7", // Purple 500
  "#d946ef", // Fuchsia 500
  "#06b6d4", // Cyan 500
  "#10b981", // Emerald 500
];

interface CellProps {
  x: number
  y: number
  width: number
  height: number
  index: number
  name: string
  value: number
  percentage: number
  depth: number
}

// Recharts clone l'élément `content` en lui injectant ces props : toutes optionnelles pour le typage de `<CustomizedContent />`
const CustomizedContent = (props: Partial<CellProps>) => {
  const { x = 0, y = 0, width = 0, height = 0, index = 0, name = "", value = 0, percentage = 0, depth = 0 } = props;

  // Render leaf nodes
  if (depth !== 2) return null;
  if (width <= 0 || height <= 0) return null;

  // Légende « nom • % » si elle tient dans la case, sinon le % seul, sinon rien (jamais de texte qui déborde)
  const captionSize = width > 120 ? 12 : 10;
  const fits = (text: string) => text.length * captionSize * 0.6 <= width - 12;
  const full = `${name} • ${formatRate(percentage, 1)}`;
  const short = formatRate(percentage, 1);
  const caption = fits(full) ? full : fits(short) ? short : null;

  return (
    <g className="cursor-pointer transition-opacity hover:opacity-90">
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill: COLORS[index % COLORS.length],
          stroke: '#fff',
          strokeWidth: 2,
          strokeOpacity: 1,
          rx: 8,
          ry: 8
        }}
      />
      {width > 40 && height > 40 && (
        <text
          x={x + width / 2}
          y={y + height / 2 - 8}
          textAnchor="middle"
          fill="#fff"
          fontSize={width > 120 ? 16 : 12}
          fontWeight="bold"
          className="pointer-events-none select-none"
        >
          {new Intl.NumberFormat(appLocale(), { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value)}
        </text>
      )}
      {caption && height > 50 && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 15}
          textAnchor="middle"
          fill="#fff"
          fillOpacity={0.9}
          fontSize={captionSize}
          className="pointer-events-none select-none"
        >
          {caption}
        </text>
      )}
    </g>
  );
};

export const AllocationTreemap: React.FC<AllocationTreemapProps> = ({ data, onItemClick }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[260px] md:h-[400px] bg-slate-50 rounded-xl border border-dashed border-slate-200">
        <p className="text-slate-400 font-medium">{i18n.t("allocationTreemap.aucuneDonneeDAllocationDisponible", { ns: "settings" })}</p>
      </div>
    );
  }

  return (
    <div className="theme-island w-full h-[300px] md:h-[400px] bg-slate-900 rounded-xl overflow-hidden">
      <ResponsiveContainer width="100%" height="100%">
        <Treemap
          data={[{ name: 'root', children: data }]}
          dataKey="value"
          aspectRatio={4 / 3}
          stroke="#fff"
          content={<CustomizedContent />}
          isAnimationActive={false}
          onClick={(node: TreemapNode) => {
            if (node && node.depth === 2 && onItemClick) {
              onItemClick(node);
            }
          }}
        >
          <Tooltip 
            formatter={(value: number, name: string) => [formatAmountWithShare(value, data.reduce((sum, i) => sum + (i.value || 0), 0)), name]}
            contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
          />
        </Treemap>
      </ResponsiveContainer>
    </div>
  );
};
