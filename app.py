from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "🧠 Chatbot is running!"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '').lower()

    # Simple logic
    if 'medicare' in message:
        reply = "Thanks for asking about Medicare. Would you like to schedule a free call?"
    elif 'help' in message:
        reply = "Sure, I can help! Ask me about Medicare, supplements, or VA benefits."
    else:
        reply = "I'm not sure what you mean — can you rephrase that?"

    return jsonify({'reply': reply})

if __name__ == '__main__':
    app.run(debug=True)
