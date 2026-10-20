# Edaverse SEO implementation

Prepared 20 October 2026. Audience assumption: English-speaking students and data analysts worldwide. The search terms below reflect product fit; no search-volume or ranking claims have been made.

## Implemented locally

| Page | Main topic | Supporting intent |
| --- | --- | --- |
| `/` | No-code exploratory data analysis | Automated EDA, CSV and Excel analysis |
| `/csv-data-analysis/` | CSV data analysis without code | Column statistics, distributions, correlations |
| `/excel-data-profiling/` | Excel data profiling | Missing values, data quality checks |
| `/automated-data-cleaning/` | Guided data cleaning | CSV cleanup, Excel cleanup, preparation |

- Replaced the slogan-only homepage heading with a descriptive heading and explained the analysis workflow.
- Added substantial feature guides, examples, FAQs, and ordinary HTML links between public pages.
- Generated all four public pages as static HTML using the same React components used in the browser. This includes content and metadata before JavaScript runs.
- Added unique titles, descriptions, canonical URLs, and social tags per page. Preserved the favicon and updated the social image to show the current homepage.
- Added WebSite and WebPage structured data, SoftwareApplication details on the homepage, and breadcrumbs on feature pages. No invented reviews, ratings, or FAQ rich-result promises.
- Generated the sitemap from the public page list at build time. Preserved the existing robots policy, including the GPTBot restriction.
- Added a real Cloudflare Pages 404 page and explicit authentication callback rewrites, with noindex headers for callbacks.
- Removed the inaccurate browser-only processing claim; the application sends uploads to a backend. The homepage now explains this and links to self-hosting instructions.
- Deferred loading workspace and authentication screens until needed.
- Added build validation to frontend CI so missing content or broken metadata can fail a pull request.

## Verification

The production build and automated SEO checks passed for four pages. Checks parse generated HTML without executing JavaScript and validate substantial content, one H1, unique titles and descriptions, canonicals, social URLs, parseable structured data, local assets, internal links, sitemap membership, and noindex on the error page.

The frontend suite passed: 20 tests across four files. New coverage includes homepage content before authentication loads, existing demo navigation, feature-page demo and sign-in entry, opening the workspace after sign-in, SSO callback URLs with and without a trailing slash, and hydration of the homepage and all three guides without replacing their headings.

Desktop browser inspection confirmed the updated homepage and navigation to the CSV guide. Screenshots are in `doc/seo/`. Phone-width checks at 390 pixels confirmed that the homepage and CSV guide have no horizontal overflow, and the homepage layout was visually inspected. The Cloudflare preview loaded the real authentication form. HTTP checks confirmed the four public pages, the four-URL sitemap, and a real 404 for missing pages. A trailing-slash callback issue discovered during preview checks was corrected with an explicit rewrite and a dedicated noindex callback document. Completing a real sign-in and uploading private data were not part of the smoke test. No performance score, rankings, or Google rich-result eligibility has been claimed.

## Publish the changes

Changes are on `codex/edaverse-seo`. GitHub access was confirmed after checking outside the restricted network environment; the saved login is valid.

For Cloudflare Pages, keep `frontend` as the root directory, `npm run build` as the build command, and `dist` as the output directory. The build now includes prerendering and validation; do not replace it with `vite build` alone. Keep the existing production `VITE_CLERK_PUBLISHABLE_KEY`, `VITE_APP_URL`, `VITE_API_URL`, and optional Sentry settings. No new runtime secrets or services are required. Node 24 matches the repository's CI configuration.

After deploying the preview, check the home page, each feature page, demo entry, sign-in, sign-out, and the Google SSO callback. Check a deliberately nonexistent URL returns HTTP 404 and the callback still loads the app. Cloudflare's routing behavior cannot be fully tested by Vite's preview server. Then merge and check the production deployment.

## Google Search Console

The owner verified the Domain property through Cloudflare. On 20 October 2026, the connected browser confirmed access to the verified property. The live sitemap at `https://edaverse.app/sitemap.xml` was submitted successfully; Search Console reported Success and one discovered page. URL Inspection confirmed that the homepage is already indexed and served over HTTPS. The initial performance reports are still processing. The updated sitemap will include four public pages after deployment. No additional DNS settings were changed during submission.

1. Sign in to [Google Search Console](https://search.google.com/search-console). Check whether `edaverse.app` is already a property in the property selector.
2. If absent, add the Domain property `edaverse.app`. Google will provide the exact DNS TXT verification value. Add that value through the domain's DNS provider and complete verification. Do not guess or reuse another domain's token.
3. After the changes are live, submit `https://edaverse.app/sitemap.xml` in Sitemaps. Inspect the homepage and each feature URL with URL Inspection, run a live test, and request indexing where available.
4. Check Pages for crawl errors, duplicate/canonical problems, or blocked URLs. Check Core Web Vitals when sufficient real-user data is available.
5. Record the first complete 28-day period as a baseline: organic clicks, impressions, click-through rate, search queries, indexed public pages, countries, and devices. Compare subsequent complete periods; separate branded `edaverse` queries from non-branded discovery queries.

Google decides when to crawl and index pages. A sitemap and valid structured data do not guarantee indexing, rankings, or enhanced search features.

## Content and measurement follow-through

The first four pages are complete. Use actual Search Console queries to prioritize further work:

| Priority | Next useful asset | What it should contain |
| --- | --- | --- |
| 1 | A worked EDA walkthrough | A public sample CSV, screenshots from a real run, explanations of missing values and correlations, and a downloadable result |
| 2 | A data quality checklist | Concrete checks for types, missingness, duplicates, unusual values, and business rules; link to profiling and cleaning guides |
| 3 | A feature engineering tutorial | A reproducible example with supported operations, explanations of each choice, and a link to the cleaning workflow |

Create each new guide around a distinct user task and add it to the shared page registry so that its metadata and sitemap entry are generated together. Avoid near-identical keyword pages.

The public GitHub repository initially had no About description, website, or topics. Suggested description: “Open-source, no-code exploratory data analysis for CSV and Excel: profiling, guided cleaning, feature engineering, and export.” Suggested website: `https://edaverse.app/`. Suggested topics: `exploratory-data-analysis`, `data-cleaning`, `data-profiling`, `csv`, `excel`, `react`, `fastapi`.

Share a useful sample analysis with relevant data communities and documentation resources when ready. No outreach, directory submissions, or paid links were sent or purchased. Search Console supplies organic-search measurement without adding a tracking script. Product conversion tracking can be planned after the owner selects an analytics service and privacy settings.

## References

- [Google: JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- [Google: Build and submit a sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Google: Software application structured data](https://developers.google.com/search/docs/appearance/structured-data/software-app)
- [Cloudflare Pages: serving pages and 404 behavior](https://developers.cloudflare.com/pages/configuration/serving-pages/)
- [Cloudflare Pages: redirects](https://developers.cloudflare.com/pages/configuration/redirects/)
