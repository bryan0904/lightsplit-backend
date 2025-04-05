# app.py 的修改版
from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import random
import time

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
    
    # 生成一个4位数的房间ID
    while True:
        room_id = str(random.randint(1000, 9999))
        if room_id not in rooms:  # 确保唯一性
            break
    
    rooms[room_id] = {
        "title": data["title"],
        "members": data["members"],
        "payments": {},
        "payment_records": []  # 新增：用于保存详细的支付记录
    }
    return jsonify({"room_id": room_id})

@app.route('/submit_payment/<room_id>', methods=['POST'])
def submit_payment(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
        
    data = request.get_json()
    name = data["name"]
    amount = float(data["amount"])
    description = data.get("description", "未填写描述")  # 新增：获取描述
    
    # 累计付款金额
    if name in rooms[room_id]["payments"]:
        rooms[room_id]["payments"][name] += amount
    else:
        rooms[room_id]["payments"][name] = amount
        
    # 保存详细的支付记录
    payment_record = {
        "id": str(time.time()),  # 使用时间戳作为ID
        "name": name,
        "amount": amount,
        "description": description,
        "date": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    rooms[room_id]["payment_records"].append(payment_record)
        
    return jsonify({"success": True})

@app.route('/result/<room_id>', methods=['GET'])
def get_result(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
        
    room = rooms[room_id]
    payments = room["payments"]
    members = room["members"]

    # 确保所有成员都有付款记录
    for member in members:
        if member not in payments:
            payments[member] = 0

    # 计算总额和平均值
    total = sum(payments.values())
    avg = total / len(members) if len(members) > 0 else 0

    # 计算每人余额
    balances = {name: round(amount - avg, 2) for name, amount in payments.items()}

    # 计算转账明细
    transactions = []
    balances_copy = balances.copy()

    while any(abs(balance) > 0.01 for balance in balances_copy.values()):
        # 找出最大债权人和债务人
        creditors = {k: v for k, v in balances_copy.items() if v > 0}
        debtors = {k: v for k, v in balances_copy.items() if v < 0}

        if not creditors or not debtors:
            break

        max_creditor = max(creditors.items(), key=lambda x: x[1])
        max_debtor = min(debtors.items(), key=lambda x: x[1])

        # 计算转账金额
        amount = min(max_creditor[1], -max_debtor[1])
        amount = round(amount, 2)

        # 更新余额
        balances_copy[max_creditor[0]] -= amount
        balances_copy[max_debtor[0]] += amount

        transactions.append({
            "from": max_debtor[0],
            "to": max_creditor[0],
            "amount": amount
        })

    return jsonify({
        "title": room["title"],
        "members": room["members"],
        "balances": balances,
        "transactions": transactions,
        "total_spent": round(total, 2),
        "average_per_person": round(avg, 2),
        "payment_records": room["payment_records"]  # 新增：返回详细的支付记录
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
