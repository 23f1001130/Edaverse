import numpy as np
import pandas as pd
from fastapi import APIRouter, Request
from app.services.auth import get_request_user_id
from app.services.parser import parse_file
from app.services.store import save_dataset, list_datasets, get_dataset

router = APIRouter()

DEMO_FILENAME = "customer_churn_demo.csv"


def _make_demo_csv() -> bytes:
    """Generate a realistic customer churn demo dataset."""
    rng = np.random.default_rng(42)
    n = 2000

    tenure = rng.integers(1, 72, n)
    monthly = rng.normal(70, 25, n).clip(20, 150).round(2)
    total = (tenure * monthly * rng.uniform(0.9, 1.1, n)).round(2)
    age = rng.integers(18, 80, n)
    support = rng.poisson(2, n)
    satisfaction = rng.normal(7, 2, n).clip(1, 10).round(1)

    churn_prob = (
        0.4 * (tenure < 12) + 0.3 * (support > 3) +
        0.3 * (satisfaction < 5) + rng.uniform(0, 0.2, n)
    )
    churn = np.where(churn_prob > 0.5, "Yes", "No")

    df = pd.DataFrame({
        "customer_id": [f"CUST{1000+i}" for i in range(n)],
        "age": age,
        "tenure_months": tenure,
        "monthly_charges": monthly,
        "total_charges": total,
        "contract_type": rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.5, 0.3, 0.2]),
        "payment_method": rng.choice(["Credit card", "Bank transfer", "Electronic check", "Mailed check"], n),
        "support_calls": support,
        "satisfaction_score": satisfaction,
        "churn": churn,
        "signup_date": pd.to_datetime("2020-01-01") + pd.to_timedelta(rng.integers(0, 1460, n), unit="D"),
    })

    df.loc[rng.choice(n, int(n*0.024), replace=False), "age"] = np.nan
    df.loc[rng.choice(n, int(n*0.067), replace=False), "satisfaction_score"] = np.nan

    return df.to_csv(index=False).encode("utf-8")


@router.post("/demo")
async def load_demo(request: Request):
    owner_id = get_request_user_id(request)

    # For signed-in users: reuse an existing demo dataset so we don't create duplicates.
    if owner_id:
        existing = list_datasets(owner_id, include_demo=True)
        for summary in existing:
            if summary.get("filename") == DEMO_FILENAME and summary.get("is_demo"):
                full = get_dataset(summary["id"], owner_id)
                if full:
                    return full

    contents = _make_demo_csv()
    result = parse_file(filename=DEMO_FILENAME, contents=contents)
    if result.get("success"):
        # Mark as demo so it is excluded from the History panel listing
        # but still saved so the EDA pipeline can reference it by ID.
        result["is_demo"] = True
        result = save_dataset(result, owner_id=owner_id)
    return result
