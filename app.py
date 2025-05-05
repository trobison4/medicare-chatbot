from flask import Flask, request, jsonify
import requests
import os
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/')
def home():
    return "SMS Bot is running!"

@app.route('/message', methods=['POST'])
def handle_sms():
    try:
        from_number = request.form.get("From")
        body = request.form.get("Body")

        print(f"📩 Incoming SMS from {from_number}: {body}")

        system_prompt = """
You are a friendly SMS assistant for McGirl Insurance.
Only answer questions about Medicare, VA, TRICARE, or CHAMPVA.
Keep replies casual and short like a friend. Ask one question at a time.
If a user is ready, say:
'We’ve got Monday at 10 AM or Tuesday at 2 PM — would either work for you?'

If they pick a time, call /book with:
{
  "first_name": "Theo",
  "phone": "720-695-7888",
  "email": "theodore.robison@yahoo.com",
  "time": "May 6 at 10:00 AM",
  "coverage": "TRICARE",
  "has_medicare_ab": "Yes"
}
Then reply: 'Perfect. Watch for a confirmation by text or email!'
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": body}
            ]
        )
        reply = response.choices[0].message.content.strip()
        print(f"🤖 GPT Reply: {reply}")

        # Send reply via Twilio
        twilio_sid = os.getenv("TWILIO_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_number = os.getenv("TWILIO_PHONE")
        twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"

        payload = {
            "To": from_number,
            "From": twilio_number,
            "Body": reply
        }

        requests.post(twilio_url, data=payload, auth=(twilio_sid, twilio_token))
        return "", 200

    except Exception as e:
        print("❌ Error in /message:", e)
        return "", 500

@app.route('/book', methods=['POST'])
def book():
    try:
        data = request.get_json()
        first_name = data.get('first_name', 'Unknown')
        phone = data.get('phone', 'Not provided')
        email = data.get('email', 'Not provided')

        # 📤 Submit to GHL calendar booking link
        ghl_url = "https://link.mcgirlinsurance.com/widget/booking/WEiPPsXPuf4RiQQFb3tm"
        payload = {
            "full_name": first_name,
            "phone": phone,
            "email": email
        }

        print("📨 Submitting booking to GHL:", payload)
        response = requests.post(ghl_url, data=payload)
        print("📬 GHL Response:", response.status_code, response.text)

        return jsonify({"status": "success", "message": f"Submitted to GHL for {first_name}"}), 200

    except Exception as e:
        print("❌ Error in /book:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
