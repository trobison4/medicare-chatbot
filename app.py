from flask import Flask, request
import requests
import os
from openai import OpenAI  # ✅ NEW IMPORT

app = Flask(__name__)
client = OpenAI()  # ✅ NEW CLIENT

@app.route('/')
def home():
    return "SMS Bot is running!"

@app.route('/message', methods=['POST'])
def handle_sms():
    try:
        # Get incoming SMS details from Twilio
        from_number = request.form.get("From")
        body = request.form.get("Body")

        print(f"📩 Incoming SMS from {from_number}: {body}")

        # System prompt
        system_prompt = """
You are a friendly, helpful SMS assistant for McGirl Insurance.
You only answer questions about Medicare, VA, TRICARE, or CHAMPVA.
Never explain in detail — keep replies short and casual like a friend.
Ask one question at a time. Always lead toward offering a quick 10-minute call.
If a user asks about costs, coverage, or eligibility, reply:
'I’ll make sure your advisor covers that during the call. Would mornings or afternoons work better?'
"""

        # ✅ GPT chat call using new API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": body}
            ]
        )
        reply = response.choices[0].message.content.strip()
        print(f"🤖 GPT Reply: {reply}")

        # Send reply back using Twilio
        twilio_sid = os.getenv("TWILIO_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_number = os.getenv("TWILIO_PHONE")
        twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"

        payload = {
            "To": from_number,
            "From": twilio_number,
            "Body": reply
        }

        response = requests.post(twilio_url, data=payload, auth=(twilio_sid, twilio_token))
        print("📤 Twilio status:", response.status_code)

        return "", 200

    except Exception as e:
        print("❌ Error in /message:", e)
        return "", 500

if __name__ == '__main__':
    app.run(debug=True)
