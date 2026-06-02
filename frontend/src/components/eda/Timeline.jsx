import React from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

export default function Timeline({ data }) {
  const { column, timeline, min, max } = data
  return (
    <div className="chart-card">
      <div className="chart-header">
        <span className="chart-col">{column}</span>
        <span className="chart-badge" style={{ background: '#fff7ed', color: '#c2410c' }}>timeline</span>
      </div>
      <div className="chart-stats-row">
        <span>from <strong>{min?.slice(0,10)}</strong></span>
        <span>to <strong>{max?.slice(0,10)}</strong></span>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={timeline} margin={{ top: 4, right: 12, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="period" tick={{ fontSize: 9 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }} />
          <Line type="monotone" dataKey="count" stroke="#c2410c" strokeWidth={2} dot={{ r: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
