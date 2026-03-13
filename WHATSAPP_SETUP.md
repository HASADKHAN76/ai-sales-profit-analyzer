# WhatsApp Bot Setup Guide

## Step 1: Create Twilio Account (FREE)

1. Go to https://www.twilio.com/try-twilio
2. Sign up (free trial gives $15 credit)
3. Verify your phone number
4. Skip the "What do you want to build?" questions

## Step 2: Get WhatsApp Sandbox

1. In Twilio Console, go to: **Messaging → Try it out → Send a WhatsApp message**
2. You'll see a number like: `+1 415 523 8886`
3. Send this message from YOUR WhatsApp to that number:
   ```
   join <your-sandbox-code>
   ```
   Example: `join beside-mountain`

4. You'll get a confirmation message ✅

## Step 3: Get Your Credentials

From Twilio Console Dashboard:
- **Account SID**: Starts with `AC...`
- **Auth Token**: Click "Show" to reveal

## Step 4: Save Credentials

Add to your `.env` file:
```bash
TWILIO_ACCOUNT_SID=AC...your-sid...
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
YOUR_WHATSAPP_NUMBER=whatsapp:+1234567890
```

Replace `+1234567890` with YOUR WhatsApp number (with country code)

---

## What's Next?

Run the bot script and start chatting with your Sales Analyzer on WhatsApp!
