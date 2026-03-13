"""
data_connector.py
Abstraction layer for data ingestion.

Current sources
---------------
- CSV file upload (Streamlit / filesystem)
- SQLite / PostgreSQL via SQLAlchemy (ready-to-use)
- REST CRM stub (Salesforce / HubSpot template)

To add a new source, subclass DataConnector and implement `load()`.
"""

from __future__ import annotations

import io
import os
from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text


# ─────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────
class DataConnector(ABC):
    """Abstract base for every data source."""

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Return a raw DataFrame with at least the required columns."""
        ...

    def test_connection(self) -> tuple[bool, str]:
        """Optionally override for health-checks."""
        return True, "OK"


# ─────────────────────────────────────────────
# CSV (primary demo source)
# ─────────────────────────────────────────────
class CSVConnector(DataConnector):
    """
    Accepts either:
        - a file-like object from st.file_uploader
        - a filesystem path (str / Path)
    """

    def __init__(self, source):
        self.source = source

    def load(self) -> pd.DataFrame:
        if isinstance(self.source, (str, os.PathLike)):
            return pd.read_csv(self.source)

        # Streamlit UploadedFile or any file-like
        raw = self.source.read()
        return pd.read_csv(io.BytesIO(raw))


# ─────────────────────────────────────────────
# SQL (SQLite / PostgreSQL / MySQL)
# ─────────────────────────────────────────────
class SQLConnector(DataConnector):
    """
    Usage example
    -------------
    conn = SQLConnector(
        connection_string="postgresql+psycopg2://user:pw@host:5432/db",
        query="SELECT * FROM sales WHERE date >= '2024-01-01'",
    )
    df = conn.load()
    """

    def __init__(self, connection_string: str, query: str):
        self.connection_string = connection_string
        self.query = query
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            self._engine = create_engine(self.connection_string)
        return self._engine

    def test_connection(self) -> tuple[bool, str]:
        try:
            with self._get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Connection successful"
        except Exception as exc:
            return False, str(exc)

    def load(self) -> pd.DataFrame:
        engine = self._get_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(self.query), conn)


# ─────────────────────────────────────────────
# CRM REST stub (Salesforce / HubSpot)
# ─────────────────────────────────────────────
class CRMConnector(DataConnector):
    """
    Lightweight REST stub.  Replace the body of `_fetch_records()` with
    your vendor SDK or API calls.

    Environment variables expected:
        CRM_BASE_URL   https://myorg.salesforce.com/services/data/v59.0
        CRM_API_KEY    <bearer token or API key>
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        endpoint: str = "/query?q=SELECT+Id,Name+FROM+Opportunity",
    ):
        import requests  # lazy import

        self._requests = requests
        self.base_url = base_url or os.getenv("CRM_BASE_URL", "")
        self.api_key  = api_key  or os.getenv("CRM_API_KEY",  "")
        self.endpoint = endpoint

    def test_connection(self) -> tuple[bool, str]:
        if not self.base_url or not self.api_key:
            return False, "CRM_BASE_URL or CRM_API_KEY not configured."
        try:
            resp = self._requests.get(
                self.base_url + self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            resp.raise_for_status()
            return True, "CRM connection successful"
        except Exception as exc:
            return False, str(exc)

    def _fetch_records(self) -> list[dict]:
        """Override this for your specific CRM vendor."""
        resp = self._requests.get(
            self.base_url + self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        # Salesforce wraps results in data["records"]; adjust for your CRM:
        return data.get("records", data)

    def load(self) -> pd.DataFrame:
        records = self._fetch_records()
        return pd.DataFrame(records)


# ─────────────────────────────────────────────
# Factory helper
# ─────────────────────────────────────────────
def get_connector(source_type: str, **kwargs) -> DataConnector:
    """
    Factory:
        get_connector("csv",  source=uploaded_file)
        get_connector("sql",  connection_string="sqlite:///sales.db", query="SELECT * FROM sales")
        get_connector("crm",  base_url="...", api_key="...")
    """
    mapping = {
        "csv": CSVConnector,
        "sql": SQLConnector,
        "crm": CRMConnector,
    }
    cls = mapping.get(source_type.lower())
    if cls is None:
        raise ValueError(f"Unknown source type '{source_type}'. Choose from: {list(mapping)}")
    return cls(**kwargs)
