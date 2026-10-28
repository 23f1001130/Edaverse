# Large dataset ingestion

The hosted upload limit remains 100 MiB. A network error alone does not establish
whether a request timed out, the API restarted, or the connection failed; inspect
Render logs for the failed request to establish the exact cause.

## Changes

- Run ingestion in a synchronous FastAPI worker, leaving the event loop available
  for health checks and other requests. Admit one ingestion per process; overlapping
  uploads get a clear 503 rather than expanding several frames in memory.
- Read the spooled upload directly. CSV/TSV/text and XLSX files at least 10 MiB are
  normalized to a temporary UTF-8 CSV without building a full dataframe. CSV uses
  10,000-row chunks; XLSX imports the first worksheet through the configured reader.
- Preserve every parsed row in the active stored artifact and upload that artifact
  to R2 through the existing persistence path. The previous large-CSV path could
  persist only its 10,000-row schema sample.
- Infer types and detailed statistics from the first 10,000 rows. Scan the full
  normalized file for exact row/missing counts and numeric min/max/mean. Reject
  malformed large CSV records with an actionable error rather than silently
  discarding bad lines. Report when a workbook contains additional worksheets.
- Bound interactive EDA charts to the first 10,000 rows. Both streaming and regular
  EDA responses include analysis scope. UI and HTML reports disclose this; row and
  missing-value counts still use the full dataset schema.
- Show actual upload progress, elapsed time, and a distinct server-processing
  message after transfer. Remove simulated profiling steps. Do not automatically
  resend a failed upload; show a clear connection-error message.

## Verification

- Backend: 69 tests, including CSV tail preservation, full-file missing counts,
  Excel iteration, header reparsing, malformed-file cleanup, upload limit, and
  responsive config requests during ingestion, and restoration of promoted data.
- Frontend: 37 tests; production build and all four prerendered SEO checks pass.
- Local integration benchmark using UCI's public Online Retail II workbook:
  45,622,278 bytes (43.51 MiB), first worksheet 525,461 rows. Ingestion 26.57 s,
  chart EDA 0.37 s, peak process working set 150.03 MiB. These are local measurements,
  with local persistence; hosted CPU, network, R2, and cold starts add latency.

## Remaining limits

XLSX iteration still loads workbook metadata/shared strings. Very wide sheets or
huge shared-string tables can exceed a small server's resources. Large legacy XLS,
JSON, and Parquet parsing and full-data cleaning/modeling operations keep their
existing behavior; this is not a guarantee that every 100 MiB file fits in memory.
Only the first worksheet is imported, matching the previous Excel behavior.
Sampled charts are exploratory and may omit rare or late-occurring values.

The deployment manifest uses Render's free plan. Free-instance cold starts and
limited compute remain hosting constraints; upgrading compute requires a separate
hosting decision. No hosting plan, billing, or security settings are changed here.

## Native Excel reader on Azure

The Docker image sets `XLSX_READER=calamine` and pins python-calamine 0.9.0.
This accelerates XLSX files at least 10 MiB on the 1 vCPU / 2 GiB Azure instance.
Non-container deployments default to the existing openpyxl reader, retaining the
lower-memory behavior on Render. Set `XLSX_READER=openpyxl` to roll back without
changing the image. Small files and other formats retain their existing paths.

Calamine materializes the worksheet, so native reading is limited to compressed
files up to 64 MiB, expanded archives up to 384 MiB and up to 8 million cells.
Larger files use openpyxl. These guards are not a guarantee that every workbook
fits within 2 GiB. Ingestion still admits one upload per process.

An XML preflight preserves the worksheet dimensions and selects the first actual
worksheet, including when chart sheets precede it. Workbooks with Excel error
cells use openpyxl because Calamine converts those cells to empty strings.
Native parse failures restart the output from scratch through openpyxl. Leading
columns, header selection, dates, text IDs and trailing formatted cells are
covered by parity tests. `profile.reader` reports the actual large-XLSX reader.

A fresh local comparison on the same public 45,622,278-byte UCI Online Retail II
workbook measured 20.90 s / 129.11 MiB peak for openpyxl and 14.26 s / 417.53 MiB
for Calamine, including normalization, validation and profiling. Both produced
the same complete CSV SHA-256
`224f1c7548bc713088cf56ddf7c087ccdc6c07d6c8c3d2e58deb322a414c31b4`
and identical schema hashes across 525,461 rows / 8 columns. These local numbers
exclude network transfer and cloud persistence; hosted improvement must be measured
after the Azure revision is updated. All 75 backend tests pass locally; the image
workflow also checks native Excel ingestion inside the built Linux container.
