"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const AXIS_COLOR = "#6b6b6b";
const GRID_COLOR = "#262626";

/** Compact axis label formatter — "1234" -> "1.2k", "12000" -> "12k". */
function fmtAxis(v: number): string {
  if (v == null || isNaN(v)) return "";
  const n = Number(v);
  if (Math.abs(n) >= 1000) {
    return `${(n / 1000).toFixed(n % 1000 === 0 ? 0 : 1)}k`;
  }
  // Drop unnecessary decimals
  return Number.isInteger(n) ? n.toString() : n.toFixed(1);
}

const tooltipStyle = {
  background: "#141414",
  border: "1px solid #262626",
  borderRadius: 8,
  fontSize: 12,
  color: "#f5f5f5",
};

type Datum = Record<string, number | string>;

export function TrendArea({
  data,
  dataKey,
  color = "var(--color-recovery)",
  unit = "",
  height = 180,
  xKey = "date",
}: {
  data: Datum[];
  dataKey: string;
  color?: string;
  unit?: string;
  height?: number;
  xKey?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.4} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID_COLOR} vertical={false} />
        <XAxis
          dataKey={xKey}
          stroke={AXIS_COLOR}
          fontSize={10}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: string) => (typeof v === "string" ? v.slice(5) : String(v))}
          minTickGap={24}
        />
        <YAxis stroke={AXIS_COLOR} fontSize={10} tickLine={false} axisLine={false} width={44} tickFormatter={fmtAxis} />
        <Tooltip
          contentStyle={tooltipStyle}
          cursor={{ stroke: GRID_COLOR }}
          formatter={(v) => [`${v}${unit}`, dataKey] as [string, string]}
        />
        <Area
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          strokeWidth={2}
          fill={`url(#grad-${dataKey})`}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function TrendLine({
  data,
  dataKey,
  color = "var(--color-recovery)",
  unit = "",
  height = 180,
  xKey = "date",
}: {
  data: Datum[];
  dataKey: string;
  color?: string;
  unit?: string;
  height?: number;
  xKey?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={GRID_COLOR} vertical={false} />
        <XAxis
          dataKey={xKey}
          stroke={AXIS_COLOR}
          fontSize={10}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: string) => (typeof v === "string" ? v.slice(5) : String(v))}
          minTickGap={24}
        />
        <YAxis stroke={AXIS_COLOR} fontSize={10} tickLine={false} axisLine={false} width={44} tickFormatter={fmtAxis} />
        <Tooltip
          contentStyle={tooltipStyle}
          cursor={{ stroke: GRID_COLOR }}
          formatter={(v) => [`${v}${unit}`, dataKey] as [string, string]}
        />
        <Line
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function BarSeries({
  data,
  dataKey,
  color = "var(--color-strain)",
  height = 180,
  xKey = "date",
  unit = "",
}: {
  data: Datum[];
  dataKey: string;
  color?: string;
  height?: number;
  xKey?: string;
  unit?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={GRID_COLOR} vertical={false} />
        <XAxis
          dataKey={xKey}
          stroke={AXIS_COLOR}
          fontSize={10}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: string) => (typeof v === "string" ? v.slice(5) : String(v))}
          minTickGap={16}
        />
        <YAxis stroke={AXIS_COLOR} fontSize={10} tickLine={false} axisLine={false} width={44} tickFormatter={fmtAxis} />
        <Tooltip
          contentStyle={tooltipStyle}
          cursor={{ fill: "#1c1c1c" }}
          formatter={(v) => [`${v}${unit}`, dataKey] as [string, string]}
        />
        <Bar dataKey={dataKey} fill={color} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function StackedBars({
  data,
  keys,
  height = 220,
  xKey = "date",
}: {
  data: Datum[];
  keys: { key: string; color: string; label: string }[];
  height?: number;
  xKey?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={GRID_COLOR} vertical={false} />
        <XAxis
          dataKey={xKey}
          stroke={AXIS_COLOR}
          fontSize={10}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: string) => (typeof v === "string" ? v.slice(5) : String(v))}
          minTickGap={16}
        />
        <YAxis stroke={AXIS_COLOR} fontSize={10} tickLine={false} axisLine={false} width={44} tickFormatter={fmtAxis} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#1c1c1c" }} />
        {keys.map((k) => (
          <Bar key={k.key} dataKey={k.key} stackId="a" fill={k.color} name={k.label} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
