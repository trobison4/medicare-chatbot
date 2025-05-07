from flask import Flask, request, jsonify
import requests
import os
import json
from datetime import timedelta
from dateutil import parser
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from check_availability import get_available_slots

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === Google Calendar Setup ===
SCOPES = ['https://www.googleapis.com/auth/calendar']
GOOGLE_KEY = json.loads(os.environ["GOOGLE_KEY_JSON"])
BOT_CALENDAR_ID = 'theo@mcgirlinsurance.com'


credentials = service_account.Credentials.from_service_account_info(GOOGLE_KEY, scopes=SCOPES)
calendar_service = build("calendar", "v3", credentials=credentials)

# === GPT SYSTEM PROMPT ===
system_prompt = """
You are a friendly, knowledgeable Medicare assistant representing **McGirl Insurance**, helping U.S. veterans, their families, and seniors understand how VA, TRICARE, or CHAMPVA coverage works with Medicare. Your tone is respectful and casual — like texting a friend.

McGirl Insurance does not charge for help. If someone asks about Medicare rules, costs, or coverage specifics, DO NOT explain — instead, book a call with one of our licensed advisors.

✅ BOOK FIRST — THEN QUALIFY

Always begin by asking:
"Would mornings or afternoons work better for a quick 10-minute call?"

Once they respond:
1. Call `getTimeslots`.
2. Offer ONLY 2 available times:
   > "Great! We’ve got Tuesday at 10 AM or Wednesday at 11 AM — would either work for you?"
3. When the user picks a time, call `bookAppointment`.

Use this format:
{
  "first_name": "Theo",
  "phone": "720-695-7888",
  "email": "theodore.robison@yahoo.com",
  "time": "May 8 at 10:00 AM",
  "coverage": "TRICARE",
  "has_medicare_ab": "Yes"
}

Then confirm:
> "Perfect. You’re booked for [time]. Watch for a confirmation by text or email!"
"""

# === TOOL DEFINITIONS ===
tools = [
    {
        "type": "function",
        "function": {
            "name": "getTimeslots",
            "description": "Fetch real-time appointment availability",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "bookAppointment",
            "description": "Book a Medicare appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "phone": {"type": "string"},
                    "email": {"type": "string"},
                    "time": {"type": "string"},
                    "coverage": {"type": "string"},
                    "has_medicare_ab": {"type": "string"}
                },
                "required": ["first_name", "phone", "email", "time", "coverage", "has_medicare_ab"]
            }
        }
    }
]

@app.route('/')
def home():
    return "SMS Bot is running!"

@app.route('/timeslots', methods=['GET'])
def timeslots():
    try:
        slots = get_available_slots()
        return jsonify([{"time": slot} for slot in slots]), 200
    except Exception as e:
        print("❌ Error in /timeslots:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/message', methods=['POST'])
def handle_sms():
    try:
        data = request.get_json()
        from_number = data["data"]["payload"]["from"]["phone_number"]
        body = data["data"]["payload"]["text"]
        

        print(f"📩 Incoming SMS from {from_number}: {body}")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": body}
            ],
            tools=tools,
            tool_choice="auto"
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            tool_call = choice.message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            print(f"🛠 Tool Call: {function_name} with {function_args}")

            if function_name == "getTimeslots":
                slots = get_available_slots()
                top_slots = slots[:2]

                follow_up = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": body},
                        {"role": "assistant", "tool_calls": [tool_call]},
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": "getTimeslots",
                            "content": json.dumps({"times": top_slots})
                        }
                    ]
                )
                reply = follow_up.choices[0].message.content.strip()
                print(f"🤖 GPT Reply (after timeslots): {reply}")

            elif function_name == "bookAppointment":
                booking = requests.post(
                    "https://medicare-chatbot-gz9v.onrender.com/book",
                    json=function_args
                )
                
                if booking.status_code == 200:
                    reply = f"Perfect. You're booked for {function_args['time']} — confirmation coming soon!"
                else:
                    reply = "Oops — something went wrong trying to book you. Can we try again?"
                print(f"🤖 GPT Reply (after booking): {reply}")

        else:
            reply = choice.message.content.strip()
            print(f"🤖 GPT Reply (no tool): {reply}")

        telnyx_token = os.getenv("TELNYX_API_KEY")
        telnyx_number = os.getenv("TELNYX_PHONE")

        headers = {
        "Authorization": f"Bearer {telnyx_token}",
        "Content-Type": "application/json"
        }

        payload = {
        "from": telnyx_number,
        "to": from_number,
        "text": reply
        }

        telnyx_response = requests.post("https://api.telnyx.com/v2/messages", json=payload, headers=headers)
        print(f"📤 Telnyx status: {telnyx_response.status_code}")
        print(f"📤 Telnyx response body: {telnyx_response.text}")

        return "", 200

    except Exception as e:
        print("❌ Error in /message:", e)
        return "", 500

@app.route('/book', methods=['POST'])
def book_appointment():
    try:
        if not request.is_json:
            return jsonify({"status": "error", "message": "Request must be JSON"}), 400

        data = request.get_json()
        print("📅 Booking data received:", data)

        print(f"📆 Booking to calendar: {BOT_CALENDAR_ID}")


        # Parse "May 8 at 10:00 AM" into datetime
        start = parser.parse(data["time"])
        end = start + timedelta(minutes=30)

        event = {
            "summary": f"Medicare Call: {data['first_name']} ({data['coverage']})",
            "description": f"Has Medicare A/B: {data['has_medicare_ab']}\nPhone: {data['phone']}\nEmail: {data['email']}",
            "start": {"dateTime": start.isoformat(), "timeZone": "America/Denver"},
            "end": {"dateTime": end.isoformat(), "timeZone": "America/Denver"}
        }

        calendar_service.events().insert(calendarId=BOT_CALENDAR_ID, body=event).execute()

        return jsonify({
            "status": "success",
            "message": f"✅ Appointment booked for {data['time']}"
        }), 200

    except Exception as e:
        print("❌ Error in /book:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

