"""
WhatsApp Bot for AI Sales Analyzer
Sends daily reports and answers questions via WhatsApp
"""

import os
from datetime import datetime
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import pandas as pd
from data_processor import SalesDataProcessor
from ai_assistant import SalesAIAssistant

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Twilio credentials
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
YOUR_WHATSAPP_NUMBER = os.getenv("YOUR_WHATSAPP_NUMBER")

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Global variables for data
current_df = None
current_processor = None
current_assistant = None


def load_sample_data():
    """Load sample data for demo purposes"""
    global current_df, current_processor, current_assistant

    try:
        # Try to load existing CSV
        if os.path.exists("small_sample.csv"):
            current_df = pd.read_csv("small_sample.csv")
        elif os.path.exists("sample_sales.csv"):
            current_df = pd.read_csv("sample_sales.csv")
        else:
            return False

        # Process data
        current_processor = SalesDataProcessor(current_df)
        context = current_processor.build_ai_context()
        current_assistant = SalesAIAssistant(context)

        return True
    except Exception as e:
        print(f"Error loading data: {e}")
        return False


def send_whatsapp_message(to_number, message):
    """Send a WhatsApp message"""
    try:
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=message,
            to=to_number
        )
        print(f"✓ Message sent: {msg.sid}")
        return True
    except Exception as e:
        print(f"✗ Error sending message: {e}")
        return False


def generate_daily_report():
    """Generate daily sales report"""
    if current_processor is None:
        return "⚠️ No data loaded. Please upload a CSV file first."

    kpis = current_processor.calculate_kpis()
    monthly = current_processor.monthly_summary()
    top_products = current_processor.top_products(n=3)

    report = f"""📊 **Daily Sales Report**
📅 {datetime.now().strftime('%B %d, %Y')}

💰 **Key Metrics:**
• Total Revenue: ${kpis['total_revenue']:,.2f}
• Total Profit: ${kpis['total_profit']:,.2f}
• Profit Margin: {kpis['profit_margin']:.1f}%
• Orders: {kpis['order_count']:,}

📈 **Best Month:**
{monthly.iloc[0]['month']} - ${monthly.iloc[0]['revenue']:,.0f}

🏆 **Top 3 Products:**
"""

    for idx, row in top_products.head(3).iterrows():
        report += f"{idx+1}. {row['product']} - ${row['revenue']:,.0f}\n"

    report += "\n💬 Reply with questions like:\n• 'What's the top customer?'\n• 'Show profit trend'\n• 'Analyze revenue'"

    return report


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages"""
    incoming_msg = request.values.get('Body', '').strip().lower()
    sender = request.values.get('From', '')

    print(f"📱 Received from {sender}: {incoming_msg}")

    # Create response
    resp = MessagingResponse()
    msg = resp.message()

    # Load data if not loaded
    if current_assistant is None:
        if not load_sample_data():
            msg.body("⚠️ Please upload sales data first. Send 'help' for instructions.")
            return str(resp)

    # Command handling
    if incoming_msg in ['hi', 'hello', 'hey', 'start']:
        response = """👋 Welcome to AI Sales Analyzer!

📊 **Commands:**
• 'report' - Get daily sales summary
• 'help' - Show all commands
• Ask any question about your sales data!

**Examples:**
• What's the total revenue?
• Which product sells the most?
• Show me the top customer
• What was the best month?

Powered by Gemini AI 🤖"""

    elif incoming_msg == 'report':
        response = generate_daily_report()

    elif incoming_msg == 'help':
        response = """📚 **Help Menu**

**Quick Commands:**
• 'report' - Daily sales summary
• 'status' - Check system status
• 'help' - Show this menu

**Ask Questions:**
Just type naturally! Examples:
• "What's my total profit?"
• "Which customer bought the most?"
• "Show revenue by month"
• "What's my best selling product?"

**Data Format:**
To analyze your data, upload CSV with:
date, product, price, cost, quantity, customer

Need support? Visit:
github.com/HASADKHAN76/ai-sales-profit-analyzer"""

    elif incoming_msg == 'status':
        ai_status = "✅ Gemini AI" if current_assistant and current_assistant.provider == "gemini" else "⚠️ Rule-based"
        data_rows = len(current_df) if current_df is not None else 0

        response = f"""🔍 **System Status**

✅ Bot: Active
{ai_status}
📊 Data: {data_rows:,} rows loaded
🤖 AI Provider: {current_assistant.provider if current_assistant else 'None'}

Ready to answer your questions!"""

    else:
        # Ask the AI assistant
        if current_assistant:
            try:
                response = current_assistant.chat(incoming_msg)
            except Exception as e:
                response = f"⚠️ Error processing question: {str(e)}\n\nTry asking: 'What is the total revenue?'"
        else:
            response = "⚠️ AI not initialized. Send 'help' for instructions."

    msg.body(response)
    return str(resp)


@app.route("/send-report", methods=["GET"])
def send_daily_report():
    """Endpoint to manually trigger daily report"""
    if not YOUR_WHATSAPP_NUMBER:
        return {"error": "YOUR_WHATSAPP_NUMBER not configured"}, 400

    # Load data
    if not load_sample_data():
        return {"error": "Failed to load data"}, 500

    report = generate_daily_report()
    success = send_whatsapp_message(YOUR_WHATSAPP_NUMBER, report)

    if success:
        return {"status": "Report sent successfully"}
    else:
        return {"error": "Failed to send report"}, 500


@app.route("/", methods=["GET"])
def index():
    """Health check endpoint"""
    return {
        "status": "active",
        "service": "AI Sales Analyzer WhatsApp Bot",
        "data_loaded": current_df is not None,
        "ai_provider": current_assistant.provider if current_assistant else None
    }


if __name__ == "__main__":
    print("🤖 Starting WhatsApp Bot...")
    print(f"📱 Twilio WhatsApp: {TWILIO_WHATSAPP_FROM}")
    print(f"📞 Your Number: {YOUR_WHATSAPP_NUMBER or 'Not set'}")

    # Load sample data on startup
    if load_sample_data():
        print("✅ Sample data loaded successfully")
    else:
        print("⚠️ No sample data found - bot will prompt for upload")

    # Run Flask server
    app.run(host="0.0.0.0", port=5000, debug=True)
