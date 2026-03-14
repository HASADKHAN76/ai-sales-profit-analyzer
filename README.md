# Sales Analytics Dashboard with AI Assistant

An AI-powered sales analytics dashboard built with Streamlit, featuring secure authentication and intelligent business insights.

| Layer | Technology |
|---|---|
| Frontend / Dashboard | Streamlit |
| Data processing | pandas, NumPy |
| Visualisations | Plotly |
| AI assistant | Google Gemini 2.5 Flash (free tier) + OpenAI fallback + rule-based |
| Authentication | bcrypt + JWT |
| Data ingestion | CSV upload, SQLAlchemy, REST CRM connector |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file with your API keys and secrets:

```bash
# Required for production
JWT_SECRET=replace-with-strong-random-secret

# Optional AI providers (Gemini is recommended - it's free!)
GEMINI_API_KEY=your-gemini-key-here
OPENAI_API_KEY=sk-your-openai-key-here
```

The app works without AI keys using a built-in rule-based assistant.

### 3. Run the app

```bash
streamlit run app.py
```

Open <http://localhost:8501> in your browser.

Default admin credentials (change immediately):
- Username: `admin`
- Password: `admin123`

## Features

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
