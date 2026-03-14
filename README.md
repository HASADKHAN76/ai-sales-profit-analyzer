# RetailBrain AI — Retail & E-commerce Analytics Platform

An AI-powered sales analytics dashboard for retail and e-commerce businesses, built with:

| Layer | Technology |
|---|---|
| Frontend / Dashboard | Streamlit |
| Data processing | pandas, NumPy |
| Visualisations | Plotly |
| AI assistant | Google Gemini 2.5 Flash (free tier) + OpenAI fallback + rule-based |
| Authentication | bcrypt + JWT + 2FA |
| Data ingestion | CSV upload, SQLAlchemy, REST CRM connector |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure AI (Optional but Recommended)

**Option 1: Google Gemini (FREE - Recommended)**

```bash
# Get free API key from https://makersuite.google.com/app/apikey
echo "GEMINI_API_KEY=your-gemini-key-here" > .env
```

**Option 2: OpenAI (Paid)**

```bash
echo "OPENAI_API_KEY=sk-..." >> .env
```

The app works without any API key using a built-in rule-based assistant.

### 3. Run the app

```bash
streamlit run app.py
```

Open <http://localhost:8501> in your browser.

---

## CSV Format

The uploaded CSV must contain these columns (names are case-insensitive):

| Column | Type | Description |
|---|---|---|
| `date` | date string | Transaction date |
| `product` | string | Product name / SKU |
| `price` | number | Unit selling price |
| `cost` | number | Unit cost of goods |
| `quantity` | integer | Units sold |
| `customer` | string | Customer / company name |

---

## Features

### Overview Dashboard
- KPI cards: total revenue, profit, margin %, order count, average order value
- Grouped bar chart: monthly revenue vs profit with margin % overlay
- Month-over-month revenue change (positive = green, negative = red)
- Profit margin area chart by month

### Products Tab
- Horizontal bar chart coloured by margin %
- Searchable data table with revenue, profit, units sold
- Units sold donut chart

### Customers Tab
- Top customers ranked by revenue
- Customer scatter analysis (orders vs revenue)

### Raw Data Tab
- Preview processed dataset (first 500 rows)
- Download processed CSV

### AI Assistant Tab
- Quick question buttons (one-click)
- Free-text chat input
- Scrollable conversation history
- Dataset context panel showing what the AI sees

### User Management
- Secure login with bcrypt password hashing
- JWT session tokens
- Two-factor authentication (2FA) support
- Admin panel for user management

---

## Data Sources

### SQL database

```python
from data_connector import SQLConnector

conn = SQLConnector(
    connection_string="postgresql+psycopg2://user:pw@host:5432/db",
    query="SELECT * FROM sales WHERE date >= '2024-01-01'",
)
df = conn.load()
```

### CRM REST API

```python
from data_connector import CRMConnector

conn = CRMConnector(
    base_url="https://myorg.salesforce.com/services/data/v59.0",
    api_key="<your-bearer-token>",
    endpoint="/query?q=SELECT+Id,Amount+FROM+Opportunity",
)
df = conn.load()
```

Subclass `DataConnector` and implement `load()` for any other source.

---

## AI Model Configuration

The app automatically uses the first available AI provider:

1. **Google Gemini** (priority if `GEMINI_API_KEY` is set)
   - Model: `gemini-2.5-flash`
   - Free tier: 60 requests/minute

2. **OpenAI** (fallback if `OPENAI_API_KEY` is set)
   - Model: `gpt-3.5-turbo`

3. **Rule-based** (works with no API keys)

---

## License

MIT
