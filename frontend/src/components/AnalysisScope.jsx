import React from 'react'

export default function AnalysisScope({ analysis }) {
  if (!analysis) return null
  const format = value => Number(value || 0).toLocaleString()
  let message
  if (analysis.status === 'preview') {
    message = `Preview: first ${format(analysis.rows)} of ${format(analysis.total_rows)} rows. Charts will update as the remaining batches are analyzed. All parsed rows are retained.`
  } else if (analysis.status === 'processing') {
    message = `Charts include all ${format(analysis.processed_rows)} rows processed so far, of ${format(analysis.total_rows)}. Full analysis is continuing. All parsed rows are retained.`
  } else if (analysis.status === 'complete' && analysis.full_metrics) {
    message = `Full dataset analyzed: ${format(analysis.rows)} rows. Histograms, category counts, timelines, means, standard deviations, Pearson correlations and missing-value counts cover all rows. Boxplots, quantiles, outlier checks, numeric triage, Spearman, PCA and other advanced EDA views use a ${format(analysis.sample_rows)}-row sample drawn across the dataset.`
    if (analysis.pair_columns_limited) message += ` Pairwise calculations cover the first ${analysis.pair_column_limit} columns to keep memory use bounded.`
  } else if (analysis.sampled) {
    // Older API revisions still send the original sample-only response.
    message = `Charts and advanced metrics use the first ${format(analysis.rows)} of ${format(analysis.total_rows)} rows for faster loading. Total row and missing-value counts cover the full dataset. All parsed rows are retained.`
  }
  if (!message) return null
  return <p className="wr-analysis-sample" role="note">{message}</p>
}
