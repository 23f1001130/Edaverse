# Progressive full-data charts

Large datasets now produce a quick 10,000-row preview, followed by cumulative
results as the remaining rows are scanned in 10,000-row batches. The final event
is marked complete only after every saved row has been processed and the actual
row count matches metadata. An interrupted stream retains its preview in the UI
and offers retry without uploading again. Small datasets complete directly.

## Accuracy and scope

| Result | Final coverage |
| --- | --- |
| Numeric histograms, min/max/mean/std/skewness | Every finite numeric value |
| Category counts, distinct category counts and top categories | All non-null category values, with disk-backed counts |
| Monthly timelines | All parseable dates, normalized to UTC |
| Pearson correlations | All pairwise-complete finite numeric rows, up to 40 numeric columns |
| Missing counts | All rows and columns |
| Missingness co-occurrence | All rows, first 40 dataset columns |
| Numeric triage mean/std/skewness and null rates | All rows; its unique/outlier counts remain sampled |
| Median/quartiles, boxplots, outlier checks, Spearman, PCA, scatter points and pivot heatmap | A deterministic uniform reservoir of up to 10,000 rows across the dataset; individual visualizations may display fewer points |
| Automated observations | Full-data missing/skew/correlation summaries; sampled uniqueness/outlier checks are qualified in their text |

The sampled views are labelled in the workspace and exported HTML report. Numeric
distribution details specifically distinguish sampled quantiles/boxplots from
full-data histogram counts and moments. Category bars show the top 10; the API
also reports the total count outside those bars. Identifier-like text columns
remain excluded from distribution charts.

During processing, every chart update is cumulative, not a chart of just the most
recent batch. Histogram edges initially use metadata ranges. Values outside those
ranges appear in explicit underflow/overflow buckets while processing. If metadata
ranges are missing, rounded or stale, a second bounded scan builds final histogram
bins from the actual data range. No batch averages or correlations are averaged
together. Pearson uses translated pairwise sufficient statistics; numeric moments
use stable parallel-merge formulas.

## Storage and concurrency

CSV reads preserve text values and explicitly coerce numeric columns. Parquet uses
Arrow record batches. Category counts use a temporary SQLite database with a small
page cache, keeping high-cardinality strings off the Python heap. Temporary files
are closed and removed when the stream finishes, fails or is cancelled. A single
process-wide analysis slot serializes large scans; duplicate requests reuse the
first completed summary instead of repeating the work.

Completed JSON summaries are cached locally and in the existing private R2 bucket.
Cache keys include the algorithm version, dataset/owner identity, data revision,
active format and analysis limits. Uploads receive a revision UUID; promoting
cleaned or engineered data, or restoring original data, creates a new revision.
Legacy records use their schema/shape/workflow/operation metadata as a version.
No credentials or new cloud services are added.

Local caches use an `.eda-cache` suffix, separate from dataset metadata, and have
a combined 128 MiB limit. Each cached result is at most 8 MiB. Cache writes are
atomic and optional; R2 cache operations use short network timeouts and limited
retries. A cold instance can restore a completed summary without downloading the
whole source dataset. Deleting a dataset removes its R2 prefix, including caches.

All analysis/report endpoints validate the request's dataset ownership before
computing or reading caches. The report download uses authenticated fetch. These
checks also cover target analysis, model importance and before/after comparison.

## Stream contract

`GET /api/datasets/{id}/eda/stream` emits SSE events with `stage`, `label`,
`progress`, and optional `data`:

- `loading`: checking cache/loading preview.
- `preview`: immediately usable initial EDA with `analysis.status=preview`.
- `queued`: preview remains visible while the scan slot is occupied.
- `batch`: cumulative chart data, `processed_rows`, `total_rows`, and status processing.
- `finalizing`: optional histogram range validation/second pass.
- `complete`: full-data summaries plus explicit sampled-metric coverage.
- `error`: the client keeps existing partial results, without declaring completion.

The regular `/eda` endpoint and report share the same engine/cache. Older clients
still receive a final `complete` event; newer clients also render partial events.
Newer clients retain a legacy sample-only scope label against an older API revision.

## Validation

Local Windows measurement using the public UCI Online Retail II first worksheet:
525,461 rows / 8 columns. Preview 0.297 s; complete summary 7.440 s; cached reopen
0.0137 s; peak process working set 119.23 MiB; cached JSON 39,238 bytes. Five
intermediate updates were emitted. This excludes upload, source download, cloud
cache network time and cloud CPU differences. It is not an Azure latency promise.

Tests cover CSV and Parquet, late-occurring categories and numeric shifts, exact
histogram totals, full-data moments, pairwise-missing correlations, missing-value
co-occurrence, full timelines, large numeric offsets, local/R2 cache reuse,
revision invalidation, cancellation/timeout cleanup, duplicate-request reuse,
authenticated HTTP streaming, owner isolation, and visible preview/interruption UI.
The Linux image smoke test also exercises upload → preview → full tail counts →
cached reopen through HTTP.

## Remaining production work

Keep maximum replicas at 1. The semaphore is per process, not a distributed job
queue. The scan is tied to the HTTP stream: closing a tab can cancel it, and retry
starts a fresh scan unless a completed cache already exists. Schema/type inference
is still sampled during large-file ingestion. Very wide data, extreme numeric
values, legacy formats, disk limits and long-running requests still need limits
and capacity testing. Cleaning, feature engineering, target/model analysis and
report comparisons retain their existing full-frame operations. This release does
not claim that every workflow now operates in bounded memory.

Priorities for the next releases:

1. Durable ingestion/analysis jobs with persisted status, cancellation, checkpoints,
   retries and idempotency. Continue after browser disconnects and service restarts.
   Return a job ID promptly and expose progress independently of the SSE connection.
2. Normalize large imports into typed Parquet row groups in the worker; key summaries
   by dataset revision and filter state. Preserve an exportable original artifact.
   Validate types/IDs/dates before conversion. Extend batching to cleaning, target
   analysis and report generation before raising row or concurrency limits.
3. Add date/category/range filters, saved analysis views, worksheet selection and
   column-type overrides. Show which dataset revision, filter and coverage an export
   represents. These provide practical value beyond adding more chart types.
4. Measure upload, parsing, storage and analysis separately, with request/job IDs,
   latency/error dashboards, memory/disk alerts and budget alerts. Verify restore
   procedures, retention/deletion, tenant isolation and rollback in staging before
   increasing traffic. Existing request IDs/Sentry hooks provide a starting point.

References:
- [Azure asynchronous request/reply pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply)
- [Arrow/Parquet I/O](https://arrow.apache.org/docs/python/parquet/parquet.html)
- [Azure Container Apps observability](https://learn.microsoft.com/en-us/azure/container-apps/observability)
