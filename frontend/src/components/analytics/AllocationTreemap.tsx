import React from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';

interface AllocationItem {
  name: string;
  value: number;
  percentage: number;
}

interface AllocationTreemapProps {
  data: AllocationItem[];
  onItemClick?: (item: any) => void;
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

const CustomizedContent = (props: any) => {
  const { x, y, width, height, index, name, value, percentage, depth } = props;

  // Render leaf nodes
  if (depth !== 2) return null;
  if (width <= 0 || height <= 0) return null;

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
          {new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value)}
        </text>
      )}
      {width > 60 && height > 50 && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 15}
          textAnchor="middle"
          fill="#fff"
          fillOpacity={0.9}
          fontSize={width > 120 ? 12 : 10}
          className="pointer-events-none select-none"
        >
          {name} • {percentage} %
        </text>
      )}
    </g>
  );
};

export const AllocationTreemap: React.FC<AllocationTreemapProps> = ({ data, onItemClick }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[400px] bg-slate-50 rounded-xl border border-dashed border-slate-200">
        <p className="text-slate-400 font-medium">Aucune donnée d'allocation disponible.</p>
      </div>
    );
  }

  return (
    <div className="w-full h-[400px] bg-slate-900 rounded-xl overflow-hidden">
      <ResponsiveContainer width="100%" height="100%">
        <Treemap
          data={[{ name: 'root', children: data }]}
          dataKey="value"
          aspectRatio={4 / 3}
          stroke="#fff"
          content={<CustomizedContent />}
          isAnimationActive={false}
          onClick={(node: any) => {
            if (node && node.depth === 2 && onItemClick) {
              onItemClick(node);
            }
          }}
        >
          <Tooltip 
            formatter={(value: number) => [new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value), "Valeur"]}
            contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }}
          />
        </Treemap>
      </ResponsiveContainer>
    </div>
  );
};
