from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import os

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app, resources={
    r"/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

rooms = {}

@app.route('/', methods=['GET', 'OPTIONS'])
def index():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    return "Backend is running!"

@app.route('/create_room', methods=['POST'])
def create_room():
    data = request.get_json()
    room_id = str(uuid.uuid4())
    rooms[room_id] = {
        "title": data["title"],
        "members": data["members"],
        "payments": {},
        "payment_descriptions": {}
    }
    return jsonify({
        "room_id": room_id,
        "title": data["title"],
        "members": data["members"]
    })

@app.route('/submit_payment/<room_id>', methods=['POST'])
def submit_payment(room_id):
    data = request.get_json()
    name = data["name"]
    amount = float(data["amount"])
    
    if name in rooms[room_id]["payments"]:
        rooms[room_id]["payments"][name] += amount
    else:
        rooms[room_id]["payments"][name] = amount
    
    if "description" in data:
        rooms[room_id]["payment_descriptions"][name] = data["description"]
    
    return jsonify({"message": "付款已保存！"})

@app.route('/result/<room_id>', methods=['GET'])
def get_result(room_id):
    room = rooms[room_id]
    payments = room["payments"]
    
    for member in room["members"]:
        if member not in payments:
            payments[member] = 0.0
    
    total = sum(payments.values())
    avg = total / len(room["members"])
    balances = {name: round(amount - avg, 2) for name, amount in payments.items()}
    
    transactions = []
    balances_copy = balances.copy()
    while any(abs(b) > 0.01 for b in balances_copy.values()):
        creditor = max(balances_copy.items(), key=lambda x: x[1])
        debtor = min(balances_copy.items(), key=lambda x: x[1])
        amount = min(creditor[1], -debtor[1])
        balances_copy[creditor[0]] -= amount
        balances_copy[debtor[0]] += amount
        transactions.append({
            "from": debtor[0],
            "to": creditor[0],
            "amount": round(amount, 2)
        })
    
    return jsonify({
        "room_id": room_id,
        "title": room["title"],
        "members": room["members"],
        "payments": payments,
        "balances": balances,
        "transactions": transactions,
        "total_spent": round(total, 2),
        "average_per_person": round(avg, 2),
        "payment_descriptions": room.get("payment_descriptions", {})
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
