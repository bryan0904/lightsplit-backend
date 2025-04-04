from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)

rooms = {}

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
    return jsonify({"room_id": room_id})

@app.route('/submit_payment/<room_id>', methods=['POST'])
def submit_payment(room_id):
    data = request.get_json()
    name = data["name"]
    amount = float(data["amount"])
    
    # 关键修复：累加金额，而不是覆盖
    if name in rooms[room_id]["payments"]:
        rooms[room_id]["payments"][name] += amount
    else:
        rooms[room_id]["payments"][name] = amount
    
    if "description" in data:
        rooms[room_id]["payment_descriptions"][name] = data["description"]
    
    return jsonify({"message": "Payment saved!"})

@app.route('/result/<room_id>', methods=['GET'])
def get_result(room_id):
    room = rooms[room_id]
    payments = room["payments"]
    members = room["members"]
    
    # 确保所有成员都有金额记录（即使没付过钱）
    for member in members:
        if member not in payments:
            payments[member] = 0.0
    
    total = sum(payments.values())
    avg = total / len(members)
    balances = {name: round(amount - avg, 2) for name, amount in payments.items()}
    
    # 计算谁该给谁钱
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
        "members": members,
        "payments": payments,
        "balances": balances,
        "transactions": transactions,
        "total_spent": round(total, 2),
        "average_per_person": round(avg, 2),
        "payment_descriptions": room.get("payment_descriptions", {})
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
