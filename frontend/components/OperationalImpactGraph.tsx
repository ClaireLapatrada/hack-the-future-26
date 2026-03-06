"use client";

type Line = { line_id: string; product: string; at_risk: boolean };
type Dep = { item_id: string; supplier_id: string; single_source: boolean; line_id: string };

type OperationalImpactGraphProps = {
  affectedProductionLines: Line[];
  criticalDependencies: Dep[];
  supplierNames?: Record<string, string>;
  /** All suppliers from profile (id + name). When provided, graph shows every supplier; edges still come from criticalDependencies only. */
  allSuppliers?: Array<{ id: string; name: string }>;
};

export function OperationalImpactGraph({
  affectedProductionLines,
  criticalDependencies,
  supplierNames = {},
  allSuppliers,
}: OperationalImpactGraphProps) {
  const suppliersFromDeps = [...new Set(criticalDependencies.map((d) => d.supplier_id))];
  const suppliers = allSuppliers?.length
    ? allSuppliers.map((s) => s.id)
    : suppliersFromDeps;
  const items = [...new Set(criticalDependencies.map((d) => d.item_id))];
  const lines = affectedProductionLines;
  const singleSourceIds = new Set(criticalDependencies.filter((d) => d.single_source).map((d) => d.supplier_id));
  const supplierNameMap = allSuppliers?.length
    ? Object.fromEntries(allSuppliers.map((s) => [s.id, s.name]))
    : supplierNames;

  const w = 600;
  const h = 240;
  const pad = 40;
  const labelRowY = 22;
  const contentTop = 48;
  const contentBottom = h - pad;
  const contentHeight = contentBottom - contentTop;
  const supplierBoxWidth = 100;
  const itemBoxWidth = 100;
  const lineBoxWidth = 120;
  const col1 = pad + supplierBoxWidth / 2 + 20;
  const col2 = w / 2;
  const col3 = w - pad - lineBoxWidth / 2;

  const supplierY = (i: number) => contentTop + (i * contentHeight) / Math.max(1, suppliers.length);
  const itemY = (i: number) => contentTop + (i * contentHeight) / Math.max(1, items.length);
  const lineY = (i: number) => contentTop + (i * contentHeight) / Math.max(1, lines.length);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-full w-full max-w-full" style={{ aspectRatio: `${w} / ${h}` }} preserveAspectRatio="xMidYMid meet" aria-label="Operational impact supply network">
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="1" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {/* Edges: supplier -> item -> line */}
      {criticalDependencies.map((d, i) => {
        const si = suppliers.indexOf(d.supplier_id);
        const ii = items.indexOf(d.item_id);
        const li = lines.findIndex((l) => l.line_id === d.line_id);
        if (si < 0 || ii < 0 || li < 0) return null;
        const x1 = col1 + supplierBoxWidth / 2;
        const y1 = supplierY(si);
        const x2Start = col2 - itemBoxWidth / 2;
        const x2End = col2 + itemBoxWidth / 2;
        const y2 = itemY(ii);
        const x3 = col3;
        const y3 = lineY(li);
        const single = d.single_source;
        const lineLeft = col3 - lineBoxWidth / 2;
        return (
          <g key={`${d.supplier_id}-${d.item_id}-${d.line_id}-${i}`}>
            <path
              d={`M ${x1} ${y1} C ${(x1 + x2Start) / 2} ${y1}, ${(x1 + x2Start) / 2} ${y2}, ${x2Start} ${y2}`}
              fill="none"
              stroke={single ? "rgba(239, 68, 68, 0.5)" : "rgba(255,255,255,0.15)"}
              strokeWidth={single ? 2 : 1}
              strokeDasharray={single ? "4 2" : undefined}
            />
            <path
              d={`M ${x2End} ${y2} C ${(lineLeft + x2End) / 2} ${y2}, ${(lineLeft + x2End) / 2} ${y3}, ${lineLeft} ${y3}`}
              fill="none"
              stroke={single ? "rgba(239, 68, 68, 0.5)" : "rgba(255,255,255,0.15)"}
              strokeWidth={single ? 2 : 1}
              strokeDasharray={single ? "4 2" : undefined}
            />
          </g>
        );
      })}
      {/* Nodes: Suppliers */}
      <g fill="none" stroke="rgba(34, 211, 238, 0.6)" strokeWidth="1.5">
        {suppliers.map((id, i) => (
          <rect
            key={id}
            x={col1 - supplierBoxWidth / 2}
            y={supplierY(i) - 12}
            width={supplierBoxWidth}
            height="24"
            rx="4"
            fill="rgba(18,23,31,0.9)"
            className={singleSourceIds.has(id) ? "stroke-danger/60" : ""}
          />
        ))}
      </g>
      {suppliers.map((id, i) => (
        <g key={`label-${id}`}>
          <title>{supplierNameMap[id] || id}</title>
          <text
            x={col1}
            y={supplierY(i) + 4}
            textAnchor="middle"
            className="fill-textPrimary text-[9px] font-mono"
          >
            {(supplierNameMap[id] || id).length > 14 ? (supplierNameMap[id] || id).slice(0, 12) + "…" : supplierNameMap[id] || id}
          </text>
        </g>
      ))}
      {/* Nodes: Items */}
      <g fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1">
        {items.map((itemId, i) => (
          <rect
            key={itemId}
            x={col2 - itemBoxWidth / 2}
            y={itemY(i) - 10}
            width={itemBoxWidth}
            height="20"
            rx="3"
            fill="rgba(18,23,31,0.95)"
          />
        ))}
      </g>
      {items.map((itemId, i) => (
        <g key={`item-${itemId}`}>
          <title>{itemId}</title>
          <text
            x={col2}
            y={itemY(i) + 3}
            textAnchor="middle"
            className="fill-textMuted text-[9px] font-mono"
          >
            {itemId.length > 16 ? itemId.slice(0, 14) + "…" : itemId}
          </text>
        </g>
      ))}
      {/* Nodes: Production lines */}
      <g fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1">
        {lines.map((l, i) => (
          <rect
            key={l.line_id}
            x={col3 - lineBoxWidth / 2}
            y={lineY(i) - 12}
            width={lineBoxWidth}
            height="24"
            rx="4"
            fill={l.at_risk ? "rgba(239, 68, 68, 0.12)" : "rgba(18,23,31,0.9)"}
            className={l.at_risk ? "stroke-danger/50" : ""}
          />
        ))}
      </g>
      {lines.map((l, i) => {
        const label = l.product || l.line_id;
        return (
          <g key={`line-${l.line_id}`}>
            <title>{label}</title>
            <text
              x={col3}
              y={lineY(i) + 4}
              textAnchor="middle"
              className={`text-[9px] font-mono ${l.at_risk ? "fill-danger" : "fill-textPrimary"}`}
            >
              {label.length > 16 ? label.slice(0, 14) + "…" : label}
            </text>
          </g>
        );
      })}
      {/* Labels — above content area to avoid overlap */}
      <text x={col1} y={labelRowY} textAnchor="middle" className="fill-textMuted text-[9px] font-mono uppercase">
        Suppliers
      </text>
      <text x={col2} y={labelRowY} textAnchor="middle" className="fill-textMuted text-[9px] font-mono uppercase">
        Components
      </text>
      <text x={col3} y={labelRowY} textAnchor="middle" className="fill-textMuted text-[9px] font-mono uppercase">
        Production lines
      </text>
    </svg>
  );
}
