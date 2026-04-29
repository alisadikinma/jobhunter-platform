"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useActivityTimeline } from "@/hooks/useStats";

const DAYS = 14;

export function WeeklyChart() {
  const { data, isLoading, error } = useActivityTimeline(DAYS);

  if (isLoading) {
    return (
      <div className="card flex h-64 items-center justify-center text-sm text-neutral-500">
        Loading timeline…
      </div>
    );
  }
  if (error) {
    return (
      <div className="card flex h-64 items-center justify-center text-sm text-red-400">
        Failed to load activity timeline.
      </div>
    );
  }

  const days = data?.days ?? [];
  const isEmpty = days.every((d) => d.count === 0);

  const formatted = days.map((d) => {
    const dt = new Date(d.date);
    return {
      ...d,
      label: dt.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    };
  });

  return (
    <div className="card">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-medium text-neutral-300">
          Activity (last {DAYS} days)
        </h2>
        {isEmpty && (
          <span className="text-xs text-neutral-500">
            No activity yet — start an application to populate.
          </span>
        )}
      </div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={formatted} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
            <CartesianGrid stroke="#262626" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              stroke="#737373"
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              stroke="#737373"
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              cursor={{ fill: "rgba(59,130,246,0.08)" }}
              contentStyle={{
                background: "#0a0a0a",
                border: "1px solid #262626",
                borderRadius: 6,
                fontSize: 12,
              }}
              labelStyle={{ color: "#a3a3a3" }}
            />
            <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
