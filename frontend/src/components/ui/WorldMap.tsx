import React, { useMemo, useState } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
  Sphere,
  Graticule,
  ZoomableGroup
} from "react-simple-maps";
import { scaleLinear } from "d3-scale";

const geoUrl = "https://unpkg.com/world-atlas@2.0.2/countries-110m.json";

interface WorldMapProps {
  data: Array<{ name: string; value: number; percentage: number }>;
}

const WorldMap: React.FC<WorldMapProps> = ({ data }) => {
  const [position, setPosition] = useState({ coordinates: [0, 0], zoom: 1 });
  const [hoveredCountry, setHoveredCountry] = useState<{ name: string; value: number; percentage: number; x: number; y: number } | null>(null);

  const colorScale = useMemo(() => {
    const values = data.map((d) => d.value);
    const maxValue = Math.max(...values, 1);

    return scaleLinear<string>()
      .domain([0, 0.001, maxValue])
      .range(["#f1f5f9", "#64748b", "#0f172a"]);
  }, [data]);

  const countryDataMap = useMemo(() => {
    const map: Record<string, { value: number; percentage: number; displayName: string }> = {};

    const CODE_ALIASES: Record<string, string[]> = {
      USA: ["USA", "840", "UNITED STATES", "UNITED STATES OF AMERICA", "ÉTATS-UNIS", "ETATS-UNIS"],
      FRA: ["FRA", "250", "FRANCE"],
      DEU: ["DEU", "276", "GERMANY", "ALLEMAGNE"],
      JPN: ["JPN", "392", "JAPAN", "JAPON"],
      GBR: ["GBR", "826", "UNITED KINGDOM", "ROYAUME-UNI", "UK"],
      CHE: ["CHE", "756", "SWITZERLAND", "SUISSE"],
      NLD: ["NLD", "528", "NETHERLANDS", "PAYS-BAS"],
      CHN: ["CHN", "156", "CHINA", "CHINE"],
      IND: ["IND", "356", "INDIA", "INDE"],
      TWN: ["TWN", "158", "TAIWAN", "TAÏWAN"],
      KOR: ["KOR", "410", "SOUTH KOREA", "KOREA", "CORÉE DU SUD"],
      BRA: ["BRA", "076", "76", "BRAZIL", "BRÉSIL"],
      CAN: ["CAN", "124", "CANADA"],
      AUS: ["AUS", "036", "36", "AUSTRALIA", "AUSTRALIE"],
      SWE: ["SWE", "752", "SWEDEN", "SUÈDE"],
      DNK: ["DNK", "208", "DENMARK", "DANEMARK"],
      ESP: ["ESP", "724", "SPAIN", "ESPAGNE"],
      ITA: ["ITA", "380", "ITALY", "ITALIE"],
      IRL: ["IRL", "372", "IRELAND", "IRLANDE"],
      BEL: ["BEL", "056", "56", "BELGIQUE", "BELGIUM"],
      AUT: ["AUT", "040", "40", "AUSTRIA", "AUTRICHE"],
      FIN: ["FIN", "246", "FINLAND", "FINLANDE"],
      NOR: ["NOR", "578", "NORWAY", "NORVÈGE"],
      SGP: ["SGP", "702", "SINGAPORE", "SINGAPOUR"],
      HKG: ["HKG", "344", "HONG KONG"],
      MEX: ["MEX", "484", "MEXICO", "MEXIQUE"],
      ZAF: ["ZAF", "710", "SOUTH AFRICA", "AFRIQUE DU SUD"],
      SAU: ["SAU", "682", "SAUDI ARABIA", "ARABIE SAOUDITE"],
      POL: ["POL", "616", "POLAND", "POLOGNE"],
      PRT: ["PRT", "620", "PORTUGAL"],
    };

    data.forEach((d) => {
      const upper = d.name.toUpperCase().trim();
      let matchedCode: string | null = null;
      for (const [code, aliases] of Object.entries(CODE_ALIASES)) {
        if (code === upper || aliases.some((a) => a === upper || upper.includes(a))) {
          matchedCode = code;
          break;
        }
      }

      const keysToRegister = matchedCode ? CODE_ALIASES[matchedCode] : [upper];
      keysToRegister.forEach((key) => {
        if (map[key]) {
          map[key].value += d.value;
        } else {
          map[key] = { value: d.value, percentage: d.percentage, displayName: d.name };
        }
      });
    });

    return map;
  }, [data]);

  const handleMoveEnd = (position: { coordinates: [number, number]; zoom: number }) => {
    setPosition(position);
  };

  return (
    <div className="relative w-full h-full bg-slate-50/50 rounded-xl overflow-hidden border border-slate-100 dark:border-slate-800 shadow-inner group">
      <ComposableMap
        projectionConfig={{ rotate: [-10, 0, 0], scale: 140 }}
        className="w-full h-full"
      >
        <ZoomableGroup
          zoom={position.zoom}
          center={position.coordinates as [number, number]}
          onMoveEnd={handleMoveEnd}
          maxZoom={8}
        >
          <Sphere id="sphere" stroke="#cbd5e1" strokeWidth={0.5} fill="transparent" />
          <Graticule stroke="#cbd5e1" strokeWidth={0.3} step={[10, 10]} />
          <Geographies geography={geoUrl}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const countryName = geo.properties.name.toUpperCase();
                const countryId = geo.id?.toString().toUpperCase();
                const d = countryDataMap[countryId] || countryDataMap[countryName];
                
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={d ? colorScale(d.value) : "#f8fafc"}
                    stroke="#94a3b8"
                    strokeWidth={0.4}
                    onMouseEnter={(e) => {
                      if (d) {
                        setHoveredCountry({
                          name: geo.properties.name,
                          value: d.value,
                          percentage: d.percentage,
                          x: e.clientX,
                          y: e.clientY
                        });
                      }
                    }}
                    onMouseMove={(e) => {
                      if (d) {
                        setHoveredCountry(prev => prev ? { ...prev, x: e.clientX, y: e.clientY } : null);
                      }
                    }}
                    onMouseLeave={() => setHoveredCountry(null)}
                    style={{
                      default: { outline: "none", transition: "all 250ms" },
                      hover: { fill: d ? "#0f172a" : "#cbd5e1", outline: "none", cursor: d ? "pointer" : "default" },
                      pressed: { outline: "none" }
                    }}
                  />
                );
              })
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>

      {/* Custom Tooltip */}
      {hoveredCountry && (
        <div 
          className="fixed z-[9999] pointer-events-none bg-slate-900 text-white p-3 rounded-lg shadow-2xl border border-slate-700 transform -translate-x-1/2 -translate-y-[calc(100%+10px)]"
          style={{ left: hoveredCountry.x, top: hoveredCountry.y }}
        >
          <div className="space-y-1 min-w-[150px]">
            <p className="font-bold text-sm border-b border-slate-700 pb-1 mb-1">{hoveredCountry.name}</p>
            <div className="flex justify-between gap-4 text-xs">
              <span className="text-slate-400">Investi</span>
              <span className="font-mono font-bold">
                {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(hoveredCountry.value)}
              </span>
            </div>
            <div className="flex justify-between gap-4 text-xs">
              <span className="text-slate-400">Part du portef.</span>
              <span className="font-bold text-slate-200">{hoveredCountry.percentage.toFixed(1)}%</span>
            </div>
          </div>
          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-full w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[6px] border-t-slate-900"></div>
        </div>
      )}
        
      {/* Controls Overlay */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button 
          onClick={() => setPosition(p => ({ ...p, zoom: Math.min(p.zoom * 1.5, 8) }))}
          className="w-8 h-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md shadow-sm flex items-center justify-center text-slate-600 dark:text-slate-300 hover:bg-slate-50 transition-colors"
        >
          +
        </button>
        <button 
          onClick={() => setPosition(p => ({ ...p, zoom: Math.max(p.zoom / 1.5, 1), coordinates: p.zoom <= 1.5 ? [0, 0] : p.coordinates }))}
          className="w-8 h-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md shadow-sm flex items-center justify-center text-slate-600 dark:text-slate-300 hover:bg-slate-50 transition-colors"
        >
          -
        </button>
      </div>
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 p-2 bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm rounded-lg border border-slate-200 dark:border-slate-800 text-[10px] text-slate-500 shadow-sm">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-24 h-1.5 bg-gradient-to-r from-[#f1f5f9] via-[#64748b] to-[#0f172a] rounded-full border border-slate-200 dark:border-slate-700" />
        </div>
        <div className="flex justify-between px-0.5 font-medium">
          <span>0</span>
          <span>Investissement Max</span>
        </div>
      </div>
    </div>
  );
};

export default WorldMap;
