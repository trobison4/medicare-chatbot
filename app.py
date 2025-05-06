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
"We’ve got Monday at 10 AM or Tuesday at 2 PM — would either work for you?"

If they pick a time, call /book with:
{
  "first_name": "Theo",
  "phone": "720-695-7888",
  "email": "theodore.robison@yahoo.com",
  "slot_id": "replace_with_slot_id",
  "timezone": "America/Denver",
  "coverage": "TRICARE",
  "has_medicare_ab": "Yes"
}
Then reply: "Perfect. Watch for a confirmation by text or email!"
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
        first_name = data.get("first_name")
        phone = data.get("phone")
        email = data.get("email")
        slot_id = data.get("slot_id")
        timezone = data.get("timezone", "America/Denver")
        coverage = data.get("coverage", "Unknown")
        has_medicare = data.get("has_medicare_ab", "Unknown")

        ghl_url = "https://rest.gohighlevel.com/v1/appointments/"
        headers = {
            "Authorization": f"Bearer {os.getenv('GHL_API_KEY')}",
            "Content-Type": "application/json"
        }

        payload = {
            "calendarId": "WEiPPsXPuf4RiQQFb3tm",
            "selectedSlot": slot_id,
            "selectedTimezone": timezone,
            "contact": {
                "firstName": first_name,
                "email": email,
                "phone": phone
            },
            "customFields": {
                "coverage_type": coverage,
                "has_medicare_ab": has_medicare
            }
        }

        print("📤 Booking payload:", payload)
        response = requests.post(ghl_url, json=payload, headers=headers)
        print("📥 GHL response:", response.status_code, response.text)

        if response.status_code in [200, 201]:
            return jsonify({"status": "success", "message": f"Booked to GHL for {first_name}"}), 200
        else:
            return jsonify({"status": "error", "message": "Booking failed", "ghl_response": response.text}), 400

    except Exception as e:
        print("❌ Error in /book:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)