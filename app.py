from flask import Flask, request, jsonify
import requests  # <-- This is the external HTTP library used to send the POST
import datetime
import json
from check_availability import get_available_slots  # ✅ Make sure this exists and works

app = Flask(__name__)

@app.route('/')
def home():
    return "Veteran Booking API is live!"

@app.route('/book', methods=['POST'])
def book():
    try:
        data = request.get_json()

        first_name = data.get('first_name', 'Unknown')
        phone = data.get('phone', 'Not provided')
        email = data.get('email', 'Not provided')
        preferred_time = data.get('time', 'Not specified')
        coverage = data.get('coverage', 'Unknown')
        has_medicare = data.get('has_medicare_ab', 'Unknown')

        # Log the booking info
        print("==== New Booking Request ====")
        print(f"Name: {first_name}")
        print(f"Phone: {phone}")
        print(f"Email: {email}")
        print(f"Preferred Time: {preferred_time}")
        print(f"Coverage: {coverage}")
        print(f"Has Medicare A & B: {has_medicare}")
        print("================================")

        # 🔁 Submit to Go High Level
        ghl_url = "https://link.mcgirlinsurance.com/widget/booking/WEiPPsXPuf4RiQQFb3tm"
        payload = {
            "full_name": first_name,
            "phone": phone,
            "email": email
        }

        print("🔍 Sending this to GHL:", payload)

        try:
            ghl_response = requests.post(ghl_url, data=payload)

            print("📬 GHL status code:", ghl_response.status_code)
            print("📬 GHL response text:", ghl_response.text)
        except Exception as e:
            print("🚨 Exception while posting to GHL:", str(e))


        return jsonify({
            "status": "success",
            "message": f"Booking info received and submitted to GHL for {first_name}."
        }), 200

    except Exception as e:
        print("Booking error:", e)
        return jsonify({
            "status": "error",
            "message": "Failed to process booking.",
            "error": str(e)
        }), 500


@app.route('/timeslots', methods=['GET'])
def timeslots():
    try:
        raw_slots = get_available_slots(limit=10)

        # Format to [{"time": "..."}] for GPT compatibility
        slots = [{"time": slot} for slot in raw_slots]

        return jsonify(slots)
    except Exception as e:
        print("Timeslot error:", e)
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve timeslots.",
            "error": str(e)
        }), 500

