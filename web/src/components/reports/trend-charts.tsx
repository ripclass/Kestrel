"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const data = [
  { month: "Jan", alerts: 74 },
  { month: "Feb", alerts: 92 },
  { month: "Mar", alerts: 108 },
  { month: "Apr", alerts: 126 },
];

export function TrendCharts() {
  return (
    <div className="h-80 rounded-2xl border border-border/70 bg-card p-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <XAxis dataKey="month" />
          <YAxis />
          <Tooltip />
          <Area type="monotone" dataKey="alerts" stroke="#58a6a6" fill="#58a6a633" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
