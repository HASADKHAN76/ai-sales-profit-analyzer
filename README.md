# AI Sales & Profit Analyzer

A full-stack, AI-powered sales analytics dashboard built with:

| Layer | Technology |
|---|---|
| Frontend / Dashboard | Streamlit |
| Data processing | pandas, NumPy |
| Visualisations | Plotly |
| AI assistant | Google Gemini 2.5 Flash (free tier) + OpenAI fallback + rule-based |
| Data ingestion | CSV upload, SQLAlchemy, REST CRM stub |

---

## Project Structure

```
sales_analyzer/
├── app.py                   # Streamlit dashboard (entry point)
├── data_processor.py        # All pandas analytics & KPI calculations
├── ai_assistant.py          # OpenAI chatbot + rule-based fallback
├── data_connector.py        # CSV / SQL / CRM data abstraction layer
├── sample_data_generator.py # Generates a realistic demo CSV
├── requirements.txt
└── .env.example             # Environment variables template
```

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

# Free tier: 60 requests/minute, no credit card required!
```

**Option 2: OpenAI (Paid)**

```bash
echo "OPENAI_API_KEY=sk-..." >> .env
```

The app works without any API key using a built-in rule-based assistant.

### 3. Generate sample data (optional)

```bash
python sample_data_generator.py             # → sample_sales.csv  (2 000 rows)
python sample_data_generator.py --rows 5000 # larger dataset
```

### 4. Run the app

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

### Dashboard tab
- KPI cards: total revenue, profit, margin %, order count, average order value
- Grouped bar chart: monthly revenue vs profit with margin % overlay
- Month-over-month revenue change (positive = green, negative = red)
- Profit margin area chart by month

### Products tab
- Horizontal bar chart coloured by margin %
- Searchable data table with revenue, profit, units sold
- Units sold pie / donut chart

### Customers tab
- Top customers ranked by revenue
- Order count heatmap colour scale

### Raw Data tab
- Preview processed dataset (first 500 rows)
- Download processed CSV

### AI Assistant tab
- Six suggested question buttons (one-click)
- Free-text chat input
- Scrollable conversation history
- Expandable "dataset context" panel showing what the AI sees

---

## Extending Data Sources

### SQL database

```python
from data_connector import SQLConnector

conn = SQLConnector(
    connection_string="postgresql+psycopg2://user:pw@host:5432/db",
    query="SELECT * FROM sales WHERE date >= '2024-01-01'",
)
df = conn.load()
```

### CRM REST API (Salesforce / HubSpot)

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
   - Change to `gpt-4o` in `ai_assistant.py` for better answers

3. **Rule-based** (works with no API keys)

---

## Deploy to Streamlit Cloud

### Step 1: Prepare Repository
Your code is already on GitHub: `https://github.com/HASADKHAN76/ai-sales-profit-analyzer`

### Step 2: Deploy
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select:
   - Repository: `HASADKHAN76/ai-sales-profit-analyzer`
   - Branch: `main`
   - Main file: `app.py`

### Step 3: Add Secrets
In the app settings, add your secrets:

```toml
GEMINI_API_KEY = "AIzaSy..."
```

### Step 4: Deploy!
Click "Deploy" and your app will be live in minutes!

**Live URL:** `https://your-app-name.streamlit.app`

---

## License

MIT
