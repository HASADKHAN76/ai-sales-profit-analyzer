"""
WhatsApp Bot for AI Sales Analyzer
Interactive menu-based bot - just tap a number to get info!
"""

import os
from datetime import datetime
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import pandas as pd
from data_processor import load_and_clean, total_kpis, build_context_summary, monthly_summary, top_products, top_customers
from ai_assistant import SalesAIAssistant

load_dotenv()

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
YOUR_WHATSAPP_NUMBER = os.getenv("YOUR_WHATSAPP_NUMBER")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

current_df = None
current_assistant = None


def load_sample_data():
    global current_df, current_assistant
    try:
        if os.path.exists("small_sample.csv"):
            raw_df = pd.read_csv("small_sample.csv")
        elif os.path.exists("sample_sales.csv"):
            raw_df = pd.read_csv("sample_sales.csv")
        else:
            return False
        current_df = load_and_clean(raw_df)
        context = build_context_summary(current_df)
        current_assistant = SalesAIAssistant(context)
        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False


MAIN_MENU = """*AI Sales Analyzer Bot*

Pick a number:

*1* - Full Sales Report
*2* - Top Products
*3* - Top Customers
*4* - Monthly Trends
*5* - Revenue & Profit
*6* - Profit Margins
*7* - Best & Worst Month
*8* - Ask AI a Question
*9* - System Status
*0* - Show This Menu

Just type a number!"""


def get_full_report():
    if current_df is None:
        return "No data loaded."
    kpis = total_kpis(current_df)
    return f"""*Full Sales Report*
{datetime.now().strftime('%B %d, %Y')}

*Revenue:* ${kpis['total_revenue']:,.2f}
*Profit:* ${kpis['total_profit']:,.2f}
*Margin:* {kpis['profit_margin_pct']:.1f}%
*Orders:* {kpis['total_orders']:,}
*Avg Order:* ${kpis['avg_order_value']:,.2f}

Reply *2* for Top Products
Reply *3* for Top Customers
Reply *0* for Main Menu"""


def get_top_products_report():
    if current_df is None:
        return "No data loaded."
    tp = top_products(current_df, n=5)
    msg = "*Top 5 Products by Revenue:*\n\n"
    for i, (_, row) in enumerate(tp.iterrows(), 1):
        msg += f"*{i}. {row['product']}*\n"
        msg += f"   Revenue: ${row['total_revenue']:,.0f}\n"
        msg += f"   Profit: ${row['total_profit']:,.0f}\n"
        msg += f"   Margin: {row['profit_margin_pct']:.0f}%\n"
        msg += f"   Units: {row['units_sold']}\n\n"
    msg += "Reply *0* for Main Menu"
    return msg


def get_top_customers_report():
    if current_df is None:
        return "No data loaded."
    tc = top_customers(current_df, n=5)
    msg = "*Top 5 Customers by Revenue:*\n\n"
    for i, (_, row) in enumerate(tc.iterrows(), 1):
        msg += f"*{i}. {row['customer']}*\n"
        msg += f"   Revenue: ${row['total_revenue']:,.0f}\n"
        msg += f"   Profit: ${row['total_profit']:,.0f}\n"
        msg += f"   Orders: {row['orders']}\n\n"
    msg += "Reply *0* for Main Menu"
    return msg


def get_monthly_trends():
    if current_df is None:
        return "No data loaded."
    ms = monthly_summary(current_df)
    msg = "*Monthly Trends:*\n\n"
    for _, row in ms.iterrows():
        trend = ""
        mom = row.get('mom_revenue_chg_pct')
        if pd.notna(mom):
            arrow = "+" if mom >= 0 else ""
            trend = f" ({arrow}{mom:.0f}%)"
        msg += f"*{row['month_str']}*\n"
        msg += f"  Revenue: ${row['revenue']:,.0f}{trend}\n"
        msg += f"  Profit: ${row['profit']:,.0f}\n"
        msg += f"  Margin: {row['profit_margin_pct']:.0f}%\n\n"
    msg += "Reply *0* for Main Menu"
    return msg


def get_revenue_profit():
    if current_df is None:
        return "No data loaded."
    kpis = total_kpis(current_df)
    return f"""*Revenue & Profit Summary*

*Total Revenue:* ${kpis['total_revenue']:,.2f}
*Total Profit:* ${kpis['total_profit']:,.2f}
*Total Cost:* ${kpis['total_cost']:,.2f}
*Orders:* {kpis['total_orders']:,}
*Avg Order Value:* ${kpis['avg_order_value']:,.2f}

Reply *6* for Profit Margins
Reply *0* for Main Menu"""


def get_profit_margins():
    if current_df is None:
        return "No data loaded."
    kpis = total_kpis(current_df)
    tp = top_products(current_df, n=5)
    msg = f"""*Profit Margin Analysis*

*Overall Margin:* {kpis['profit_margin_pct']:.1f}%

*Margin by Product:*\n\n"""
    for _, row in tp.iterrows():
        m = row['profit_margin_pct']
        bars = int(m / 5)
        bar = "█" * bars + "░" * (20 - bars)
        msg += f"*{row['product']}*\n"
        msg += f"  {bar} {m:.0f}%\n\n"
    msg += "Reply *0* for Main Menu"
    return msg


def get_best_worst_month():
    if current_df is None:
        return "No data loaded."
    ms = monthly_summary(current_df)
    best = ms.loc[ms['revenue'].idxmax()]
    worst = ms.loc[ms['revenue'].idxmin()]
    best_profit = ms.loc[ms['profit'].idxmax()]
    worst_profit = ms.loc[ms['profit'].idxmin()]

    return f"""*Best & Worst Months*

*Highest Revenue:*
  {best['month_str']} - ${best['revenue']:,.0f}

*Lowest Revenue:*
  {worst['month_str']} - ${worst['revenue']:,.0f}

*Highest Profit:*
  {best_profit['month_str']} - ${best_profit['profit']:,.0f}

*Lowest Profit:*
  {worst_profit['month_str']} - ${worst_profit['profit']:,.0f}

Reply *4* for Full Monthly Trends
Reply *0* for Main Menu"""


def get_status():
    provider = current_assistant.provider if current_assistant else 'None'
    data_rows = len(current_df) if current_df is not None else 0
    return f"""*System Status*

*Bot:* Active
*AI:* {provider.upper()}
*Data:* {data_rows:,} rows loaded
*Model:* gemini-2.5-flash

Reply *0* for Main Menu"""


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    print(f"From {sender}: {incoming_msg}")

    resp = MessagingResponse()
    msg = resp.message()

    if current_assistant is None:
        if not load_sample_data():
            msg.body("No data loaded.")
            return str(resp)

    q = incoming_msg.strip()

    try:
        if q == '0' or q.lower() in ['menu', 'hi', 'hello', 'hey', 'start']:
            response = MAIN_MENU
        elif q == '1':
            response = get_full_report()
        elif q == '2':
            response = get_top_products_report()
        elif q == '3':
            response = get_top_customers_report()
        elif q == '4':
            response = get_monthly_trends()
        elif q == '5':
            response = get_revenue_profit()
        elif q == '6':
            response = get_profit_margins()
        elif q == '7':
            response = get_best_worst_month()
        elif q == '8':
            response = """*Ask AI Mode*

Type your question after 8
Example: *8 Which product has best margin?*

Or just type your question directly!

Reply *0* for Main Menu"""
        elif q.startswith('8 ') or q.startswith('8:'):
            question = q[2:].strip()
            response = current_assistant.chat(question)
            response += "\n\nReply *0* for Main Menu"
        elif q == '9':
            response = get_status()
        else:
            response = current_assistant.chat(incoming_msg)
            response += "\n\nReply *0* for Main Menu"
    except Exception as e:
        response = f"Error: {str(e)}\n\nReply *0* for Main Menu"

    msg.body(response)
    return str(resp)


@app.route("/send-report", methods=["GET"])
def send_daily_report():
    if not YOUR_WHATSAPP_NUMBER:
        return {"error": "YOUR_WHATSAPP_NUMBER not configured"}, 400
    if current_df is None:
        if not load_sample_data():
            return {"error": "Failed to load data"}, 500
    report = get_full_report()
    try:
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM, body=report, to=YOUR_WHATSAPP_NUMBER
        )
        return {"status": "Report sent"}
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/", methods=["GET"])
def index():
    return {
        "status": "active",
        "service": "AI Sales Analyzer WhatsApp Bot",
        "data_loaded": current_df is not None,
        "ai_provider": current_assistant.provider if current_assistant else None
    }


if __name__ == "__main__":
    print("=" * 50)
    print("  AI Sales Analyzer - WhatsApp Bot")
    print("=" * 50)

    if load_sample_data():
        print(f"Data loaded | AI: {current_assistant.provider}")
    else:
        print("No sample data found")

    try:
        from pyngrok import ngrok
        public_url = ngrok.connect(5000).public_url
        webhook_url = f"{public_url}/whatsapp"
        print(f"\nngrok: {public_url}")
        print(f"Webhook: {webhook_url}")
        print(f"\n>>> SET IN TWILIO: {webhook_url}")
        print(f"\nBot READY! Send 'hi' on WhatsApp")
    except Exception as e:
        print(f"\nngrok error: {e}")
        print("Running local only...")

    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
