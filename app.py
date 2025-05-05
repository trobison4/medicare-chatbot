from flask import Flask, request, jsonify
import requests
import os
from openai import OpenAI
import datetime
import zoneinfo
import json
from dateutil import parser
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === Google Calendar Setup ===
key_info = json.loads(os.environ['GOOGLE_KEY_JSON'])
SCOPES = ['https://www.googleapis.com/auth/calendar']
BOT_CALENDAR_ID = 'c_81bfd5e6eed02d27fade2338561f7676e9afe81ba165403958ba3d3e383ab9b6@group.calendar.google.com'
MOUNTAIN = zoneinfo.ZoneInfo("America/Denver")
UTC = datetime.timezone.utc

credentials = service_account.Credentials.from_service_account_info(
    key_info, scopes=SCOPES
)
calendar_service = build('calendar', 'v3', credentials=credentials)

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
You are a warm, helpful SMS assistant representing McGirl Insurance.
You only answer questions about Medicare, VA, TRICARE, or CHAMPVA.
Never explain in detail — keep replies short and casual like a friend.
Ask one question at a time.

If a user is open to a call, suggest:
'We’ve got openings like Monday at 10 AM or Tuesday at 2 PM — would either work for you?'

If they pick a time, call the /book endpoint with:
{
  "first_name": "Theo",
  "phone": "720-695-7888",
  "email": "theodore.robison@yahoo.com",
  "time": "May 6 at 10:00 AM",
  "coverage": "TRICARE",
  "has_medicare_ab": "Yes"
}

Then say:
'Perfect. Watch for a confirmation by text or email!'
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

        response = requests.post(twilio_url, data=payload, auth=(twilio_sid, twilio_token))
        print("📤 Twilio status:", response.status_code)

        return "", 200

    except Exception as e:
        print("❌ Error in /message:", e)
        return "", 500

@app.route('/book', methods=['POST'])
def book():
    try:
        data = request.get_json()
        first_name = data['first_name']
        phone = data['phone']
        email = data['email']
        time = data['time']
        coverage = data['coverage']
        has_medicare_ab = data['has_medicare_ab']

        start_local = parser.parse(time).replace(tzinfo=MOUNTAIN)
        end_local = start_local + datetime.timedelta(minutes=30)
        start_utc = start_local.astimezone(UTC).isoformat()
        end_utc = end_local.astimezone(UTC).isoformat()

        event = {
            'summary': f'Booking: {first_name}',
            'description': f'Coverage: {coverage}\nMedicare A/B: {has_medicare_ab}\nPhone: {phone}\nEmail: {email}',
            'start': {'dateTime': start_utc, 'timeZone': 'UTC'},
            'end': {'dateTime': end_utc, 'timeZone': 'UTC'},
            'attendees': [{'email': email}]
        }

        calendar_service.events().insert(calendarId=BOT_CALENDAR_ID, body=event).execute()
        print(f"✅ Booked calendar slot for {first_name} at {time}")
        return jsonify({"status": "success", "message": f"Booked {time} for {first_name}"}), 200

    except Exception as e:
        print("❌ Booking error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/book', methods=['POST'])
def book():
    try:
        data = request.get_json()
        first_name = data['first_name']
        phone = data['phone']
        email = data['email']
        time = data['time']
        coverage = data['coverage']
        has_medicare_ab = data['has_medicare_ab']

        start_local = parser.parse(time).replace(tzinfo=MOUNTAIN)
        end_local = start_local + datetime.timedelta(minutes=30)
        start_utc = start_local.astimezone(UTC).isoformat()
        end_utc = end_local.astimezone(UTC).isoformat()

        event = {
            'summary': f'Booking: {first_name}',
            'description': f'Coverage: {coverage}\nMedicare A/B: {has_medicare_ab}\nPhone: {phone}\nEmail: {email}',
            'start': {'dateTime': start_utc, 'timeZone': 'UTC'},
            'end': {'dateTime': end_utc, 'timeZone': 'UTC'},
            'attendees': [{'email': email}]
        }

        calendar_service.events().insert(calendarId=BOT_CALENDAR_ID, body=event).execute()
        print(f"✅ Booked calendar slot for {first_name} at {time}")
        return jsonify({"status": "success", "message": f"Booked {time} for {first_name}"}), 200

    except Exception as e:
        print("❌ Booking error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
