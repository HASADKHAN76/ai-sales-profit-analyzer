"""Business reports module shared across business types."""

from __future__ import annotations

import streamlit as st
import pandas as pd

import business_management as bm
import database as db


def render_reports_page() -> None:
    business = bm.get_current_business_info()
    if not business:
        st.error("No business selected.")
        return

    st.subheader("Reports")
    revenue = db.get_business_revenue_summary(business["id"])
    transactions = db.get_business_transactions(business["id"], limit=500)

    col1, col2, col3 = st.columns(3)
    col1.metric("Revenue", f"${revenue['total_revenue']:,.0f}")
    col2.metric("Profit", f"${revenue['total_profit']:,.0f}")
    col3.metric("Transactions", f"{revenue['total_transactions']:,}")

    if not transactions:
        st.info("No transactions available for reporting.")
        return

    df = pd.DataFrame(transactions)
    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Transactions CSV",
        data=csv_bytes,
        file_name=f"{business['name'].replace(' ', '_').lower()}_transactions_report.csv",
        mime="text/csv",
    )
