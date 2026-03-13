"""
data_processor.py
Core analytics engine — all pandas transformations live here.
"""

import pandas as pd
import numpy as np
from typing import Optional


# ─────────────────────────────────────────────
# Schema validation
# ─────────────────────────────────────────────
REQUIRED_COLUMNS = {"date", "product", "price", "cost", "quantity", "customer"}


def validate_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    """Return (ok, error_message). Empty error means success."""
    missing = REQUIRED_COLUMNS - set(df.columns.str.lower().str.strip())
    if missing:
        return False, f"Missing required columns: {', '.join(sorted(missing))}"
    return True, ""


# ─────────────────────────────────────────────
# Normalisation
# ─────────────────────────────────────────────
def load_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise column names, parse dates, derive revenue / profit columns.
    Returns a clean DataFrame ready for analysis.
    """
    df = df.copy()
    df.columns = df.columns.str.lower().str.strip()

    # Parse date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df.dropna(subset=["date"], inplace=True)

    # Numeric coercion
    for col in ("price", "cost", "quantity"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Derived metrics
    df["revenue"]    = df["price"] * df["quantity"]
    df["total_cost"] = df["cost"]  * df["quantity"]
    df["profit"]     = df["revenue"] - df["total_cost"]

    # Calendar helpers
    df["month"]      = df["date"].dt.to_period("M")
    df["month_str"]  = df["month"].dt.strftime("%b %Y")
    df["year"]       = df["date"].dt.year

    return df


# ─────────────────────────────────────────────
# KPI helpers
# ─────────────────────────────────────────────
def total_kpis(df: pd.DataFrame) -> dict:
    return {
        "total_revenue":     round(df["revenue"].sum(), 2),
        "total_profit":      round(df["profit"].sum(), 2),
        "total_cost":        round(df["total_cost"].sum(), 2),
        "total_orders":      len(df),
        "profit_margin_pct": round(
            df["profit"].sum() / df["revenue"].sum() * 100
            if df["revenue"].sum() else 0, 2
        ),
        "avg_order_value":   round(df["revenue"].mean(), 2),
    }


# ─────────────────────────────────────────────
# Monthly breakdowns
# ─────────────────────────────────────────────
def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate revenue, profit, orders by calendar month."""
    grp = (
        df.groupby(["month", "month_str"], sort=True)
        .agg(
            revenue=("revenue", "sum"),
            profit=("profit", "sum"),
            total_cost=("total_cost", "sum"),
            orders=("revenue", "count"),
        )
        .reset_index()
        .sort_values("month")
    )
    grp["profit_margin_pct"] = (
        grp["profit"] / grp["revenue"].replace(0, np.nan) * 100
    ).round(2)
    grp["mom_revenue_chg_pct"] = grp["revenue"].pct_change().mul(100).round(2)
    grp["mom_profit_chg_pct"]  = grp["profit"].pct_change().mul(100).round(2)
    return grp.drop(columns=["month"])


# ─────────────────────────────────────────────
# Product analytics
# ─────────────────────────────────────────────
def top_products(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    grp = (
        df.groupby("product")
        .agg(
            total_revenue=("revenue", "sum"),
            total_profit=("profit", "sum"),
            units_sold=("quantity", "sum"),
            orders=("revenue", "count"),
        )
        .reset_index()
        .sort_values("total_revenue", ascending=False)
        .head(n)
    )
    grp["profit_margin_pct"] = (
        grp["total_profit"] / grp["total_revenue"].replace(0, np.nan) * 100
    ).round(2)
    return grp


def product_monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot: rows = month, columns = product, values = revenue."""
    pivot = (
        df.groupby(["month_str", "product"])["revenue"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    return pivot


# ─────────────────────────────────────────────
# Customer analytics
# ─────────────────────────────────────────────
def top_customers(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    grp = (
        df.groupby("customer")
        .agg(
            total_revenue=("revenue", "sum"),
            total_profit=("profit", "sum"),
            orders=("revenue", "count"),
        )
        .reset_index()
        .sort_values("total_revenue", ascending=False)
        .head(n)
    )
    grp["avg_order_value"] = (
        grp["total_revenue"] / grp["orders"].replace(0, np.nan)
    ).round(2)
    return grp


# ─────────────────────────────────────────────
# AI-ready context snapshot
# ─────────────────────────────────────────────
def build_context_summary(df: pd.DataFrame) -> str:
    """
    Return a compact plaintext summary of the dataset
    to be injected into the AI system prompt.
    """
    kpis   = total_kpis(df)
    monthly = monthly_summary(df)
    prods   = top_products(df, n=5)
    custs   = top_customers(df, n=5)

    best_month_rev = monthly.loc[monthly["revenue"].idxmax(), "month_str"]
    best_month_prf = monthly.loc[monthly["profit"].idxmax(),  "month_str"]
    worst_month    = monthly.loc[monthly["revenue"].idxmin(), "month_str"]

    lines = [
        "=== SALES DATASET SUMMARY ===",
        f"Date range    : {df['date'].min().date()} → {df['date'].max().date()}",
        f"Total records : {kpis['total_orders']:,}",
        f"Total revenue : ${kpis['total_revenue']:,.2f}",
        f"Total profit  : ${kpis['total_profit']:,.2f}",
        f"Profit margin : {kpis['profit_margin_pct']}%",
        f"Avg order val : ${kpis['avg_order_value']:,.2f}",
        "",
        "--- Monthly Snapshot ---",
    ]
    for _, row in monthly.iterrows():
        lines.append(
            f"  {row['month_str']}: revenue=${row['revenue']:,.2f}  "
            f"profit=${row['profit']:,.2f}  "
            f"margin={row['profit_margin_pct']}%"
        )

    lines += [
        "",
        f"Best revenue month : {best_month_rev}",
        f"Best profit month  : {best_month_prf}",
        f"Lowest revenue month: {worst_month}",
        "",
        "--- Top 5 Products (by revenue) ---",
    ]
    for _, r in prods.iterrows():
        lines.append(
            f"  {r['product']}: revenue=${r['total_revenue']:,.2f}  "
            f"units={int(r['units_sold'])}  margin={r['profit_margin_pct']}%"
        )

    lines += ["", "--- Top 5 Customers (by revenue) ---"]
    for _, r in custs.iterrows():
        lines.append(
            f"  {r['customer']}: revenue=${r['total_revenue']:,.2f}  "
            f"orders={int(r['orders'])}  avg_order=${r['avg_order_value']:,.2f}"
        )

    return "\n".join(lines)
