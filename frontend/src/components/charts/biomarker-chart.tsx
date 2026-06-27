"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { Biomarker } from "@/types";

const statusBarColors: Record<string, string> = {
  Normal: "#10b981",
  Low: "#f59e0b",
  High: "#f59e0b",
  Critical: "#ef4444",
};

interface BiomarkerChartProps {
  biomarkers: Biomarker[];
}

export function BiomarkerChart({ biomarkers }: BiomarkerChartProps) {
  const data = biomarkers.map((b) => ({
    name: b.name.length > 12 ? b.name.substring(0, 12) + "..." : b.name,
    fullName: b.name,
    value: b.value,
    status: b.status,
    unit: b.unit,
    min: b.reference_min,
    max: b.reference_max,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="name"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          axisLine={{ stroke: "#334155" }}
          tickLine={{ stroke: "#334155" }}
        />
        <YAxis
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          axisLine={{ stroke: "#334155" }}
          tickLine={{ stroke: "#334155" }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#0f172a",
            border: "1px solid #1e293b",
            borderRadius: "8px",
            color: "#e2e8f0",
          }}
          formatter={(value, _name, props) => {
            const p = (props as { payload?: { fullName?: string; unit?: string; status?: string } }).payload;
            return [
              `${value} ${p?.unit ?? ""} (${p?.status ?? ""})`,
              p?.fullName ?? "",
            ];
          }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={statusBarColors[entry.status] || "#3b82f6"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
