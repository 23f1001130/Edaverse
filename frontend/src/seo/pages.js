export const SITE_URL = 'https://edaverse.app'

export const home = {
  path: '/', title: 'No-Code EDA for CSV & Excel Data | edaverse',
  description: 'Explore CSV and Excel data without code. Profile missing values, visualize correlations, review cleaning suggestions, and export results with edaverse.',
}

export const featurePages = [
  {
    path: '/csv-data-analysis/', label: 'CSV data analysis',
    title: 'CSV Data Analysis Without Code | edaverse',
    description: 'Analyze CSV files without writing code. Explore column statistics, missing values, distributions, outliers, and correlations with edaverse.',
    heading: 'Understand your CSV data before your next decision.',
    intro: 'A spreadsheet export is only the start. edaverse turns CSV files into an exploratory data analysis workspace where you can inspect data quality, compare distributions, and investigate relationships without writing Python or SQL.',
    sections: [
      ['Start with a column-by-column profile', 'Upload a CSV file to see its rows, columns, detected data types, and missing values. Use this first pass to find incomplete fields and check whether numeric and categorical columns have been interpreted as expected. Review parser warnings before relying on the results.'],
      ['Look beyond averages', 'Distributions reveal skew and unusual values that a single average can hide. Compare numeric columns, inspect category frequencies, and use correlation heatmaps to look for relationships worth investigating. A correlation is a starting point for analysis; it does not establish cause and effect.'],
      ['Example: inspect a customer churn export', 'For a file with tenure, monthly charges, contract type, and churn, start by checking missing cells and data types. Then compare tenure and charges distributions and examine relationships among numeric fields. Treat the product preview as an illustration, and use the demo to explore a sample dataset before uploading your own.'],
      ['Move from exploration to a reusable result', 'Review suggested cleaning operations, apply the ones appropriate for your dataset, and continue into feature engineering. Export a cleaned dataset, notebook, or report so you can take the result into your next analysis.'],
    ],
    steps: ['Upload your CSV and review parsing warnings.', 'Inspect column quality, distributions, and correlations.', 'Review cleaning suggestions and export your results.'],
    faqs: [
      ['Do I need to write code to analyze a CSV?', 'No. edaverse provides a visual workspace for profiling, exploratory analysis, guided cleaning, and feature engineering. You can export a notebook if you want to continue working in code.'],
      ['Will every CSV be interpreted correctly automatically?', 'Files can contain unusual delimiters, encodings, or headers. Review the detected columns, preview, and parser warnings before continuing; check the source file if the interpretation is unexpected.'],
    ],
  },
  {
    path: '/excel-data-profiling/', label: 'Excel data profiling',
    title: 'Excel Data Profiling & Quality Checks | edaverse',
    description: 'Profile Excel data without code. Inspect column types, missing values, distributions, and correlations before cleaning or analyzing your dataset.',
    heading: 'Check your Excel data before building on it.',
    intro: 'Workbook data can look tidy while still containing missing fields, inconsistent types, and unusual values. edaverse helps students and analysts profile tabular Excel data before preparing a report or building a model.',
    sections: [
      ['Inspect the structure of your table', 'Upload a supported Excel file and review the parsed columns and inferred types. Confirm that the data preview matches the table you intended to analyze, particularly when the source workbook has title rows or formatting around the data.'],
      ['Find gaps and unusual values', 'Column-level profiles show missing values and summary statistics. Use distributions and outlier information to investigate entries that may need correction. An unusual value can be a real observation, so compare it with the source before removing it.'],
      ['Example: prepare a monthly sales table', 'Check that dates, amounts, and region labels have sensible types. Inspect missing amounts and unusually large values, then compare distributions before choosing cleaning operations. This workflow helps you decide which issues matter for a report instead of changing every flagged value automatically.'],
      ['Know what profiling can tell you', 'Data profiling describes the parsed dataset; it is not a full audit of workbook formulas, macros, or formatting. Confirm the imported data and keep your original workbook so that you can trace any changes back to their source.'],
    ],
    steps: ['Upload your Excel table and confirm the imported preview.', 'Review missing fields, data types, and statistical summaries.', 'Choose cleaning operations and export the prepared data.'],
    faqs: [
      ['Can I use edaverse instead of writing spreadsheet formulas?', 'You can use the visual workspace for supported profiling and cleaning tasks without writing formulas. It complements a spreadsheet workflow; review the imported data before using the analysis.'],
      ['Does data profiling validate every business rule?', 'No. Profiling highlights structural and statistical issues. You still need to check business rules, such as valid product codes or acceptable transaction ranges, using your knowledge of the dataset.'],
    ],
  },
  {
    path: '/automated-data-cleaning/', label: 'Automated data cleaning',
    title: 'Guided Data Cleaning for CSV & Excel | edaverse',
    description: 'Find data quality issues in CSV and Excel files. Review cleaning suggestions, prepare features, and export a cleaned dataset with edaverse.',
    heading: 'Clean messy data with a review at every step.',
    intro: 'Preparing data often takes longer than exploring it. edaverse brings profiling, cleaning suggestions, and feature engineering into one workflow so you can understand an issue before deciding how to fix it.',
    sections: [
      ['Profile before changing anything', 'Start with missing values, detected types, and distributions. A blank field may mean unknown, not applicable, or a collection error. Understanding that distinction helps you choose an appropriate treatment rather than applying the same rule to every column.'],
      ['Review suggested fixes', 'The cleaning workspace flags issues and offers supported operations for you to review. Apply changes that fit your analysis and check the results. Automated suggestions help you find candidates for cleanup; they cannot decide what is correct for every business context.'],
      ['Example: prepare data for a predictive model', 'For a customer dataset, examine incomplete numeric fields and inconsistent categories before engineering features. Decide how missing information should be represented, review unusual values against the source, and export the prepared data. When building a model, keep evaluation data separate and avoid using information that would not be available at prediction time.'],
      ['Keep a usable output', 'Export a cleaned file for another tool, a report for review, or a notebook for further work. Preserve your original source data and compare the output with the original so that you can explain the preparation choices you made.'],
    ],
    steps: ['Profile the original dataset and identify quality issues.', 'Review and apply suitable cleaning suggestions.', 'Inspect the result, engineer features, and export.'],
    faqs: [
      ['Does edaverse change data without my review?', 'The guided cleaning workflow lets you review suggestions before applying changes. Check each operation against your goals and keep a copy of your source data.'],
      ['Can I continue into feature engineering after cleaning?', 'Yes. The workspace includes feature engineering operations and export options so you can continue preparing the dataset after reviewing its quality.'],
    ],
  },
]

export const blogPosts = [
  {
    path: '/blog/analyze-csv-without-code/', label: 'Analyze CSV without code',
    title: 'How to Analyze a CSV File Without Writing Code | edaverse',
    description: 'Learn how to explore, profile, and clean CSV data without Python or SQL. A step-by-step guide using edaverse for no-code exploratory data analysis.',
    heading: 'How to analyze a CSV file without writing code',
    published: '2026-11-17',
    body: [
      ['The problem with raw CSV files', 'You exported a CSV from your CRM, survey tool, or database. Now what? Opening it in a spreadsheet shows rows and columns, but not the story: which columns have missing data, whether numeric fields contain outliers, or how variables relate to each other. Writing Python or R to answer these questions takes time — and assumes you know them.'],
      ['What exploratory data analysis actually means', 'Exploratory data analysis (EDA) is the first pass over a dataset. You check its shape, look at distributions, find missing values, spot outliers, and examine correlations. The goal is not to build a model — it is to understand what you have before deciding what to do with it.'],
      ['A no-code approach', 'Tools like edaverse let you do this visually. Upload a CSV file and get a column-by-column profile: data types, null counts, unique values, and summary statistics. Then look at distribution charts and a correlation heatmap without writing a line of code.'],
      ['Step 1: Upload and check the parse', 'Drag your file into edaverse or use the upload button. The parser detects delimiters, encodings, and data types automatically. Review the preview and any warnings — a date column interpreted as text, or a numeric column with commas, is worth catching early.'],
      ['Step 2: Profile and explore', 'The overview tab shows row count, column count, missing values, and duplicates. The distributions tab visualizes each numeric column. The correlations tab shows a heatmap of relationships. These three views answer most first-pass questions without any code.'],
      ['Step 3: Clean and export', 'If you find issues — missing values, inconsistent categories, outliers — the cleaning tab suggests fixes. Review each suggestion, apply the ones that fit, and export a cleaned CSV, an Excel file, or a Jupyter notebook for further work.'],
      ['When you do need code', 'No-code EDA covers the first 80% of data exploration. For custom statistical tests, domain-specific transformations, or machine learning pipelines, export a notebook and continue in Python. The point is not to avoid code forever — it is to skip the boilerplate.'],
    ],
  },
  {
    path: '/blog/data-cleaning-steps/', label: 'Data cleaning steps',
    title: '5 Data Cleaning Steps Every Dataset Needs | edaverse',
    description: 'A practical guide to the five data cleaning steps that catch the most common quality issues in CSV and Excel datasets.',
    heading: '5 data cleaning steps every dataset needs',
    published: '2026-11-17',
    body: [
      ['Why cleaning comes before analysis', 'A model trained on dirty data produces dirty predictions. A report built on inconsistent categories tells a misleading story. Data cleaning is not glamorous, but skipping it is the most common source of wrong conclusions in data work.'],
      ['Step 1: Check data types', 'A zip code stored as a number loses leading zeros. A date stored as text cannot be sorted chronologically. The first cleaning step is confirming that every column has the right type — and fixing the ones that do not.'],
      ['Step 2: Handle missing values', 'Not all missing values are the same. A blank cell might mean "unknown", "not applicable", or "data entry error". Decide the meaning before choosing a treatment: drop the row, fill with a default, or flag it for review.'],
      ['Step 3: Standardize categories', 'If your dataset has "USA", "US", "United States", and "united states" in the same column, any grouping or filtering will give wrong results. Standardize categorical values to a single canonical form.'],
      ['Step 4: Detect and handle outliers', 'An age of 999 or a transaction amount of -$50,000 is probably an error. But a genuinely large purchase is not. Look at outliers in context: compare them against the source data before removing them.'],
      ['Step 5: Remove duplicates', 'Duplicate rows inflate counts and skew averages. But not every duplicate is accidental — a customer who placed two identical orders on the same day might be real. Check whether the duplication is in the data or in the collection process.'],
      ['Automate what you can', 'Manual cleaning does not scale. Tools like edaverse automate the detection side — flagging missing values, type mismatches, and duplicates — while keeping you in the loop for decisions. Review suggestions, apply the ones that fit, and export.'],
    ],
  },
  {
    path: '/blog/what-is-eda/', label: 'What is EDA',
    title: 'What is Exploratory Data Analysis (EDA)? A Beginner\'s Guide | edaverse',
    description: 'Exploratory data analysis explained for beginners. Learn what EDA is, why it matters, and how to do it without writing code.',
    heading: 'What is exploratory data analysis?',
    published: '2026-11-17',
    body: [
      ['EDA in one sentence', 'Exploratory data analysis is the process of examining a dataset to understand its structure, quality, and patterns before doing anything else with it.'],
      ['Why EDA matters', 'Jumping straight to modeling or reporting without understanding your data is like navigating without a map. EDA reveals missing values that would break a model, skewed distributions that would bias an average, and correlations that suggest which variables matter.'],
      ['The four things EDA answers', 'Every EDA answers four questions: (1) What shape is the data — how many rows, columns, and what types? (2) What is missing or broken — nulls, duplicates, type errors? (3) What does each variable look like — distributions, outliers, common values? (4) How do variables relate — correlations, group differences, trends?'],
      ['EDA with code vs. without code', 'The traditional approach uses Python (pandas, matplotlib, seaborn) or R. This works well but requires programming knowledge and repetitive boilerplate. No-code tools like edaverse automate the common steps: upload a file, get a profile, explore distributions, and review correlations — all in a visual interface.'],
      ['When to use EDA', 'Before building a machine learning model. Before writing a report. Before making a business decision based on data. Before cleaning a dataset. Any time you receive data you have not seen before.'],
      ['A practical example', 'You receive a CSV of customer transactions. EDA tells you: 2% of rows have no transaction amount (needs investigation), the amount distribution is right-skewed (median is better than mean), and transaction count correlates with customer tenure (expected but worth confirming). Ten minutes of EDA saves hours of debugging later.'],
      ['Getting started', 'Try edaverse with the built-in demo dataset, or upload your own CSV or Excel file. The workspace walks you through profiling, distributions, correlations, and cleaning without requiring any code.'],
    ],
  },
]

export const homeFaqs = [
  ['What is exploratory data analysis (EDA)?', 'EDA is the first investigation of a dataset: checking its structure, missing values, distributions, and relationships. It helps you decide which questions to ask and which preparation steps to take before deeper analysis.'],
  ['What can I do with edaverse?', 'Upload CSV or Excel data, inspect column profiles and visualizations, review cleaning suggestions, engineer features, and export a cleaned file, notebook, or report.'],
  ['Do I need a dataset to try it?', 'No. Choose View demo to explore a sample dataset before uploading your own. Sign in when you are ready to use your own data.'],
  ['Are uploaded files processed only in my browser?', 'No. The hosted application sends uploads to its backend for processing. Use the demo to explore the product before deciding which data to upload. The open-source repository also includes self-hosting instructions.'],
]

export function normalizePath(path) {
  return path === '/' ? '/' : `${path.replace(/\/+$/, '')}/`
}

export const blogIndex = {
  path: '/blog/', title: 'Blog — Data Analysis Guides | edaverse',
  description: 'Guides on exploratory data analysis, data cleaning, and working with CSV and Excel data without code.',
}

export function findPage(path) {
  const normalized = normalizePath(path)
  if (normalized === '/') return home
  if (normalized === '/blog/') return blogIndex
  return featurePages.find(page => page.path === normalized) || blogPosts.find(page => page.path === normalized)
}
