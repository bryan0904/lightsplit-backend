# app.py 更新版本
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
        "payment_records": []  # 用于保存详细的支付记录
    }
    return jsonify({"room_id": room_id})

@app.route('/submit_payment/<room_id>', methods=['POST'])
def submit_payment(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
        
    data = request.get_json()
    name = data["name"]
    amount = float(data["amount"])
    description = data.get("description", "未填写描述")
    involved_members = data.get("involved_members", rooms[room_id]["members"])  # 默认所有成员参与
    
    # 保存详细的支付记录
    payment_record = {
        "id": str(time.time()),  # 使用时间戳作为ID
        "name": name,
        "amount": amount,
        "description": description,
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "involved_members": involved_members  # 记录涉及的成员
    }
    rooms[room_id]["payment_records"].append(payment_record)
    
    # 重新计算每个人的支付金额
    recalculate_payments(room_id)
        
    return jsonify({"success": True})

@app.route('/edit_payment/<room_id>', methods=['PUT'])
def edit_payment(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
        
    data = request.get_json()
    payment_id = data["id"]
    
    # 查找支付记录
    for i, record in enumerate(rooms[room_id]["payment_records"]):
        if record["id"] == payment_id:
            # 更新记录
            record["name"] = data["name"]
            record["amount"] = float(data["amount"])
            record["description"] = data.get("description", "未填写描述")
            record["involved_members"] = data.get("involved_members", rooms[room_id]["members"])
            record["date"] = time.strftime("%Y-%m-%d %H:%M:%S") + " (已编辑)"
            
            # 重新计算每个人的支付金额
            recalculate_payments(room_id)
            return jsonify({"success": True})
    
    return jsonify({"error": "Payment record not found"}), 404

@app.route('/delete_payment/<room_id>', methods=['DELETE'])
def delete_payment(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
        
    data = request.get_json()
    payment_id = data["id"]
    
    # 查找并删除支付记录
    for i, record in enumerate(rooms[room_id]["payment_records"]):
        if record["id"] == payment_id:
            rooms[room_id]["payment_records"].pop(i)
            
            # 重新计算每个人的支付金额
            recalculate_payments(room_id)
            return jsonify({"success": True})
    
    return jsonify({"error": "Payment record not found"}), 404

def recalculate_payments(room_id):
    """重新计算房间中每个人的付款金额"""
    room = rooms[room_id]
    members = room["members"]
    payment_records = room["payment_records"]
    
    # 重置所有支付
    room["payments"] = {member: 0 for member in members}
    
    # 根据支付记录和涉及成员计算每个人的实际支付和应付
    for record in payment_records:
        # 支付人支付的金额
        payer = record["name"]
        if payer in room["payments"]:
            room["payments"][payer] += record["amount"]
        else:
            room["payments"][payer] = record["amount"]
        
        # 计算每个涉及成员应分担的金额
        involved = record["involved_members"]
        if involved and len(involved) > 0:
            share_per_person = record["amount"] / len(involved)
            for member in involved:
                if member != payer:  # 避免重复计算支付者的金额
                    if member in room["payments"]:
                        room["payments"][member] -= share_per_person
                    else:
                        room["payments"][member] = -share_per_person

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

    # 计算总额和每个人的消费额
    total_spent = sum([record["amount"] for record in room["payment_records"]])
    
    # 计算每人余额
    balances = {name: round(amount, 2) for name, amount in payments.items()}

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

    # 计算平均消费（考虑到每个支付的涉及成员可能不同）
    total_person_times = sum([len(record["involved_members"]) for record in room["payment_records"] if "involved_members" in record])
    avg_per_person = round(total_spent / total_person_times, 2) if total_person_times > 0 else 0

    return jsonify({
        "title": room["title"],
        "members": room["members"],
        "balances": balances,
        "transactions": transactions,
        "total_spent": round(total_spent, 2),
        "average_per_person": avg_per_person,
        "payment_records": room["payment_records"]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
