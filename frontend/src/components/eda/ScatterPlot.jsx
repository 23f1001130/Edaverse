import React from 'react'
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

export default function ScatterPlot({ data }) {
  const { x_col, y_col, correlation, points } = data
  const color = correlation > 0 ? '#2563eb' : '#dc2626'
  return (
    <div className="chart-card">
      <div className="chart-header">
        <span className="chart-col">{x_col} × {y_col}</span>
        <span className="chart-badge numeric">r = {correlation}</span>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <ScatterChart margin={{ top: 8, right: 12, left: -16, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis type="number" dataKey="x" name={x_col} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis type="number" dataKey="y" name={y_col} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
          />
          <Scatter data={points} fill={color} fillOpacity={0.55} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
