import json


def _q(value: str) -> str:
    return repr(value)


def _title_from_id(op_id: str) -> str:
    return op_id.replace("::", " / ").replace("_", " ")


def _cleaning_code(fix_id: str) -> str | None:
    if fix_id == "drop_duplicates":
        return (
            "before_rows = len(df)\n"
            "df = df.drop_duplicates().reset_index(drop=True)\n"
            "print(f'Removed {before_rows - len(df)} duplicate rows')\n"
        )

    if "::" not in fix_id:
        return None

    action, col = fix_id.split("::", 1)
    col_q = _q(col)

    if action == "drop_column":
        return (
            f"col = {col_q}\n"
            "if col in df.columns:\n"
            "    df = df.drop(columns=[col])\n"
            "    print(f'Dropped column: {col}')\n"
            "else:\n"
            "    print(f'Skipped missing column: {col}')\n"
        )

    if action == "fill_median":
        return (
            f"col = {col_q}\n"
            "if col in df.columns:\n"
            "    numeric = pd.to_numeric(df[col], errors='coerce').replace([np.inf, -np.inf], np.nan)\n"
            "    median_value = numeric.median()\n"
            "    before_nulls = int(numeric.isna().sum())\n"
            "    df[col] = numeric.fillna(median_value)\n"
            "    print(f'Filled {before_nulls} values in {col} with median={median_value:.4g}')\n"
        )

    if action == "knn_impute":
        return (
            f"col = {col_q}\n"
            "if col in df.columns:\n"
            "    before_nulls = int(df[col].isna().sum())\n"
            "    imputed, filled = knn_fill_numeric(df, col, k=5)\n"
            "    df[col] = imputed\n"
            "    print(f'KNN-imputed {filled} of {before_nulls} missing values in {col}')\n"
        )

    if action == "fill_unknown":
        return (
            f"col = {col_q}\n"
            "if col in df.columns:\n"
            "    before_nulls = int(df[col].isna().sum())\n"
            "    df[col] = df[col].fillna('Unknown')\n"
            "    print(f'Filled {before_nulls} values in {col} with Unknown')\n"
        )

    if action in ("trim", "trim_whitespace"):
        return (
            f"col = {col_q}\n"
            "if col in df.columns:\n"
            "    before = df[col].copy()\n"
            "    df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)\n"
            "    changed = int((before != df[col]).fillna(False).sum())\n"
            "    print(f'Trimmed whitespace in {changed} rows of {col}')\n"
        )

    if action == "fix_string_nulls":
        return (
            f"col = {col_q}\n"
            "if col in df.columns:\n"
            "    before_nulls = int(df[col].isna().sum())\n"
            "    df[col] = df[col].apply(\n"
            "        lambda x: np.nan if isinstance(x, str) and x.strip().lower() in STRING_NULLS else x\n"
            "    )\n"
            "    converted = int(df[col].isna().sum()) - before_nulls\n"
            "    numeric = pd.to_numeric(df[col], errors='coerce').replace([np.inf, -np.inf], np.nan)\n"
            "    if numeric.notna().sum() >= max(1, df[col].notna().sum() * 0.8):\n"
            "        df[col] = numeric.fillna(numeric.median())\n"
            "        fill_note = 'median'\n"
            "    else:\n"
            "        df[col] = df[col].fillna('Unknown')\n"
            "        fill_note = 'Unknown'\n"
            "    print(f'Converted {converted} string-null values in {col} and filled with {fill_note}')\n"
        )

    if action == "cap_outliers":
        return (
            f"col = {col_q}\n"
            "if col in df.columns:\n"
            "    numeric = pd.to_numeric(df[col], errors='coerce').replace([np.inf, -np.inf], np.nan)\n"
            "    q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)\n"
            "    iqr = q3 - q1\n"
            "    if iqr > 0:\n"
            "        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr\n"
            "        core = numeric[(numeric >= lower) & (numeric <= upper)].dropna()\n"
            "        if len(core) >= 4 and len(core) < numeric.dropna().shape[0]:\n"
            "            q1, q3 = core.quantile(0.25), core.quantile(0.75)\n"
            "            iqr = q3 - q1\n"
            "            if iqr > 0:\n"
            "                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr\n"
            "        capped = int(((numeric < lower) | (numeric > upper)).sum())\n"
            "        df[col] = numeric.clip(lower=lower, upper=upper)\n"
            "        print(f'Capped {capped} outliers in {col} to [{lower:.4g}, {upper:.4g}]')\n"
        )

    return None


def _feature_code(op_id: str) -> str | None:
    parts = op_id.split("::")
    op = parts[0]

    if op in ("drop_redundant", "drop_low_variance") and len(parts) >= 2:
        col_q = _q(parts[1])
        return (
            f"col = {col_q}\n"
            "if col in df.columns:\n"
            "    df = df.drop(columns=[col])\n"
            "    print(f'Dropped feature column: {col}')\n"
        )

    if op == "missing_indicator" and len(parts) >= 2:
        col_q = _q(parts[1])
        return (
            f"col = {col_q}\n"
            "new_col = f'{col}__missing'\n"
            "if col in df.columns and new_col not in df.columns:\n"
            "    df[new_col] = df[col].isna().astype(int)\n"
            "    print(f'Created {new_col}')\n"
        )

    if op == "transform" and len(parts) >= 3:
        col_q, transform_q = _q(parts[1]), _q(parts[2])
        return (
            f"col = {col_q}\n"
            f"transform = {transform_q}\n"
            "new_col = f'{col}__{transform}'\n"
            "if col in df.columns and new_col not in df.columns:\n"
            "    s = pd.to_numeric(df[col], errors='coerce').replace([np.inf, -np.inf], np.nan)\n"
            "    if transform in ('log', 'log_shift'):\n"
            "        shift = max(0, 1 - s.min())\n"
            "        df[new_col] = np.log(s + shift)\n"
            "    elif transform == 'log1p':\n"
            "        shift = -s.min() if (s <= -1).any() else 0\n"
            "        df[new_col] = np.log1p(s + shift)\n"
            "    elif transform == 'sqrt':\n"
            "        df[new_col] = np.sqrt(s.clip(lower=0))\n"
            "    elif transform == 'boxcox':\n"
            "        from scipy.stats import boxcox\n"
            "        shift = max(0, 1 - s.dropna().min())\n"
            "        vals, lam = boxcox(s.dropna() + shift)\n"
            "        df[new_col] = np.nan\n"
            "        df.loc[s.notna(), new_col] = vals\n"
            "        print(f'Box-Cox lambda for {col}: {lam:.4g}')\n"
            "    print(f'Created {new_col}')\n"
        )

    if op == "scale" and len(parts) >= 3:
        col_q, method_q = _q(parts[1]), _q(parts[2])
        return (
            f"col = {col_q}\n"
            f"method = {method_q}\n"
            "new_col = f'{col}__scaled'\n"
            "if col in df.columns and new_col not in df.columns:\n"
            "    s = pd.to_numeric(df[col], errors='coerce').replace([np.inf, -np.inf], np.nan)\n"
            "    if method == 'standard':\n"
            "        std = s.std()\n"
            "        df[new_col] = (s - s.mean()) / std if std != 0 else s * 0\n"
            "    elif method == 'minmax':\n"
            "        mn, mx = s.min(), s.max()\n"
            "        df[new_col] = (s - mn) / (mx - mn) if mx != mn else s * 0\n"
            "    elif method == 'robust':\n"
            "        iqr = s.quantile(0.75) - s.quantile(0.25)\n"
            "        df[new_col] = (s - s.median()) / iqr if iqr != 0 else s * 0\n"
            "    print(f'Created {new_col}')\n"
        )

    if op == "bin" and len(parts) >= 3:
        col_q = _q(parts[1])
        return (
            f"col = {col_q}\n"
            "new_col = f'{col}__qbin'\n"
            "if col in df.columns and new_col not in df.columns:\n"
            "    s = pd.to_numeric(df[col], errors='coerce').replace([np.inf, -np.inf], np.nan)\n"
            "    df[new_col] = pd.qcut(s, q=min(5, max(2, s.nunique())), labels=False, duplicates='drop')\n"
            "    print(f'Created {new_col}')\n"
        )

    if op == "encode" and len(parts) >= 3:
        col_q, method_q = _q(parts[1]), _q(parts[2])
        return (
            f"col = {col_q}\n"
            f"method = {method_q}\n"
            "if col in df.columns:\n"
            "    if method == 'ohe':\n"
            "        dummies = pd.get_dummies(df[col], prefix=col, dtype=int)\n"
            "        dummies = dummies[[c for c in dummies.columns if c not in df.columns]]\n"
            "        df = pd.concat([df, dummies], axis=1)\n"
            "        print(f'Created {len(dummies.columns)} one-hot columns for {col}')\n"
            "    elif method == 'ordinal':\n"
            "        new_col = f'{col}__ordinal'\n"
            "        if new_col not in df.columns:\n"
            "            cats = df[col].dropna().unique()\n"
            "            mapping = {v: i for i, v in enumerate(sorted(cats, key=str))}\n"
            "            df[new_col] = df[col].map(mapping)\n"
            "            print(f'Created {new_col}')\n"
            "    elif method == 'frequency':\n"
            "        new_col = f'{col}__freq'\n"
            "        if new_col not in df.columns:\n"
            "            freq = df[col].value_counts(normalize=True, dropna=True)\n"
            "            df[new_col] = df[col].map(freq).fillna(0)\n"
            "            print(f'Created {new_col}')\n"
        )

    if op == "target_encode" and len(parts) >= 3:
        col_q, target_q = _q(parts[1]), _q(parts[2])
        return (
            f"col = {col_q}\n"
            f"target = {target_q}\n"
            "new_col = f'{col}__target_enc'\n"
            "if col in df.columns and target in df.columns and col != target and new_col not in df.columns:\n"
            "    y_raw = df[target]\n"
            "    if pd.api.types.is_numeric_dtype(y_raw):\n"
            "        y = pd.to_numeric(y_raw, errors='coerce').replace([np.inf, -np.inf], np.nan)\n"
            "    else:\n"
            "        top_class = y_raw.dropna().astype(str).value_counts().index[0]\n"
            "        y = (y_raw.astype(str) == top_class).astype(float).where(y_raw.notna())\n"
            "    work = pd.DataFrame({'cat': df[col], 'target': y})\n"
            "    global_mean = float(work['target'].mean())\n"
            "    grouped = work.groupby('cat')['target'].agg(['sum', 'count'])\n"
            "    sums = df[col].map(grouped['sum']).astype(float)\n"
            "    counts = df[col].map(grouped['count']).astype(float)\n"
            "    smoothing = 10.0\n"
            "    numerator = (sums - y.fillna(0)) + global_mean * smoothing\n"
            "    denominator = (counts - y.notna().astype(float)).clip(lower=0) + smoothing\n"
            "    df[new_col] = (numerator / denominator).fillna(global_mean)\n"
            "    print(f'Created {new_col}')\n"
        )

    if op in ("datetime", "datetime_decompose") and len(parts) >= 2:
        col_q = _q(parts[1])
        return (
            f"col = {col_q}\n"
            "if col in df.columns:\n"
            "    dt = pd.to_datetime(df[col], errors='coerce')\n"
            "    parts = {\n"
            "        'year': dt.dt.year,\n"
            "        'month': dt.dt.month,\n"
            "        'day': dt.dt.day,\n"
            "        'dayofweek': dt.dt.dayofweek,\n"
            "        'hour': dt.dt.hour,\n"
            "    }\n"
            "    created = []\n"
            "    for part, values in parts.items():\n"
            "        new_col = f'{col}__{part}'\n"
            "        if new_col not in df.columns and (part != 'hour' or values.max() > 0):\n"
            "            df[new_col] = values\n"
            "            created.append(new_col)\n"
            "    print(f'Created datetime columns: {created}')\n"
        )

    if op == "timeseries" and len(parts) >= 4:
        date_col_q, col_q, method_q = _q(parts[1]), _q(parts[2]), _q(parts[3])
        return (
            f"date_col = {date_col_q}\n"
            f"col = {col_q}\n"
            f"method = {method_q}\n"
            "if date_col in df.columns and col in df.columns:\n"
            "    ordered = df.assign(__dt_sort=pd.to_datetime(df[date_col], errors='coerce')).sort_values('__dt_sort')\n"
            "    s = pd.to_numeric(ordered[col], errors='coerce').replace([np.inf, -np.inf], np.nan)\n"
            "    if method == 'lag1':\n"
            "        new_col = f'{col}__lag1'\n"
            "        if new_col not in df.columns:\n"
            "            ordered[new_col] = s.shift(1)\n"
            "            df[new_col] = ordered.sort_index()[new_col]\n"
            "    elif method == 'roll3':\n"
            "        new_col = f'{col}__roll3_mean'\n"
            "        if new_col not in df.columns:\n"
            "            ordered[new_col] = s.rolling(window=3, min_periods=1).mean()\n"
            "            df[new_col] = ordered.sort_index()[new_col]\n"
            "    print(f'Created time-series feature for {col} using {method}')\n"
        )

    return None


def build_workflow_notebook(dataset: dict) -> dict:
    filename = dataset.get("filename", "dataset")
    header_row = dataset.get("header_row")
    skiprows = int(header_row) if header_row is not None else 0
    workflow = dataset.get("workflow", {})
    cleaning_ids = workflow.get("applied_cleaning_fix_ids", [])
    feature_ids = workflow.get("applied_feature_op_ids", [])

    def code_cell(source: str) -> dict:
        return {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": source.splitlines(True),
        }

    def markdown_cell(source: str) -> dict:
        return {
            "cell_type": "markdown",
            "metadata": {},
            "source": source.splitlines(True),
        }

    cells = [
        markdown_cell(
            f"# edaverse workflow for `{filename}`\n\n"
            "This notebook recreates the analysis workflow recorded in edaverse. "
            "Run it against the original uploaded file when you want to reproduce the full pipeline from raw data."
        ),
        markdown_cell("## 1. Load libraries and helper functions\n\nImports plus small helpers used by the cleaning, feature engineering, and chart cells."),
        code_cell(
            "import math\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "try:\n"
            "    plt.style.use('seaborn-v0_8-whitegrid')\n"
            "except Exception:\n"
            "    plt.style.use('default')\n"
            "\n"
            "PLOT_COLORS = {\n"
            "    'teal': '#2f7d72',\n"
            "    'mint': '#74d6c9',\n"
            "    'copper': '#d48b5c',\n"
            "    'amber': '#d99a2b',\n"
            "    'ink': '#10201d',\n"
            "    'muted': '#60736d',\n"
            "}\n"
            "\n"
            "plt.rcParams.update({\n"
            "    'figure.facecolor': '#f8fbf9',\n"
            "    'axes.facecolor': '#ffffff',\n"
            "    'axes.edgecolor': '#d7e2de',\n"
            "    'axes.labelcolor': PLOT_COLORS['ink'],\n"
            "    'axes.titlecolor': PLOT_COLORS['ink'],\n"
            "    'axes.titlesize': 15,\n"
            "    'axes.titleweight': 'bold',\n"
            "    'xtick.color': PLOT_COLORS['muted'],\n"
            "    'ytick.color': PLOT_COLORS['muted'],\n"
            "    'grid.color': '#e3ece8',\n"
            "    'grid.linewidth': 0.8,\n"
            "    'font.size': 11,\n"
            "})\n"
            "\n"
            "def polish_axis(ax, title=None, xlabel=None, ylabel=None):\n"
            "    if title:\n"
            "        ax.set_title(title, loc='left', pad=14)\n"
            "    if xlabel is not None:\n"
            "        ax.set_xlabel(xlabel)\n"
            "    if ylabel is not None:\n"
            "        ax.set_ylabel(ylabel)\n"
            "    ax.spines['top'].set_visible(False)\n"
            "    ax.spines['right'].set_visible(False)\n"
            "    ax.spines['left'].set_color('#d7e2de')\n"
            "    ax.spines['bottom'].set_color('#d7e2de')\n"
            "    ax.grid(axis='x', alpha=0.7)\n"
            "    ax.grid(axis='y', alpha=0.28)\n"
            "    return ax\n"
            "\n"
            "def annotate_horizontal_bars(ax, values, suffix=''):\n"
            "    if len(values) == 0:\n"
            "        return\n"
            "    max_value = max(float(v) for v in values) or 1\n"
            "    for patch, value in zip(ax.patches, values):\n"
            "        ax.text(\n"
            "            patch.get_width() + max_value * 0.015,\n"
            "            patch.get_y() + patch.get_height() / 2,\n"
            "            f'{value:.1f}{suffix}' if isinstance(value, float) else f'{value}{suffix}',\n"
            "            va='center', color=PLOT_COLORS['muted'], fontsize=9,\n"
            "        )\n"
            "\n"
            "STRING_NULLS = {'null', 'none', 'na', 'n/a', 'nan', 'nil', 'missing', '-', '--', '?', 'unknown', ''}\n"
            "\n"
            "def finite_numeric(series):\n"
            "    return pd.to_numeric(series, errors='coerce').replace([np.inf, -np.inf], np.nan)\n"
            "\n"
            "def knn_fill_numeric(df, target_col, k=5):\n"
            "    numeric_df = df.apply(lambda s: pd.to_numeric(s, errors='coerce')).replace([np.inf, -np.inf], np.nan)\n"
            "    target = numeric_df[target_col].copy()\n"
            "    predictors = [\n"
            "        c for c in numeric_df.columns\n"
            "        if c != target_col and numeric_df[c].notna().sum() >= max(5, len(numeric_df) * 0.5)\n"
            "    ][:12]\n"
            "    missing_idx = target[target.isna()].index\n"
            "    if len(missing_idx) == 0 or len(predictors) < 2:\n"
            "        return target.fillna(target.median()), 0\n"
            "    donor_mask = target.notna() & numeric_df[predictors].notna().any(axis=1)\n"
            "    donors = numeric_df.loc[donor_mask, predictors]\n"
            "    donor_y = target.loc[donor_mask]\n"
            "    if len(donors) < k:\n"
            "        return target.fillna(target.median()), int(target.isna().sum())\n"
            "    med = donors.median()\n"
            "    spread = donors.std().replace(0, np.nan).fillna(1)\n"
            "    donors_scaled = ((donors.fillna(med) - med) / spread).to_numpy(dtype=float)\n"
            "    filled = 0\n"
            "    for idx in missing_idx:\n"
            "        row = numeric_df.loc[idx, predictors]\n"
            "        if row.notna().sum() == 0:\n"
            "            continue\n"
            "        row_scaled = ((row.fillna(med) - med) / spread).to_numpy(dtype=float)\n"
            "        distances = np.sqrt(((donors_scaled - row_scaled) ** 2).sum(axis=1))\n"
            "        nearest = np.argsort(distances)[:min(k, len(donor_y))]\n"
            "        target.loc[idx] = float(donor_y.iloc[nearest].median())\n"
            "        filled += 1\n"
            "    return target.fillna(target.median()), filled\n"
        ),
        markdown_cell(
            "## 2. Load the dataset\n\n"
            "Update `DATA_PATH` to your file path. If edaverse used a later row as the header, "
            "`SKIPROWS` is prefilled so pandas starts reading from that header row."
        ),
        code_cell(
            f"DATA_PATH = {_q(filename)}  # You can also write: DATA_PATH = 'Enter Your path'\n"
            f"SKIPROWS = {skiprows}  # edaverse header row selection; keep 0 when the first row is the header.\n"
            "\n"
            "# For Excel files, this is the main line users usually edit:\n"
            "# df = pd.read_excel(DATA_PATH, skiprows=SKIPROWS)\n"
            "\n"
            "path_lower = DATA_PATH.lower()\n"
            "if path_lower.endswith('.parquet'):\n"
            "    df = pd.read_parquet(DATA_PATH)\n"
            "elif path_lower.endswith(('.xlsx', '.xls')):\n"
            "    df = pd.read_excel(DATA_PATH, skiprows=SKIPROWS)\n"
            "elif path_lower.endswith('.json'):\n"
            "    df = pd.read_json(DATA_PATH)\n"
            "else:\n"
            "    df = pd.read_csv(DATA_PATH, skiprows=SKIPROWS)\n"
            "\n"
            "print(df.shape)\n"
            "df.head()\n"
        ),
        markdown_cell("## 3. Initial profile\n\nThis cell summarizes column types, missing values, and basic numeric statistics before transformations."),
        code_cell(
            "profile = pd.DataFrame({\n"
            "    'dtype': df.dtypes.astype(str),\n"
            "    'missing': df.isna().sum(),\n"
            "    'missing_pct': (df.isna().mean() * 100).round(2),\n"
            "    'unique': df.nunique(dropna=False),\n"
            "}).sort_values('missing_pct', ascending=False)\n"
            "display(profile)\n"
            "display(df.describe(include='all').T)\n"
        ),
        markdown_cell("## 4. Missingness chart\n\nThis bar chart shows which columns contain the most missing values."),
        code_cell(
            "missing_pct = (df.isna().mean() * 100).sort_values(ascending=False)\n"
            "missing_pct = missing_pct[missing_pct > 0].head(30)\n"
            "if missing_pct.empty:\n"
            "    print('No missing values detected.')\n"
            "else:\n"
            "    plot_data = missing_pct.sort_values()\n"
            "    fig, ax = plt.subplots(figsize=(11, max(4.5, len(plot_data) * 0.34)))\n"
            "    bars = ax.barh(plot_data.index, plot_data.values, color=PLOT_COLORS['teal'], alpha=0.88)\n"
            "    for bar in bars:\n"
            "        bar.set_edgecolor('#ffffff')\n"
            "        bar.set_linewidth(1.2)\n"
            "    annotate_horizontal_bars(ax, [float(v) for v in plot_data.values], suffix='%')\n"
            "    polish_axis(ax, 'Columns with missing values', 'Missing values (%)', '')\n"
            "    ax.set_xlim(0, max(5, float(plot_data.max()) * 1.16))\n"
            "    plt.tight_layout()\n"
            "    plt.show()\n"
        ),
        markdown_cell("## 5. Numeric distributions\n\nHistograms for numeric columns help reveal skew, outliers, and unusual ranges."),
        code_cell(
            "numeric_cols = df.select_dtypes(include='number').columns.tolist()\n"
            "if not numeric_cols:\n"
            "    print('No numeric columns found.')\n"
            "else:\n"
            "    cols = numeric_cols[:12]\n"
            "    fig, axes = plt.subplots(math.ceil(len(cols) / 3), 3, figsize=(15, 4.2 * math.ceil(len(cols) / 3)))\n"
            "    axes = np.array(axes).reshape(-1)\n"
            "    for ax, col in zip(axes, cols):\n"
            "        values = finite_numeric(df[col]).dropna()\n"
            "        ax.hist(values, bins=32, color=PLOT_COLORS['teal'], alpha=0.86, edgecolor='white', linewidth=0.8)\n"
            "        if len(values):\n"
            "            ax.axvline(values.median(), color=PLOT_COLORS['copper'], linewidth=2, label='median')\n"
            "            ax.legend(frameon=False, fontsize=9)\n"
            "        polish_axis(ax, col, 'Value', 'Rows')\n"
            "    for ax in axes[len(cols):]:\n"
            "        ax.axis('off')\n"
            "    plt.tight_layout()\n"
            "    plt.show()\n"
        ),
        markdown_cell("## 6. Categorical distributions\n\nTop-value bar charts for categorical/text columns show dominant categories and possible cleanup issues."),
        code_cell(
            "categorical_cols = df.select_dtypes(exclude='number').columns.tolist()\n"
            "if not categorical_cols:\n"
            "    print('No categorical columns found.')\n"
            "else:\n"
            "    cols = categorical_cols[:8]\n"
            "    fig, axes = plt.subplots(len(cols), 1, figsize=(12.5, max(4, len(cols) * 3.1)))\n"
            "    axes = np.array([axes]).reshape(-1)\n"
            "    for ax, col in zip(axes, cols):\n"
            "        counts = df[col].astype('object').fillna('Missing').value_counts().head(12).sort_values()\n"
            "        bars = ax.barh(counts.index.astype(str), counts.values, color=PLOT_COLORS['copper'], alpha=0.9)\n"
            "        for bar in bars:\n"
            "            bar.set_edgecolor('#ffffff')\n"
            "            bar.set_linewidth(1.0)\n"
            "        annotate_horizontal_bars(ax, [int(v) for v in counts.values])\n"
            "        polish_axis(ax, col, 'Rows', '')\n"
            "        ax.set_xlim(0, max(1, int(counts.max()) * 1.15))\n"
            "    plt.tight_layout()\n"
            "    plt.show()\n"
        ),
        markdown_cell("## 7. Correlation heatmap\n\nThe heatmap is useful before feature engineering to spot redundancy and strong numeric relationships."),
        code_cell(
            "numeric = df.select_dtypes(include='number')\n"
            "if numeric.shape[1] < 2:\n"
            "    print('Need at least two numeric columns for correlation.')\n"
            "else:\n"
            "    corr = numeric.corr().round(2)\n"
            "    fig, ax = plt.subplots(figsize=(min(14, 0.55 * len(corr.columns) + 4), min(12, 0.55 * len(corr.columns) + 4)))\n"
            "    im = ax.imshow(corr, cmap='BrBG', vmin=-1, vmax=1, interpolation='nearest')\n"
            "    ax.set_xticks(range(len(corr.columns)), corr.columns, rotation=90)\n"
            "    ax.set_yticks(range(len(corr.columns)), corr.columns)\n"
            "    if len(corr.columns) <= 12:\n"
            "        for i in range(len(corr.columns)):\n"
            "            for j in range(len(corr.columns)):\n"
            "                value = corr.iloc[i, j]\n"
            "                ax.text(j, i, f'{value:.2f}', ha='center', va='center', color='#10201d' if abs(value) < 0.55 else '#ffffff', fontsize=8)\n"
            "    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)\n"
            "    polish_axis(ax, 'Numeric correlation heatmap', '', '')\n"
            "    plt.tight_layout()\n"
            "    plt.show()\n"
        ),
    ]

    if cleaning_ids:
        cells.append(markdown_cell("## 8. Applied cleaning workflow\n\nEach code cell below recreates one cleaning action that was applied in edaverse."))
        for fix_id in cleaning_ids:
            code = _cleaning_code(fix_id)
            cells.append(markdown_cell(f"### Cleaning: `{fix_id}`\n\n{_title_from_id(fix_id).capitalize()}."))
            cells.append(code_cell(code or f"# Unsupported cleaning operation: {fix_id}\n"))
    else:
        cells.append(markdown_cell("## 8. Applied cleaning workflow\n\nNo cleaning operations were applied in edaverse."))

    cells.extend([
        markdown_cell("## 9. Profile after cleaning\n\nReview missing values, shape, and a sample after cleaning."),
        code_cell(
            "print('Shape after cleaning:', df.shape)\n"
            "display(pd.DataFrame({\n"
            "    'dtype': df.dtypes.astype(str),\n"
            "    'missing': df.isna().sum(),\n"
            "    'missing_pct': (df.isna().mean() * 100).round(2),\n"
            "}).sort_values('missing_pct', ascending=False))\n"
            "df.head()\n"
        ),
    ])

    if feature_ids:
        cells.append(markdown_cell("## 10. Applied feature engineering workflow\n\nEach code cell below recreates one feature engineering operation that was applied in edaverse."))
        for op_id in feature_ids:
            code = _feature_code(op_id)
            cells.append(markdown_cell(f"### Feature engineering: `{op_id}`\n\n{_title_from_id(op_id).capitalize()}."))
            cells.append(code_cell(code or f"# Unsupported feature operation: {op_id}\n"))
    else:
        cells.append(markdown_cell("## 10. Applied feature engineering workflow\n\nNo feature engineering operations were applied in edaverse."))

    cells.extend([
        markdown_cell("## 11. Final feature overview\n\nThis cell shows the final shape, newly created derived columns, and numeric summary."),
        code_cell(
            "derived_cols = [c for c in df.columns if '__' in c]\n"
            "print('Final shape:', df.shape)\n"
            "print('Derived columns:', len(derived_cols))\n"
            "display(pd.DataFrame({'derived_columns': derived_cols}).head(100))\n"
            "display(df.select_dtypes(include='number').describe().T)\n"
        ),
        markdown_cell("## 12. Final numeric distributions\n\nRun this after feature engineering to inspect the transformed and engineered numeric columns."),
        code_cell(
            "numeric_cols = df.select_dtypes(include='number').columns.tolist()\n"
            "cols = numeric_cols[:16]\n"
            "if not cols:\n"
            "    print('No numeric columns found.')\n"
            "else:\n"
            "    fig, axes = plt.subplots(math.ceil(len(cols) / 4), 4, figsize=(16, 3.6 * math.ceil(len(cols) / 4)))\n"
            "    axes = np.array(axes).reshape(-1)\n"
            "    for ax, col in zip(axes, cols):\n"
            "        values = finite_numeric(df[col]).dropna()\n"
            "        ax.hist(values, bins=32, color=PLOT_COLORS['teal'], alpha=0.86, edgecolor='white', linewidth=0.8)\n"
            "        if len(values):\n"
            "            ax.axvline(values.median(), color=PLOT_COLORS['copper'], linewidth=2)\n"
            "        polish_axis(ax, col, 'Value', 'Rows')\n"
            "    for ax in axes[len(cols):]:\n"
            "        ax.axis('off')\n"
            "    plt.tight_layout()\n"
            "    plt.show()\n"
        ),
        markdown_cell("## 13. Save the transformed dataset\n\nExports the final dataframe produced by this notebook."),
        code_cell(
            "OUTPUT_PATH = 'edaverse_transformed.csv'\n"
            "df.to_csv(OUTPUT_PATH, index=False)\n"
            "print(f'Saved {OUTPUT_PATH} with shape {df.shape}')\n"
        ),
    ])

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
            "edaverse": {
                "dataset_id": dataset.get("id"),
                "source": "workflow_log",
                "applied_cleaning_fix_ids": cleaning_ids,
                "applied_feature_op_ids": feature_ids,
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def notebook_bytes(dataset: dict) -> bytes:
    return json.dumps(build_workflow_notebook(dataset), indent=2).encode("utf-8")
