from flask import Flask, request
import requests
import openai
import os

app = Flask(__name__)

# Set your OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

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

        # Build GPT prompt
        prompt = f"""
You are a friendly, helpful SMS assistant for McGirl Insurance.
Keep replies short. Ask one question at a time.
Only talk about Medicare, VA, TRICARE, or CHAMPVA.
Start by qualifying the user.

User: {body}
AI:"""

        # GPT chat completion call
        gpt_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a warm, smart Medicare SMS assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        reply = gpt_response["choices"][0]["message"]["content"].strip()
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
