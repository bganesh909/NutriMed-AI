"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { format } from "date-fns";
import type { ProgressLog } from "@/types";

interface ProgressChartProps {
  data: ProgressLog[];
}

export function ProgressChart({ data }: ProgressChartProps) {
  const chartData = data.map((log) => ({
    date: format(new Date(log.date), "MMM dd"),
    weight: log.weight,
    body_fat: log.body_fat,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart
        data={chartData}
        margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="date"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          axisLine={{ stroke: "#334155" }}
          tickLine={{ stroke: "#334155" }}
        />
        <YAxis
          yAxisId="weight"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          axisLine={{ stroke: "#334155" }}
          tickLine={{ stroke: "#334155" }}
        />
        <YAxis
          yAxisId="bf"
          orientation="right"
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
        />
        <Legend
          wrapperStyle={{ color: "#94a3b8" }}
        />
        <Line
          yAxisId="weight"
          type="monotone"
          dataKey="weight"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={{ fill: "#3b82f6", r: 4 }}
          name="Weight (kg)"
        />
        <Line
          yAxisId="bf"
          type="monotone"
          dataKey="body_fat"
          stroke="#10b981"
          strokeWidth={2}
          dot={{ fill: "#10b981", r: 4 }}
          name="Body Fat (%)"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
