# Workspace appearance and usability

The light-mode header and sidebars stayed dark because they used fixed translucent dark backgrounds. Observation warnings, chart tooltips, and chart axes also included fixed colours, causing unreadable text after switching themes.

This change replaces the workspace surfaces with opaque theme colours and shares theme-aware chart styles across distributions, correlations, and target analysis. Warning text, heatmap text, success buttons, secondary text, and focus indicators adapt to both themes. The browser's native controls use the selected colour scheme. A small initialization script applies the saved theme before the page is painted, including on public pages and reloads. Reduced-motion preferences are respected.

The column list can be hidden to give charts more room. Column searches show the matching count, explain an empty result, and offer a reset. Analysis tabs expose the current selection and support arrow keys, Home, and End. Analysis is disabled until a dataset exists. A failed analysis has a retry action that reuses the current dataset. Target charts can shrink to the available width.

Validation includes the production build, static SEO checks, and 27 frontend tests. New tests cover theme persistence and invalid saved values, no-data navigation, empty-search recovery, hiding columns without losing a filter, column-to-distribution navigation, keyboard tabs, and retry after a network failure. Hosted visual checks should cover the workspace header, icon and column sidebars, observations, charts, and saved theme after reload in both modes.

Next larger product improvements worth considering:

1. A searchable, filterable row preview. The current overview focuses on summaries; analysts also need to inspect the records behind an issue.
2. A before-and-after preview of selected cleaning operations. The current cleaning result summarizes row and column counts after applying changes; a preview would help users choose an operation before committing it.
3. Export progress and clear error feedback. CSV and report actions currently open a URL directly, whereas notebook export reports failures. A consistent download flow would make export failures easier to understand.

These larger changes are recommendations and are not included in this appearance and navigation update.
