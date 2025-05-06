from flask import Flask, request, jsonify
import requests
import os
from openai import OpenAI

app = Flask(__name__)

# 🔐 Load OpenAI API key from environment
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

        # 🔮 Ask GPT for a reply
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": body}
            ]
        )
        reply = response.choices[0].message.content.strip()
        print(f"🤖 GPT Reply: {reply}")

        # 📤 Reply back via Twilio
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
def book_to_ghl():
    try:
        data = request.get_json()

        first_name = data.get("first_name", "Unknown")
        phone = data.get("phone")
        email = data.get("email")
        time = data.get("time")
        coverage = data.get("coverage", "Not provided")
        has_medicare = data.get("has_medicare_ab", "Unknown")

        print("📅 Booking request received:")
        print(data)

        payload = {
            "calendarId": "WEiPPsXPuf4RiQQFb3tm",
            "contact": {
                "firstName": first_name,
                "email": email,
                "phone": phone
            },
            "customFields": {
                "coverage_type": coverage,
                "has_medicare_ab": has_medicare
            },
            "startTime": time,
            "timezone": "America/Denver"
        }

        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJsb2NhdGlvbl9pZCI6Ilo3RXJ3NzVESDJaVEpDUFlMRllMIiwidmVyc2lvbiI6MSwiaWF0IjoxNzQ2NDg4OTIzNjA5LCJzdWIiOiJ4cTNLQ1dIZlJDWnJORkw2ZzFFYyJ9.wt_8fHtOrPmvxHB47HcwEhxpDtpanopPAQu2I8eC0es",
            "Content-Type": "application/json"
        }

        ghl_url = "https://rest.gohighlevel.com/v1/appointments/"
        response = requests.post(ghl_url, json=payload, headers=headers)

        print("📤 GHL response:", response.status_code, response.text)

        if response.status_code in [200, 201]:
            return jsonify({"status": "success", "message": f"Booked to GHL calendar for {first_name}"}), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to book appointment",
                "ghl_response": response.text
            }), 400

    except Exception as e:
        print("❌ Booking Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
