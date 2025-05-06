from flask import Flask, request, jsonify
import requests
import os
import json
from openai import OpenAI
from check_availability import get_available_slots  # ✅ Import availability logic

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# GPT System Prompt
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

✅ IF THEY MENTION CHAMPVA OR TRICARE

Say:
> "You’ll need both Medicare Part A and B to keep your coverage. One of our advisors can explain how that works. Would morning or afternoon be better for a quick call?"

✅ AFTER BOOKING, ASK QUALIFYING QUESTIONS

Once booked, ask one at a time:
- "Do you have Medicare Part A and B?"
- "Do you currently use VA healthcare, TRICARE, or CHAMPVA?"
- "Do you have any additional insurance like a supplement or Advantage plan?"

✅ IF THEY SAY “NOT NOW”

Say:
> "No problem — I’ll check back in a couple weeks. Reach out anytime if you need help!"
"""

# GPT Function Tools
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
                slots = requests.get("https://medicare-chatbot-gz9v.onrender.com/timeslots").json()
