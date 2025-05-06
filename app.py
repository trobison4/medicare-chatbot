from flask import Flask, request, jsonify
import requests
import os
import json
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# System prompt
system_prompt = """
You are a friendly, knowledgeable Medicare assistant representing **McGirl Insurance**, helping U.S. veterans, their families, and seniors understand how VA, TRICARE, or CHAMPVA coverage works with Medicare. Your tone is respectful and casual — like texting a friend.

McGirl Insurance does not charge for help. If someone asks about Medicare rules, costs, or coverage specifics, DO NOT explain — instead, book a call with one of our licensed advisors.

---

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

---

✅ IF THEY MENTION CHAMPVA OR TRICARE

Say:
> "You’ll need both Medicare Part A and B to keep your coverage. One of our advisors can explain how that works. Would morning or afternoon be better for a quick call?"

---

✅ AFTER BOOKING, ASK QUALIFYING QUESTIONS

Once booked, ask one at a time:
- "Do you have Medicare Part A and B?"
- "Do you currently use VA healthcare, TRICARE, or CHAMPVA?"
- "Do you have any additional insurance like a supplement or Advantage plan?"

---

✅ IF THEY SAY “NOT NOW”

Say:
> "No problem — I’ll check back in a couple weeks. Reach out anytime if you need help!"

---

✅ TONE GUIDE

- Short, casual, helpful
- 1–2 sentences per reply
- Always end in a question
- Never explain coverage — book first
"""

# Tool definitions (corrected)
tools = [
    {
        "type": "function",
        "function": {
            "name": "getTimeslots",
            "description": "Fetch real-time appointment availability",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
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
                "required": [
                    "first_name", "phone", "email",
                    "time", "coverage", "has_medicare_ab"
                ]
            }
        }
    }
]

@app.route('/')
def home():
    return "SMS Bot is running!"

@app.route('/message', methods=['POST'])
def handle_sms():
    try:
        from_number = request.form.get("From")
        body = request.form.get("Body")

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
                slots = requests.get("http://medicare-chatbot-gz9v.onrender.com/timeslots").json()
                top_slots = [s["time"] for s in slots[:2]]

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

            elif function_name == "bookAppointment":
                booking = requests.post(
                    "https://medicare-chatbot-gz9v.onrender.com/book",
                    json=function_args
                )
                if booking.status_code == 200:
                    reply = f"Perfect. You're booked for {function_args['time']} — confirmation coming soon!"
                else:
                    reply = "Oops — something went wrong trying to book you. Can we try again?"

        else:
            reply = choice.message.content.strip()

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
