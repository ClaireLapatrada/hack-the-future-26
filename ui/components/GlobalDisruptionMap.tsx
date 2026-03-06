"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { ComposableMap, Geographies, Geography, Line, Marker, ZoomableGroup } from "react-simple-maps";
import planningConfig from "../../planning_config.json";

const geoUrl =
  "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

export function GlobalDisruptionMap({
  disruptionRisk,
  activeDisruptions,
}: {
  disruptionRisk: number;
  activeDisruptions: number;
}) {
  const router = useRouter();
  type PlanningConfig = {
    airfreight_rates?: Record<string, { rate_per_kg: number; transit_days: number }>;
  };

  const pc = planningConfig as PlanningConfig;
  const laneKeys = Object.keys(pc.airfreight_rates ?? {});
  const defaultLaneKey = "Taiwan|Germany";
  const [originCountry, destCountry] = (laneKeys[0] ?? defaultLaneKey).split("|") as [string, string];

  const countryCoords: Record<string, [number, number]> = {
    Taiwan: [121, 23.5],
    Germany: [10, 51],
    Vietnam: [108, 15],
  };

  const originCoord = countryCoords[originCountry] ?? [121.5, 31.2];
  const destCoord = countryCoords[destCountry] ?? [4.5, 52.0];

  const countryMeta: Record<
    string,
    { code: string; label: string; cityCountry: string; roleLabel: "Origin" | "Destination" }
  > = {
    Taiwan: {
      code: "TW-TAIWAN",
      label: "SemiTech Asia · Taiwan",
      cityCountry: "Taiwan",
      roleLabel: "Origin",
    },
    Germany: {
      code: "DE-GERMANY",
      label: "BMW / VW import hub",
      cityCountry: "Germany",
      roleLabel: "Destination",
    },
    Vietnam: {
      code: "VN-VIETNAM",
      label: "PlastiMold Vietnam · VN",
      cityCountry: "Vietnam",
      roleLabel: "Origin",
    },
  };

  const originMeta =
    countryMeta[originCountry] ?? {
      code: originCountry.toUpperCase(),
      label: originCountry,
      cityCountry: originCountry,
      roleLabel: "Origin" as const,
    };

  const destMeta =
    countryMeta[destCountry] ?? {
      code: destCountry.toUpperCase(),
      label: destCountry,
      cityCountry: destCountry,
      roleLabel: "Destination" as const,
    };
  // Map points derived from disruption regions / severity (representative, not lat/long-precise)
  type MapPoint = {
    id: string;
    label: string;
    code: string;
    region: string;
    age: string;
    status: string;
    coordinates: [number, number]; // [lon, lat]
    severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
    href: string;
  };

  const points: MapPoint[] = [
    {
      id: "EVT-SHIPPING-ASIA",
      label: "Trans-Pacific vessel delays — 9hr avg wait",
      code: "DSR-2024-027",
      region: "Pacific, US West",
      age: "4h ago",
      status: "Monitoring",
      coordinates: [140, 35],
      severity: "MEDIUM",
      href: "/disruptions?id=EVT-2024-007",
    },
    {
      id: "EVT-SUEZ",
      label: "Suez Canal transit delays — 18hr avg wait time",
      code: "DSR-2024-0843",
      region: "Suez, EG",
      age: "2h ago",
      status: "Monitoring",
      coordinates: [32.5, 30],
      severity: "HIGH",
      href: "/disruptions?id=EVT-2026-0228-004",
    },
    {
      id: "EVT-RED-SEA",
      label: "Red Sea risk corridor — reroutes via Cape",
      code: "DSR-2024-071",
      region: "Red Sea",
      age: "6h ago",
      status: "Mitigation in-progress",
      coordinates: [42, 18],
      severity: "CRITICAL",
      href: "/disruptions?id=EVT-2024-011",
    },
    {
      id: "EVT-ALT-ROUTE",
      label: "Cape of Good Hope reroute — 12d added lead time",
      code: "DSR-2024-055",
      region: "Cape Town, ZA",
      age: "1d ago",
      status: "Mitigation accepted",
      coordinates: [20, -34],
      severity: "MEDIUM",
      href: "/disruptions?id=EVT-2024-007",
    },
  ];

  const linePath: [number, number][] = [
    originCoord, // origin from planning_config
    [55, 18], // Indian Ocean
    [32.5, 30.0], // Suez
    destCoord, // destination from planning_config
  ];

  const severityColor = (severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW") => {
    if (severity === "CRITICAL") return "#ef4444";
    if (severity === "HIGH") return "#eab308";
    if (severity === "MEDIUM") return "#22d3ee"; // agentCyan — same as disruption page pill-medium-severity
    return "#94a3b8";
  };

  const [hovered, setHovered] = useState<MapPoint | null>(null);
  const [hoveredEndpoint, setHoveredEndpoint] = useState<"origin" | "dest" | null>(null);

  const wrapLabel = (label: string): { line1: string; line2?: string } => {
    if (label.length <= 34) return { line1: label };
    const breakIndex = label.lastIndexOf(" ", 34);
    const idx = breakIndex > 20 ? breakIndex : 34;
    return {
      line1: label.slice(0, idx),
      line2: label.slice(idx + 1),
    };
  };

  return (
    <div className="glass-card flex h-full flex-col overflow-hidden px-4 py-3">
      <div className="mb-3 flex items-center justify-between text-xs font-mono">
        <span className="rounded-full border border-agentCyan/40 bg-agentCyan/10 px-2 py-1 text-agentCyan">
          Global Disruption Map · Live
        </span>
        <span className="text-textMuted">
          {activeDisruptions} active · Risk {disruptionRisk}
        </span>
      </div>
      <div className="relative flex-1 overflow-hidden rounded-xl border border-white/5 bg-[#020617]">
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{ scale: 140 }}
          style={{ width: "100%", height: "100%", outline: "none" }}
          tabIndex={-1}
          onMouseDown={(e: React.MouseEvent<HTMLElement>) => {
            // prevent browser focus ring / blue box when clicking map background
            e.preventDefault();
          }}
        >
          <ZoomableGroup
            center={[20, 10]}
            zoom={1}
            minZoom={0.8}
            maxZoom={6}
          >
            <Geographies geography={geoUrl}>
              {({ geographies }) =>
                (geographies as Array<{ rsmKey: string; [key: string]: unknown }>).map((geo) => (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill="#0b1120"          // lighter land mass
                    stroke="#1f2937"        // brighter border
                    strokeWidth={0.6}
                  />
                ))
              }
            </Geographies>
            {/* Origin marker (derived from planning_config airfreight_rates) */}
            <Marker
              coordinates={originCoord}
              onMouseEnter={() => setHoveredEndpoint("origin")}
              onMouseLeave={() =>
                setHoveredEndpoint((cur) => (cur === "origin" ? null : cur))
              }
            >
              <circle r={4.5} fill="#ffffff" />
              {hoveredEndpoint === "origin" && (
                <g transform="translate(0,-90)">
                  <>
                    <rect
                      x={-127}
                      y={-50}
                      width={260}
                      height={80}
                      rx={10}
                      fill="#020617"
                      stroke="#ffffff"
                      strokeWidth={1.4}
                    />
                    <text
                      x={-116}
                      y={-34}
                      fill="#ffffff"
                      fontSize={9}
                      fontFamily="JetBrains Mono, ui-monospace, monospace"
                    >
                      SOURCE
                    </text>
                    <text
                      x={-2}
                      y={-34}
                      textAnchor="end"
                      fill="#9ca3af"
                      fontSize={9}
                      fontFamily="JetBrains Mono, ui-monospace, monospace"
                    >
                      {originMeta.code}
                    </text>
                    <text
                      x={-116}
                      y={-16}
                      fill="#e5e7eb"
                      fontSize={11}
                      fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'SF Pro Text'"
                    >
                      {originMeta.label}
                    </text>
                    <text
                      x={-116}
                      y={4}
                      fill="#9ca3af"
                      fontSize={9}
                      fontFamily="JetBrains Mono, ui-monospace, monospace"
                    >
                      {originMeta.cityCountry}
                    </text>
                    <text
                      x={122}
                      y={4}
                      textAnchor="end"
                      fill="#9ca3af"
                      fontSize={9}
                      fontFamily="JetBrains Mono, ui-monospace, monospace"
                    >
                      Route start
                    </text>
                    <text
                      x={-116}
                      y={20}
                      fill="#7dd3fc"
                      fontSize={9}
                      fontFamily="JetBrains Mono, ui-monospace, monospace"
                    >
                      Origin
                    </text>
                  </>
                </g>
              )}
            </Marker>
            {/* Destination marker (derived from planning_config airfreight_rates) with pulsing to indicate flow direction */}
            <Marker
              coordinates={destCoord}
              onMouseEnter={() => setHoveredEndpoint("dest")}
              onMouseLeave={() =>
                setHoveredEndpoint((cur) => (cur === "dest" ? null : cur))
              }
            >
              <circle
                className="map-dot-pulse"
                r={7}
                stroke="#ffffff"
                fill="none"
              />
              <circle r={4} fill="#ffffff" />
              {hoveredEndpoint === "dest" && (
                <g transform="translate(0,-90)">
                  <>
                    <rect
                      x={-127}
                      y={-50}
                      width={260}
                      height={80}
                      rx={10}
                      fill="#020617"
                      stroke="#ffffff"
                      strokeWidth={1.4}
                    />
                    <text
                      x={-116}
                      y={-34}
                      fill="#ffffff"
                      fontSize={9}
                      fontFamily="JetBrains Mono, ui-monospace, monospace"
                    >
                      DESTINATION
                    </text>
                    <text
                      x={15}
                      y={-34}
                      textAnchor="end"
                      fill="#9ca3af"
                      fontSize={9}
                      fontFamily="JetBrains Mono, ui-monospace, monospace"
                    >
                      {destMeta.code}
                    </text>
                    <text
                      x={-116}
                      y={-16}
                      fill="#e5e7eb"
                      fontSize={11}
                      fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'SF Pro Text'"
                    >
                      {destMeta.label}
                    </text>
                    <text
                      x={-116}
                      y={4}
                      fill="#9ca3af"
                      fontSize={9}
                      fontFamily="JetBrains Mono, ui-monospace, monospace"
                    >
                      {destMeta.cityCountry}
                    </text>
                    <text
                      x={122}
                      y={4}
                      textAnchor="end"
                      fill="#9ca3af"
                      fontSize={9}
                      fontFamily="JetBrains Mono, ui-monospace, monospace"
                    >
                      Route end
                    </text>
                    <text
                      x={-116}
                      y={20}
                      fill="#7dd3fc"
                      fontSize={9}
                      fontFamily="JetBrains Mono, ui-monospace, monospace"
                    >
                      Destination
                    </text>
                  </>
                </g>
              )}
            </Marker>
            {/* Route line (Asia -> Europe) as animated dashed arc toward destination */}
            <Line
              from={linePath[0]}
              to={linePath[linePath.length - 1]}
              stroke="#ffffff"
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeDasharray="4 6"
              className="route-dash"
            />
            {/* Animated nodes for each disruption point + inline hover cards */}
            {points.map((p) => (
              <Marker
                key={p.id}
                coordinates={p.coordinates}
                onMouseEnter={() => setHovered(p)}
                onMouseLeave={() => setHovered((cur) => (cur?.id === p.id ? null : cur))}
                onClick={() => router.push(p.href)}
              >
                <circle
                  className="map-dot-pulse"
                  r={8}
                  stroke={severityColor(p.severity)}
                  fill="none"
                />
                <circle r={4} fill={severityColor(p.severity)} />
                {hovered?.id === p.id && (
                  <g transform="translate(0,-90)">
                    {(() => {
                      const { line1, line2 } = wrapLabel(p.label);
                      return (
                        <>
                          <rect
                            x={-127}
                            y={-50}
                            width={260}
                            height={92}
                            rx={10}
                            fill="#020617"
                            stroke={severityColor(p.severity)}
                            strokeWidth={1.4}
                          />
                          <text
                            x={-116}
                            y={-34}
                            fill={severityColor(p.severity)}
                            fontSize={9}
                            fontFamily="JetBrains Mono, ui-monospace, monospace"
                          >
                            {p.severity}
                          </text>
                          <text
                            x={-2}
                            y={-34}
                            textAnchor="end"
                            fill="#9ca3af"
                            fontSize={9}
                            fontFamily="JetBrains Mono, ui-monospace, monospace"
                          >
                            {p.code}
                          </text>
                          <text
                            x={-116}
                            y={-16}
                            fill="#e5e7eb"
                            fontSize={11}
                            fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'SF Pro Text'"
                          >
                            {line1}
                          </text>
                          {line2 && (
                            <text
                              x={-116}
                              y={-2}
                              fill="#e5e7eb"
                              fontSize={11}
                              fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'SF Pro Text'"
                            >
                              {line2}
                            </text>
                          )}
                          <text
                            x={-116}
                            y={18}
                            fill="#9ca3af"
                            fontSize={9}
                            fontFamily="JetBrains Mono, ui-monospace, monospace"
                          >
                            {p.region}
                          </text>
                          <text
                            x={122}
                            y={18}
                            textAnchor="end"
                            fill="#9ca3af"
                            fontSize={9}
                            fontFamily="JetBrains Mono, ui-monospace, monospace"
                          >
                            {p.age}
                          </text>
                          <text
                            x={-116}
                            y={34}
                            fill="#7dd3fc"
                            fontSize={9}
                            fontFamily="JetBrains Mono, ui-monospace, monospace"
                          >
                            {p.status}
                          </text>
                        </>
                      );
                    })()}
                  </g>
                )}
              </Marker>
            ))}
          </ZoomableGroup>
        </ComposableMap>
        {/* Grid overlay + scale bar */}
        <div className="pointer-events-none absolute inset-0">
          <div className="h-full w-full [background-image:linear-gradient(#1f29331a_1px,transparent_1px),linear-gradient(90deg,#1f29331a_1px,transparent_1px)] [background-size:40px_40px]" />
          <div className="absolute bottom-4 right-4 flex items-center gap-2 rounded-md bg-black/40 px-2 py-1 text-[10px] font-mono text-slate-300">
            <div className="h-px w-16 bg-slate-400" />
            <span>2000 km</span>
          </div>
        </div>
        {/* Legend overlay */}
        <div className="pointer-events-none absolute bottom-4 left-4 flex gap-4 text-[10px] font-mono text-textMuted">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-agentCyan" />
            <span>Origin</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-warning" />
            <span>Chokepoint</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-danger" />
            <span>Critical bottleneck</span>
          </div>
        </div>
      </div>
    </div>
  );
}

