from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["https://lightsplit-frontend.vercel.app", "http://localhost:3000"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

rooms = {}

@app.route('/')
def home():
    return "Welcome to the lightsplit app!"

@app.route('/create_room', methods=['POST'])
def create_room():
    try:
        data = request.get_json()
        if not data or 'title' not in data or 'members' not in data:
            return jsonify({"error": "Missing title or members"}), 400
            
        room_id = str(uuid.uuid4())
        rooms[room_id] = {
            "title": data["title"],
            "members": data["members"],
            "payments": {}
        }
        return jsonify({"room_id": room_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/submit_payment/<room_id>', methods=['POST'])
def submit_payment(room_id):
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'amount' not in data:
            return jsonify({"error": "Missing name or amount"}), 400
            
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        rooms[room_id]["payments"][data["name"]] = float(data["amount"])
        return jsonify({"message": "Payment saved!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/result/<room_id>', methods=['GET'])
def get_result(room_id):
    try:
        if room_id not in rooms:
            return jsonify({"error": "Room not found"}), 404
            
        room = rooms[room_id]
        payments = room["payments"]
        members = room["members"]
        
        for member in members:
            payments.setdefault(member, 0)
        
        total = sum(float(v) for v in payments.values())
        avg = total / len(members)
        
        balances = {name: round(float(amount) - avg, 2) for name, amount in payments.items()}
        transactions = []
        balances_copy = balances.copy()
        
        while any(abs(balance) > 0.01 for balance in balances_copy.values()):
            creditors = {k: v for k, v in balances_copy.items() if v > 0}
            debtors = {k: v for k, v in balances_copy.items() if v < 0}
            
            if not creditors or not debtors:
                break
                
            max_creditor = max(creditors.items(), key=lambda x: x[1])
            max_debtor = min(debtors.items(), key=lambda x: x[1])
            
            amount = min(max_creditor[1], -max_debtor[1])
            amount = round(amount, 2)
            
            balances_copy[max_creditor[0]] -= amount
            balances_copy[max_debtor[0]] += amount
            
            transactions.append({
                "from": max_debtor[0],
                "to": max_creditor[0],
                "amount": amount
            })
        
        return jsonify({
            "room_id": room_id,
            "title": room["title"],
            "balances": balances,
            "transactions": transactions,
            "total_spent": round(total, 2),
            "average_per_person": round(avg, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
