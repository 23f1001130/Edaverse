import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

export default function HistogramChart({ data }) {
  const { bins, stats, column } = data
  return (
    <div className="chart-card">
      <div className="chart-header">
        <span className="chart-col">{column}</span>
        <span className="chart-badge numeric">numeric</span>
      </div>
      <div className="chart-stats-row">
        <span>min <strong>{stats.min}</strong></span>
        <span>mean <strong>{stats.mean}</strong></span>
        <span>median <strong>{stats.median}</strong></span>
        <span>max <strong>{stats.max}</strong></span>
        <span>std <strong>{stats.std}</strong></span>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={bins} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="range" tick={false} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(v) => [v, 'count']}
            labelFormatter={(l) => l}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
          />
          <Bar dataKey="count" fill="#2563eb" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
