import React from 'react'
import { BarChart as ReBarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

export default function TopValuesChart({ data }) {
  const { values, column, total_unique } = data
  return (
    <div className="chart-card">
      <div className="chart-header">
        <span className="chart-col">{column}</span>
        <span className="chart-badge cat">categorical</span>
        <span className="chart-unique">{total_unique} unique</span>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <ReBarChart data={values} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            type="category" dataKey="value"
            tick={{ fontSize: 11 }} axisLine={false} tickLine={false}
            width={90}
            tickFormatter={v => v.length > 12 ? v.slice(0, 12) + '…' : v}
          />
          <Tooltip
            formatter={(v) => [v, 'count']}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
          />
          <Bar dataKey="count" fill="#7c3aed" radius={[0, 3, 3, 0]} />
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  )
}
