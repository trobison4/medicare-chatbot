from flask import Flask, request, jsonify, send_file
import requests
import os
import json
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/message', methods=['POST'])
def handle_sms():
    try:
        from_number = request.form.get("From")
        body = request.form.get("Body")

        print(f"📩 Incoming SMS from {from_number}: {body}")

        system_prompt = """You are a friendly Medicare assistant for McGirl Insurance. 
Always reply via SMS in short, casual messages. Ask one question at a time.
Use tools to book appointments or check availability. Never guess a time. 
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": body}
            ],
            tools=[
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
                    "name": "bookAppointment",
                    "type": "function",
                    "function": {
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
            ],
            tool_choice="auto"
        )

        choice = response.choices[0]

        # 🔁 If GPT wants to call a function/tool
        if choice.finish_reason == "tool_calls":
            tool_call = choice.message.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            print(f"🛠 GPT Tool Call: {function_name} with {function_args}")

            if function_name == "getTimeslots":
                # Call your own /timeslots endpoint
                slot_resp = requests.get("https://medicare-chatbot-gz9v.onrender.com/timeslots")
                times = slot_resp.json()
                formatted = [t["time"] for t in times[:2]]

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
                            "content": json.dumps({"times": formatted})
                        }
                    ]
                )
                reply = follow_up.choices[0].message.content.strip()

            elif function_name == "bookAppointment":
                book_resp = requests.post(
                    "https://medicare-chatbot-gz9v.onrender.com/book",
                    json=function_args
                )
                if book_resp.status_code == 200:
                    reply = f"Perfect. You're booked for {function_args['time']} — confirmation coming soon!"
                else:
                    reply = "Oops — something went wrong trying to book you. Can we try again?"

        else:
            reply = choice.message.content.strip()

        # ✅ Send back via Twilio
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
