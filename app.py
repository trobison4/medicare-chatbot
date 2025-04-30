from flask import Flask, request, jsonify
import datetime
import json

app = Flask(__name__)

@app.route('/')
def home():
    return "Veteran Booking API is live!"

@app.route('/book', methods=['POST'])
def book():
    try:
        data = request.get_json()

        # Extract info from GPT
        first_name = data.get('first_name', 'Unknown')
        phone = data.get('phone', 'Not provided')
        email = data.get('email', 'Not provided')
        preferred_time = data.get('time', 'Not specified')
        coverage = data.get('coverage', 'Unknown')
        has_medicare = data.get('has_medicare', 'Unknown')

        # Log the booking info
        print("==== New Booking Request ====")
        print(f"Name: {first_name}")
        print(f"Phone: {phone}")
        print(f"Email: {email}")
        print(f"Preferred Time: {preferred_time}")
        print(f"Coverage: {coverage}")
        print(f"Has Medicare A & B: {has_medicare}")
        print("================================")

        # (Optional) Save to file or trigger booking logic here

        return jsonify({"status": "success", "message": f"Booking info received for {first_name}."}), 200

    except Exception as e:
        print("Booking error:", e)
        return jsonify({"status": "error", "message": "Failed to process booking."}), 500

if __name__ == '__main__':
    app.run(debug=True)
