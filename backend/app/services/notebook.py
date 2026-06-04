import json


def build_workflow_notebook(dataset: dict) -> dict:
    filename = dataset.get("filename", "dataset")
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
        markdown_cell(f"# edaverse workflow for `{filename}`\n\nGenerated deterministically from the applied workflow log."),
        code_cell(
            "import pandas as pd\n"
            "\n"
            "# In Colab, upload your exported parquet/csv and update this path.\n"
            "DATA_PATH = 'data.parquet'\n"
            "df = pd.read_parquet(DATA_PATH) if DATA_PATH.endswith('.parquet') else pd.read_csv(DATA_PATH)\n"
            "df.head()\n"
        ),
        code_cell("df.shape, df.dtypes, df.isna().sum().sort_values(ascending=False).head(20)\n"),
    ]

    if cleaning_ids:
        cells.append(markdown_cell("## Cleaning operations\n\n" + "\n".join(f"- `{op}`" for op in cleaning_ids)))
    else:
        cells.append(markdown_cell("## Cleaning operations\n\nNo cleaning operations were applied."))

    if feature_ids:
        cells.append(markdown_cell("## Feature engineering operations\n\n" + "\n".join(f"- `{op}`" for op in feature_ids)))
    else:
        cells.append(markdown_cell("## Feature engineering operations\n\nNo feature engineering operations were applied."))

    cells.extend([
        code_cell("numeric = df.select_dtypes(include='number')\nnumeric.describe().T\n"),
        code_cell("categorical = df.select_dtypes(exclude='number')\n{c: categorical[c].value_counts(dropna=False).head(10) for c in categorical.columns[:10]}\n"),
    ])

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
            "edaverse": {"dataset_id": dataset.get("id"), "source": "workflow_log"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def notebook_bytes(dataset: dict) -> bytes:
    return json.dumps(build_workflow_notebook(dataset), indent=2).encode("utf-8")
