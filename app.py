# app.py 的修改版 (支持编辑/删除，为按成员分摊做准备)
from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid # 导入 uuid
import time
import copy # 导入 copy

app = Flask(__name__)
CORS(app) # 允许所有来源的跨域请求

# In-memory storage (注意：对于 Google 登录等持久化功能，需要换成数据库)
rooms = {}

@app.route('/')
def home():
    return "LightSplit Backend is running!"

@app.route('/create_room', methods=['POST'])
def create_room():
    data = request.get_json()
    
    while True:
        room_id = str(random.randint(1000, 9999))
        if room_id not in rooms:
            break
    
    # 确保成员列表没有重复项
    unique_members = sorted(list(set(filter(None, data.get("members", [])))))
    if len(unique_members) < 2:
         return jsonify({"error": "At least two unique members are required"}), 400
         
    rooms[room_id] = {
        "title": data.get("title", "Untitled Room"),
        "members": unique_members,
        "payment_records": [] # 只使用 payment_records 存储详细信息
    }
    print(f"Room created: {room_id}, Data: {rooms[room_id]}") # Debugging
    return jsonify({"room_id": room_id})

@app.route('/submit_payment/<room_id>', methods=['POST'])
def submit_payment(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
        
    data = request.get_json()
    name = data.get("name")
    amount_str = data.get("amount")
    description = data.get("description", "")
    # 新增：获取参与分摊的成员，默认为房间所有成员
    involved_members = data.get("involved_members", rooms[room_id]["members"]) 

    if not name or name not in rooms[room_id]["members"]:
        return jsonify({"error": "Invalid payer name"}), 400
    
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError):
         return jsonify({"error": "Invalid amount"}), 400
         
    # 验证 involved_members 是否都是房间成员
    valid_involved_members = [m for m in involved_members if m in rooms[room_id]["members"]]
    if not valid_involved_members:
         # 如果传入的参与者列表无效或为空，则默认使用房间所有成员
         valid_involved_members = rooms[room_id]["members"]

    payment_record = {
        "id": str(uuid.uuid4()), # 使用 UUID 作为唯一ID
        "name": name,
        "amount": amount,
        "description": description,
        "involved_members": valid_involved_members, # 存储参与成员
        "date": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    rooms[room_id]["payment_records"].append(payment_record)
    print(f"Payment added to {room_id}: {payment_record}") # Debugging
        
    return jsonify({"success": True, "payment_record": payment_record})

# 新增：删除支付记录
@app.route('/payment/<room_id>/<payment_id>', methods=['DELETE'])
def delete_payment(room_id, payment_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404

    initial_length = len(rooms[room_id]["payment_records"])
    rooms[room_id]["payment_records"] = [
        p for p in rooms[room_id]["payment_records"] if p.get("id") != payment_id
    ]
    
    if len(rooms[room_id]["payment_records"]) == initial_length:
        return jsonify({"error": "Payment record not found"}), 404

    print(f"Payment deleted from {room_id}: {payment_id}") # Debugging
    return jsonify({"success": True})

# 新增：编辑支付记录
@app.route('/payment/<room_id>/<payment_id>', methods=['PUT'])
def update_payment(room_id, payment_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404

    data = request.get_json()
    
    payment_found = False
    updated_record = None
    for i, record in enumerate(rooms[room_id]["payment_records"]):
        if record.get("id") == payment_id:
            try:
                new_amount = float(data.get("amount", record["amount"]))
                if new_amount <= 0:
                     raise ValueError("Amount must be positive")
                     
                new_name = data.get("name", record["name"])
                if new_name not in rooms[room_id]["members"]:
                     raise ValueError("Invalid payer name")

                new_involved_members = data.get("involved_members", record["involved_members"])
                valid_new_involved = [m for m in new_involved_members if m in rooms[room_id]["members"]]
                if not valid_new_involved:
                    valid_new_involved = rooms[room_id]["members"] # Default if invalid

                # 更新记录
                rooms[room_id]["payment_records"][i]["name"] = new_name
                rooms[room_id]["payment_records"][i]["amount"] = new_amount
                rooms[room_id]["payment_records"][i]["description"] = data.get("description", record["description"])
                rooms[room_id]["payment_records"][i]["involved_members"] = valid_new_involved
                # 可选：更新日期 record["date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                updated_record = rooms[room_id]["payment_records"][i]
                payment_found = True
                print(f"Payment updated in {room_id}: {payment_id}, Data: {updated_record}") # Debugging
                break
            except (ValueError, TypeError) as e:
                 print(f"Error updating payment {payment_id}: {e}") # Debugging
                 return jsonify({"error": f"Invalid update data: {e}"}), 400

    if not payment_found:
        return jsonify({"error": "Payment record not found"}), 404
        
    return jsonify({"success": True, "payment_record": updated_record})


# 修改：获取结果，现在基于 payment_records 计算
@app.route('/result/<room_id>', methods=['GET'])
def get_result(room_id):
    if room_id not in rooms:
        print(f"Room not found: {room_id}") # Debugging
        return jsonify({"error": "Room not found"}), 404
        
    room = rooms[room_id]
    members = room["members"]
    payment_records = room["payment_records"]

    # 1. 初始化所有成员的余额为 0
    balances = {member: 0.0 for member in members}
    total_spent = 0.0

    # 2. 遍历每一笔支付记录，计算分摊
    for record in payment_records:
        payer = record["name"]
        amount = record["amount"]
        involved_members = record.get("involved_members", members) # 向后兼容或默认
        
        # 确保 involved_members 列表有效且非空
        valid_involved_members = [m for m in involved_members if m in members]
        if not valid_involved_members:
             valid_involved_members = members # 如果记录中没有有效成员，则默认全部分摊
             
        if not valid_involved_members: # 如果房间也没有成员了（不太可能）
             continue 

        total_spent += amount
        
        # 付款人先增加全部金额
        balances[payer] += amount
        
        # 计算每个参与者的份额
        share = amount / len(valid_involved_members)
        
        # 每个参与者（包括付款人自己）减去份额
        for member in valid_involved_members:
            balances[member] -= share

    # 3. 对余额进行四舍五入，避免浮点数精度问题
    balances = {name: round(balance, 2) for name, balance in balances.items()}
    
    # 4. 计算转账明细 (这部分逻辑不变)
    transactions = calculate_transactions(balances)

    # 计算总额和“名义”人均（现在意义不大了，但可以保留）
    avg = total_spent / len(members) if len(members) > 0 else 0

    print(f"Result for {room_id}: Balances: {balances}, Transactions: {transactions}") # Debugging

    return jsonify({
        "title": room["title"],
        "members": room["members"],
        "balances": balances,
        "transactions": transactions,
        "total_spent": round(total_spent, 2),
        "average_per_person": round(avg, 2), # 这个平均值现在可能没那么直观了
        "payment_records": room["payment_records"] # 返回详细记录给前端
    })

# 辅助函数：计算转账明细 (从原 get_result 中提取出来)
def calculate_transactions(balances):
    transactions = []
    # 使用深拷贝，避免修改原始 balances 字典
    balances_copy = copy.deepcopy(balances) 
    
    # 过滤掉余额接近0的成员，避免无限循环
    balances_copy = {k: v for k, v in balances_copy.items() if abs(v) > 0.001}

    while True:
        creditors = {k: v for k, v in balances_copy.items() if v > 0.001}
        debtors = {k: v for k, v in balances_copy.items() if v < -0.001}

        if not creditors or not debtors:
            break # 没有需要处理的债权人或债务人了

        # 排序以便找到最大债权人和最大（负最多）债务人
        sorted_creditors = sorted(creditors.items(), key=lambda item: item[1], reverse=True)
        sorted_debtors = sorted(debtors.items(), key=lambda item: item[1])

        max_creditor = sorted_creditors[0]
        max_debtor = sorted_debtors[0]

        # 计算转账金额，取两者绝对值的较小者
        amount = min(max_creditor[1], -max_debtor[1])
        amount = round(amount, 2) # 四舍五入到分

        # 避免无效转账
        if amount <= 0.001:
            # 可能由于浮点精度问题导致无法继续，强制退出
            print("Warning: Potential floating point issue or loop detected in transaction calculation.")
            break
            
        # 更新余额
        balances_copy[max_creditor[0]] = round(balances_copy[max_creditor[0]] - amount, 2)
        balances_copy[max_debtor[0]] = round(balances_copy[max_debtor[0]] + amount, 2)

        transactions.append({
            "from": max_debtor[0],
            "to": max_creditor[0],
            "amount": amount
        })
        
        # 移除余额已经为零或接近零的成员，优化性能
        balances_copy = {k: v for k, v in balances_copy.items() if abs(v) > 0.001}


    return transactions


# Python 入口点
if __name__ == '__main__':
    # Gunicorn 或其他 WSGI 服务器会查找名为 'app' 的 Flask 实例
    # 使用 app.run() 仅用于本地开发调试
    # 部署时 Render 会使用 Gunicorn: gunicorn app:app
    # host='0.0.0.0' 允许外部访问，port 默认 5000，Render 可能会覆盖
    app.run(host='0.0.0.0', port=5000, debug=True) # 添加 debug=True 以便本地开发
