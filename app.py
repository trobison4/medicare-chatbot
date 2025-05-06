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
        "name": "bookAppointment",  # ❌ This is wrong placement
        "type": "function",
        "function": {
            "description": "Book a Medicare appointment",
            ...
        }
    }
]
