from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app)

# In-memory storage
rooms = {}

@app.route('/')
def home():
    return "LightSplit Backend is running!"

@app.route('/create_room', methods=['POST'])
def create_room():
    data = request.get_json()
    room_id = str(uuid.uuid4())
    rooms[room_id] = {
        "title": data["title"],
        "members": data["members"],
        "payments": {}
    }
    return jsonify({"room_id": room_id})

@app.route('/submit_payment/<room_id>', methods=['POST'])
def submit_payment(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
        
    data = request.get_json()
    name = data["name"]
    amount = float(data["amount"])
    
    rooms[room_id]["payments"][name] = amount
    return jsonify({"success": True})

@app.route('/result/<room_id>', methods=['GET'])
def get_result(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
        
    room = rooms[room_id]
    payments = room["payments"]
    members = room["members"]

    # Ensure all members have an entry in payments
    for member in members:
        if member not in payments:
            payments[member] = 0

    # Calculate total and average
    total = sum(payments.values())
    avg = total / len(members)

    # Calculate balances
    balances = {name: round(amount - avg, 2) for name, amount in payments.items()}

    # Calculate transactions
    transactions = []
    balances_copy = balances.copy()

    while any(abs(balance) > 0.01 for balance in balances_copy.values()):
        # Find max creditor and debtor
        creditors = {k: v for k, v in balances_copy.items() if v > 0}
        debtors = {k: v for k, v in balances_copy.items() if v < 0}

        if not creditors or not debtors:
            break

        max_creditor = max(creditors.items(), key=lambda x: x[1])
        max_debtor = min(debtors.items(), key=lambda x: x[1])

        # Calculate transaction amount
        amount = min(max_creditor[1], -max_debtor[1])
        amount = round(amount, 2)

        # Update balances
        balances_copy[max_creditor[0]] -= amount
        balances_copy[max_debtor[0]] += amount

        transactions.append({
            "from": max_debtor[0],
            "to": max_creditor[0],
            "amount": amount
        })

    return jsonify({
        "title": room["title"],
        "balances": balances,
        "transactions": transactions,
        "total_spent": round(total, 2),
        "average_per_person": round(avg, 2)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
