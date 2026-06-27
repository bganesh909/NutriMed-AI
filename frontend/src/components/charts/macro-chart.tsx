"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";

interface MacroChartProps {
  protein: number;
  carbs: number;
  fat: number;
}

const COLORS = ["#3b82f6", "#f59e0b", "#10b981"];

export function MacroChart({ protein, carbs, fat }: MacroChartProps) {
  const data = [
    { name: "Protein", value: protein, unit: "g" },
    { name: "Carbs", value: carbs, unit: "g" },
    { name: "Fat", value: fat, unit: "g" },
  ];

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={4}
          dataKey="value"
          strokeWidth={0}
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: "#0f172a",
            border: "1px solid #1e293b",
            borderRadius: "8px",
            color: "#e2e8f0",
          }}
          formatter={(value, name) => [`${value}g`, String(name)]}
        />
        <Legend
          formatter={(value) => (
            <span style={{ color: "#94a3b8" }}>{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
