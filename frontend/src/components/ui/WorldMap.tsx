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
      .range(["#f1f5f9", "#818cf8", "#1e1b4b"]);
  }, [data]);

  const countryDataMap = useMemo(() => {
    const map: Record<string, { value: number; percentage: number; displayName: string }> = {};
    const normalize = (name: string) => {
      const n = name.toUpperCase().trim();
      if (n === "USA" || n === "UNITED STATES" || n === "UNITED STATES OF AMERICA" || n === "ÉTATS-UNIS") return "USA";
      if (n === "FRANCE" || n === "FRA") return "FRANCE";
      return n;
    };
    data.forEach((d) => {
      const normalizedName = normalize(d.name);
      if (map[normalizedName]) {
        map[normalizedName].value += d.value;
      } else {
        map[normalizedName] = { value: d.value, percentage: d.percentage, displayName: d.name };
      }
    });
    return map;
  }, [data]);

  const handleMoveEnd = (position: { coordinates: [number, number]; zoom: number }) => {
    setPosition(position);
  };

  return (
    <div className="relative w-full h-full bg-slate-50/50 rounded-xl overflow-hidden border border-slate-100 shadow-inner group">
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
                const countryId = geo.id?.toUpperCase();
                const d = countryDataMap["USA"] && (countryName.includes("UNITED STATES") || countryId === "USA" || geo.properties.name === "United States")
                  ? countryDataMap["USA"]
                  : (countryDataMap[countryId] || countryDataMap[countryName]);
                
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
                      hover: { fill: d ? "#4338ca" : "#cbd5e1", outline: "none", cursor: d ? "pointer" : "default" },
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
              <span className="font-bold text-emerald-400">{hoveredCountry.percentage}%</span>
            </div>
          </div>
          {/* Arrow */}
          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-full w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[6px] border-t-slate-900"></div>
        </div>
      )}
        
      {/* Controls Overlay */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button 
          onClick={() => setPosition(p => ({ ...p, zoom: Math.min(p.zoom * 1.5, 8) }))}
          className="w-8 h-8 bg-white border border-slate-200 rounded-md shadow-sm flex items-center justify-center text-slate-600 hover:bg-slate-50 transition-colors"
        >
          +
        </button>
        <button 
          onClick={() => setPosition(p => ({ ...p, zoom: Math.max(p.zoom / 1.5, 1), coordinates: p.zoom <= 1.5 ? [0, 0] : p.coordinates }))}
          className="w-8 h-8 bg-white border border-slate-200 rounded-md shadow-sm flex items-center justify-center text-slate-600 hover:bg-slate-50 transition-colors"
        >
          -
        </button>
      </div>
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 p-2 bg-white/80 backdrop-blur-sm rounded-lg border border-slate-200 text-[10px] text-slate-500 shadow-sm">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-24 h-1.5 bg-gradient-to-r from-[#f1f5f9] via-[#818cf8] to-[#1e1b4b] rounded-full border border-slate-200" />
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
