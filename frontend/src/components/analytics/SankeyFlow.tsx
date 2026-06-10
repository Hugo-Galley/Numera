import { ResponsiveContainer, Sankey, Tooltip, Rectangle, Layer } from "recharts";

interface SankeyNode {
  name: string;
  color?: string;
  value: number;
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

const formatCurrencyShort = (value: number, currency: string) => {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: currency,
    maximumFractionDigits: 0,
  }).format(value);
};

const CustomNode = (props: any) => {
  const { x, y, width, height, index, payload, containerWidth, currency } = props;
  const isOut = x + width + 40 > containerWidth;
  
  return (
    <Layer key={`node-${index}`}>
      <Rectangle
        x={x}
        y={y}
        width={width}
        height={height}
        fill={payload.color || "#0f172a"}
        fillOpacity={1}
      />
      <text
        x={x + (isOut ? -8 : width + 8)}
        y={y + height / 2 - 4}
        textAnchor={isOut ? "end" : "start"}
        verticalAnchor="middle"
        fontSize="10"
        fontWeight="bold"
        fill="#1e293b"
      >
        {payload.name}
      </text>
      <text
        x={x + (isOut ? -8 : width + 8)}
        y={y + height / 2 + 8}
        textAnchor={isOut ? "end" : "start"}
        verticalAnchor="middle"
        fontSize="9"
        fontWeight="500"
        fill="#64748b"
      >
        {formatCurrencyShort(payload.value, currency)}
      </text>
    </Layer>
  );
};

const CustomLink = (props: any) => {
  const { sourceX, targetX, sourceY, targetY, sourceControlX, targetControlX, linkWidth, index, payload } = props;
  const gradientId = `link-gradient-${index}`;

  return (
    <Layer key={`link-${index}`}>
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={payload.source.color || "#e2e8f0"} stopOpacity={0.2} />
          <stop offset="100%" stopColor={payload.target.color || "#e2e8f0"} stopOpacity={0.2} />
        </linearGradient>
      </defs>
      <path
        d={`
          M${sourceX},${sourceY}
          C${sourceControlX},${sourceY} ${targetControlX},${targetY} ${targetX},${targetY}
        `}
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth={Math.max(linkWidth, 1)}
        strokeLinecap="butt"
      />
    </Layer>
  );
};

export function SankeyFlow({ data, currency = "EUR" }: SankeyFlowProps) {
  if (!data || !data.nodes || data.nodes.length === 0 || data.links.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        Pas assez de données pour générer le diagramme de flux.
      </div>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: currency,
    }).format(value);
  };

  return (
    <div className="h-full w-full bg-white border border-slate-200 rounded-sm overflow-hidden">
      <ResponsiveContainer width="100%" height="100%">
        <Sankey
          data={data}
          node={<CustomNode currency={currency} />}
          link={<CustomLink />}
          nodeWidth={4}
          nodePadding={40}
          margin={{ top: 20, right: 100, bottom: 20, left: 100 }}
        >
          <Tooltip
            isAnimationActive={false}
            contentStyle={{
              borderRadius: "0px",
              border: "1px solid #e2e8f0",
              boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
              padding: "8px",
            }}
            formatter={(value: number) => [formatCurrency(value), "Montant"]}
          />
        </Sankey>
      </ResponsiveContainer>
    </div>
  );
}
